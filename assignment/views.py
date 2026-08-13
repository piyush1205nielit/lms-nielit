#assignment/views.py
import json

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.conf import settings
from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Count, Q
from django.views.decorators.http import require_POST
from admin_dashboard.models import Centre
from accounts.decorators import admin_required, admin_or_faculty_required
from course.models import Course, Enrollment
from .models import Assignment, AssignmentSubmission
from .forms import AssignmentForm, SubmissionForm, GradeSubmissionForm
from user_dashboard.services import mark_notifications_seen
from admin_dashboard.notifications import notify_users, get_display_name

def _is_ajax(request):
    return request.headers.get('x-requested-with') == 'XMLHttpRequest'


# ══════════════════ ADMIN ══════════════════

@admin_or_faculty_required
def assignment_list_view(request):
    assignments = Assignment.objects.select_related('course').annotate(
        submission_count=Count('submissions', distinct=True),
        graded_count=Count('submissions', filter=Q(submissions__status='graded'), distinct=True),
        ungraded_count=Count('submissions', filter=Q(submissions__status='submitted'), distinct=True),
    ).order_by('-deadline')

    course_id = request.GET.get('course', '').strip()
    search_query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '').strip()

    if course_id:
        assignments = assignments.filter(course_id=course_id)

    if search_query:
        assignments = assignments.filter(
            Q(title__icontains=search_query) | Q(course__course_name__icontains=search_query)
        )

    now = timezone.now()
    if status_filter == 'active':
        assignments = assignments.filter(is_active=True, deadline__gt=now)
    elif status_filter == 'closed':
        assignments = assignments.filter(is_active=True, deadline__lte=now)
    elif status_filter == 'inactive':
        assignments = assignments.filter(is_active=False)

    return render(request, 'assignment/manage_list.html', {
        'assignments': assignments,
        'all_courses': Course.objects.filter(status=Course.Status.ACTIVE).order_by('course_name'),
        'selected_course': course_id,
        'search_query': search_query,
        'status_filter': status_filter,
        'active_count': Assignment.objects.filter(is_active=True).count(),
        'total_submissions': AssignmentSubmission.objects.count(),
        'pending_grading': AssignmentSubmission.objects.filter(status=AssignmentSubmission.Status.SUBMITTED).count(),
        'active_page': 'assignments',
    })


@admin_or_faculty_required
def assignment_create_view(request):
    form = AssignmentForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        assignment = form.save(commit=False)
        assignment.created_by = request.user
        assignment.save()
        _notify_course_students(assignment)
        messages.success(request, f"Assignment '{assignment.title}' created and students notified.")
        return redirect('assignment:manage_list')
    return render(request, 'assignment/form.html', {'form': form, 'active_page': 'assignments'})


@admin_or_faculty_required
def assignment_edit_view(request, assignment_id):
    assignment = get_object_or_404(Assignment, id=assignment_id)
    form = AssignmentForm(request.POST or None, request.FILES or None, instance=assignment)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Assignment updated.")
        return redirect('assignment:manage_list')
    return render(request, 'assignment/form.html', {'form': form, 'assignment': assignment, 'active_page': 'assignments'})


@admin_or_faculty_required
def assignment_delete_view(request, assignment_id):
    assignment = get_object_or_404(Assignment, id=assignment_id)
    if request.method == 'POST':
        title = assignment.title
        assignment.delete()
        messages.success(request, f"Assignment '{title}' deleted.")
    return redirect('assignment:manage_list')


@admin_or_faculty_required
def assignment_submissions_view(request, assignment_id):
    assignment = get_object_or_404(Assignment, id=assignment_id)

    base_enrollments = Enrollment.objects.filter(course=assignment.course).select_related(
        'user', 'user__learner_profile', 'user__nielit_centre'
    )
    submissions_by_user = {
        s.student_id: s for s in assignment.submissions.select_related('student', 'student__learner_profile')
    }

    # ── Stat-card counts computed on the FULL (unfiltered) roster ──
    full_roster_submissions = [submissions_by_user.get(e.user_id) for e in base_enrollments]
    pending_count = sum(1 for s in full_roster_submissions if s is None)
    awaiting_count = sum(1 for s in full_roster_submissions if s and s.status != AssignmentSubmission.Status.GRADED)
    graded_count = sum(1 for s in full_roster_submissions if s and s.status == AssignmentSubmission.Status.GRADED)

    # ── Read filters ──
    search_query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '').strip()
    centre_id = request.GET.get('centre', '').strip()
    batch_code = request.GET.get('batch', '').strip()
    gender_filter = request.GET.get('gender', '').strip()

    enrollments = base_enrollments
    if centre_id:
        enrollments = enrollments.filter(user__nielit_centre_id=centre_id)
    if batch_code:
        enrollments = enrollments.filter(user__batch_code=batch_code)
    if gender_filter:
        enrollments = enrollments.filter(user__learner_profile__gender=gender_filter)
    if search_query:
        enrollments = enrollments.filter(
            Q(user__email__icontains=search_query) |
            Q(user__learner_profile__full_name__icontains=search_query) |
            Q(user__learner_profile__enrollment_number__icontains=search_query) |
            Q(user__contact__icontains=search_query)
        )

    roster = []
    for enrollment in enrollments:
        submission = submissions_by_user.get(enrollment.user_id)
        roster.append({'student': enrollment.user, 'submission': submission})

    if status_filter:
        def matches_status(entry):
            submission = entry['submission']
            if status_filter == 'pending':
                return submission is None
            if status_filter == 'awaiting':
                return submission is not None and submission.status != AssignmentSubmission.Status.GRADED
            if status_filter == 'graded':
                return submission is not None and submission.status == AssignmentSubmission.Status.GRADED
            return True

        roster = [r for r in roster if matches_status(r)]

    # ── Filter dropdown data (scoped to students actually enrolled in this course) ──
    all_centres = Centre.objects.filter(
        id__in=base_enrollments.exclude(user__nielit_centre__isnull=True).values_list('user__nielit_centre_id', flat=True)
    ).distinct().order_by('id')

    all_batches = base_enrollments.exclude(user__batch_code='').values_list(
        'user__batch_code', flat=True
    ).distinct().order_by('user__batch_code')

    return render(request, 'assignment/submissions_list.html', {
        'assignment': assignment,
        'roster': roster,
        'search_query': search_query,
        'status_filter': status_filter,
        'centre_id': centre_id,
        'batch_code': batch_code,
        'gender_filter': gender_filter,
        'all_centres': all_centres,
        'all_batches': all_batches,
        'pending_count': pending_count,
        'awaiting_count': awaiting_count,
        'graded_count': graded_count,
        'active_page': 'assignments',
    })


@admin_or_faculty_required
def submission_detail_json(request, submission_id):
    """AJAX endpoint powering the 'View Submission' modal."""
    submission = get_object_or_404(
        AssignmentSubmission.objects.select_related('student', 'student__learner_profile', 'assignment'),
        id=submission_id
    )
    profile = getattr(submission.student, 'learner_profile', None)
    student_name = (getattr(profile, 'full_name', '') or '').strip() or submission.student.email

    data = {
        'id': str(submission.id),
        'student_name': student_name,
        'student_email': submission.student.email,
        'submission_text': submission.submission_text,
        'submission_file_url': submission.submission_file.url if submission.submission_file else None,
        'submission_file_name': submission.submission_file.name.rsplit('/', 1)[-1] if submission.submission_file else None,
        'submitted_at': submission.submitted_at.strftime('%d %b %Y, %I:%M %p'),
        'is_late': submission.is_late,
        'status': submission.status,
        'marks_obtained': submission.marks_obtained,
        'max_marks': submission.assignment.max_marks,
        'feedback': submission.feedback,
    }
    return JsonResponse({'success': True, 'submission': data})


@admin_or_faculty_required
def grade_submission_view(request, submission_id):
    submission = get_object_or_404(AssignmentSubmission, id=submission_id)
    ajax = _is_ajax(request)

    if request.method == 'POST':
        form = GradeSubmissionForm(request.POST, instance=submission, max_marks=submission.assignment.max_marks)
        if form.is_valid():
            graded = form.save(commit=False)
            graded.status = AssignmentSubmission.Status.GRADED
            graded.graded_by = request.user
            graded.graded_at = timezone.now()
            graded.save()
            _notify_student_graded(graded)

            if ajax:
                return JsonResponse({
                    'success': True,
                    'message': f"Marks saved for {submission.student.email}.",
                    'submission_id': str(graded.id),
                    'marks_obtained': graded.marks_obtained,
                    'max_marks': graded.assignment.max_marks,
                    'status': graded.status,
                })
            messages.success(request, f"Marks saved for {submission.student.email}.")
            return redirect('assignment:submissions_list', assignment_id=submission.assignment.id)

        if ajax:
            return JsonResponse({'success': False, 'errors': form.errors}, status=400)
    else:
        form = GradeSubmissionForm(instance=submission, max_marks=submission.assignment.max_marks)

    # Non-JS fallback page (kept for direct links / accessibility)
    return render(request, 'assignment/grade_form.html', {
        'form': form, 'submission': submission, 'active_page': 'assignments',
    })


@admin_or_faculty_required
@require_POST
def bulk_grade_submissions_view(request, assignment_id):
    """AJAX endpoint for the bulk grading modal. Expects JSON body:
    {"grades": [{"submission_id": "...", "marks_obtained": 45, "feedback": "..."}, ...]}
    """
    assignment = get_object_or_404(Assignment, id=assignment_id)

    try:
        payload = json.loads(request.body.decode('utf-8'))
    except (json.JSONDecodeError, TypeError, UnicodeDecodeError):
        return JsonResponse({'success': False, 'error': 'Invalid request payload.'}, status=400)

    entries = payload.get('grades') or []
    if not entries:
        return JsonResponse({'success': False, 'error': 'No submissions provided.'}, status=400)

    graded_results = []
    errors = []

    with transaction.atomic():
        for entry in entries:
            submission_id = entry.get('submission_id')
            marks = entry.get('marks_obtained')
            feedback = entry.get('feedback', '')

            try:
                submission = AssignmentSubmission.objects.select_related('student', 'assignment').get(
                    id=submission_id, assignment_id=assignment_id
                )
            except (AssignmentSubmission.DoesNotExist, ValueError, TypeError):
                errors.append({'submission_id': submission_id, 'error': 'Submission not found.'})
                continue

            form = GradeSubmissionForm(
                {'marks_obtained': marks, 'feedback': feedback},
                instance=submission,
                max_marks=assignment.max_marks,
            )
            if form.is_valid():
                graded = form.save(commit=False)
                graded.status = AssignmentSubmission.Status.GRADED
                graded.graded_by = request.user
                graded.graded_at = timezone.now()
                graded.save()
                _notify_student_graded(graded)
                graded_results.append({
                    'submission_id': str(submission.id),
                    'student_email': submission.student.email,
                    'marks_obtained': graded.marks_obtained,
                })
            else:
                errors.append({
                    'submission_id': submission_id,
                    'student_email': submission.student.email,
                    'errors': form.errors,
                })

    return JsonResponse({
        'success': len(errors) == 0,
        'graded_count': len(graded_results),
        'graded': graded_results,
        'errors': errors,
    })


# ══════════════════ STUDENT ══════════════════

@login_required(login_url='user:login')
def my_assignments_view(request):
    enrolled_course_ids = Enrollment.objects.filter(user=request.user).values_list('course_id', flat=True)
    assignments = Assignment.objects.filter(
        course_id__in=enrolled_course_ids, is_active=True
    ).select_related('course').order_by('deadline')

    my_submissions = {
        s.assignment_id: s for s in AssignmentSubmission.objects.filter(student=request.user)
    }

    pending, submitted, graded, missed = [], [], [], []
    for a in assignments:
        submission = my_submissions.get(a.id)
        if submission and submission.status == AssignmentSubmission.Status.GRADED:
            graded.append({'assignment': a, 'submission': submission})
        elif submission:
            submitted.append({'assignment': a, 'submission': submission})
        elif a.is_past_deadline:
            missed.append({'assignment': a, 'submission': None})
        else:
            pending.append({'assignment': a, 'submission': None})

    mark_notifications_seen(request.user)
    return render(request, 'assignment/my_assignments.html', {
        'pending': pending, 'submitted': submitted, 'graded': graded, 'missed': missed,
        'active_page': 'assignments',
    })


@login_required(login_url='user:login')
def assignment_submit_view(request, assignment_id):
    assignment = get_object_or_404(Assignment, id=assignment_id, is_active=True)

    if not Enrollment.objects.filter(user=request.user, course=assignment.course).exists():
        messages.error(request, "You must be enrolled in this course to view this assignment.")
        return redirect('course:my_courses')

    existing_submission = assignment.submission_for(request.user)

    if existing_submission and existing_submission.status == AssignmentSubmission.Status.GRADED:
        messages.info(request, "This assignment has already been graded and can no longer be edited.")
        return redirect('assignment:my_assignments')

    if assignment.is_past_deadline and not existing_submission:
        messages.error(request, "The deadline for this assignment has passed.")
        return redirect('assignment:my_assignments')

    form = SubmissionForm(request.POST or None, request.FILES or None, instance=existing_submission)

    if request.method == 'POST' and form.is_valid():
        submission = form.save(commit=False)
        submission.assignment = assignment
        submission.student = request.user
        submission.is_late = assignment.is_past_deadline
        submission.status = AssignmentSubmission.Status.SUBMITTED
        submission.save()
        messages.success(request, "Assignment submitted successfully.")
        return redirect('assignment:my_assignments')

    return render(request, 'assignment/submit_form.html', {
        'form': form, 'assignment': assignment, 'existing_submission': existing_submission,
        'active_page': 'assignments',
    })


# ══════════════════ Notifications (plain SMTP, reuses existing email config) ══════════════════

def _notify_course_students(assignment):
    enrollments = Enrollment.objects.filter(
        course=assignment.course, access_status=Enrollment.AccessStatus.GRANTED
    ).select_related('user')

    for enrollment in enrollments:
        name = get_display_name(enrollment.user)
        notify_users(
            [enrollment.user],
            title=f"New Assignment: {assignment.title}",
            app_message=f"New assignment posted for {assignment.course.course_name} — due {assignment.deadline.strftime('%d %b %Y')}.",
            email_message=(
                f"Dear {name},\n\n"
                f"A new assignment has been posted for {assignment.course.course_name}.\n\n"
                f"Title: {assignment.title}\n"
                f"Max Marks: {assignment.max_marks}\n"
                f"Deadline: {assignment.deadline.strftime('%d %B %Y, %I:%M %p')}\n\n"
                f"Log in to your dashboard to view details and submit."
            ),
            created_by=assignment.created_by,
        )


def _notify_student_graded(submission):
    name = get_display_name(submission.student)
    notify_users(
        [submission.student],
        title=f"Assignment Graded: {submission.assignment.title}",
        app_message=f"You scored {submission.marks_obtained}/{submission.assignment.max_marks} on {submission.assignment.title}.",
        email_message=(
            f"Dear {name},\n\n"
            f"Your submission for \u201c{submission.assignment.title}\u201d ({submission.assignment.course.course_name}) has been graded.\n\n"
            f"Marks: {submission.marks_obtained} / {submission.assignment.max_marks}\n"
            f"Feedback: {submission.feedback or 'No feedback provided.'}\n\n"
            f"Log in to your dashboard to view details."
        ),
        created_by=submission.graded_by,
    )