from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from django.db.models import Count, Q

from accounts.decorators import admin_required
from course.models import Course, Enrollment
from .models import Assignment, AssignmentSubmission
from .forms import AssignmentForm, SubmissionForm, GradeSubmissionForm
from user_dashboard.services import mark_notifications_seen


# ══════════════════ ADMIN ══════════════════

@admin_required
def assignment_list_view(request):
    assignments = Assignment.objects.select_related('course').annotate(
        submission_count=Count('submissions', distinct=True),
        graded_count=Count('submissions', filter=Q(submissions__status='graded'), distinct=True),
    ).order_by('-deadline')

    course_id = request.GET.get('course', '').strip()
    if course_id:
        assignments = assignments.filter(course_id=course_id)

    return render(request, 'assignment/manage_list.html', {
        'assignments': assignments,
        'all_courses': Course.objects.filter(status=Course.Status.ACTIVE).order_by('course_name'),
        'selected_course': course_id,
        'active_page': 'assignments',
    })


@admin_required
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


@admin_required
def assignment_edit_view(request, assignment_id):
    assignment = get_object_or_404(Assignment, id=assignment_id)
    form = AssignmentForm(request.POST or None, request.FILES or None, instance=assignment)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Assignment updated.")
        return redirect('assignment:manage_list')
    return render(request, 'assignment/form.html', {'form': form, 'assignment': assignment, 'active_page': 'assignments'})


@admin_required
def assignment_delete_view(request, assignment_id):
    assignment = get_object_or_404(Assignment, id=assignment_id)
    if request.method == 'POST':
        title = assignment.title
        assignment.delete()
        messages.success(request, f"Assignment '{title}' deleted.")
    return redirect('assignment:manage_list')


@admin_required
def assignment_submissions_view(request, assignment_id):
    assignment = get_object_or_404(Assignment, id=assignment_id)

    enrolled_students = Enrollment.objects.filter(course=assignment.course).select_related('user', 'user__learner_profile')
    submissions_by_user = {s.student_id: s for s in assignment.submissions.select_related('student', 'student__learner_profile')}

    roster = []
    for enrollment in enrolled_students:
        submission = submissions_by_user.get(enrollment.user_id)
        roster.append({'student': enrollment.user, 'submission': submission})

    return render(request, 'assignment/submissions_list.html', {
        'assignment': assignment,
        'roster': roster,
        'active_page': 'assignments',
    })


@admin_required
def grade_submission_view(request, submission_id):
    submission = get_object_or_404(AssignmentSubmission, id=submission_id)
    form = GradeSubmissionForm(request.POST or None, instance=submission, max_marks=submission.assignment.max_marks)

    if request.method == 'POST' and form.is_valid():
        graded = form.save(commit=False)
        graded.status = AssignmentSubmission.Status.GRADED
        graded.graded_by = request.user
        graded.graded_at = timezone.now()
        graded.save()
        _notify_student_graded(graded)
        messages.success(request, f"Marks saved for {submission.student.email}.")
        return redirect('assignment:submissions_list', assignment_id=submission.assignment.id)

    return render(request, 'assignment/grade_form.html', {
        'form': form, 'submission': submission, 'active_page': 'assignments',
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
    students = [e.user for e in Enrollment.objects.filter(course=assignment.course).select_related('user')]
    for student in students:
        try:
            send_mail(
                subject=f"New Assignment: {assignment.title}",
                message=(
                    f"A new assignment has been posted for {assignment.course.course_name}.\n\n"
                    f"Title: {assignment.title}\n"
                    f"Max Marks: {assignment.max_marks}\n"
                    f"Deadline: {assignment.deadline.strftime('%d %b %Y, %I:%M %p')}\n\n"
                    f"Log in to your dashboard to view details and submit."
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[student.email],
                fail_silently=True,
            )
        except Exception:
            pass  # never let an email failure block assignment creation


def _notify_student_graded(submission):
    try:
        send_mail(
            subject=f"Assignment Graded: {submission.assignment.title}",
            message=(
                f"Your submission for '{submission.assignment.title}' has been graded.\n\n"
                f"Marks: {submission.marks_obtained} / {submission.assignment.max_marks}\n"
                f"Feedback: {submission.feedback or 'No feedback provided.'}\n\n"
                f"Log in to your dashboard to view details."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[submission.student.email],
            fail_silently=True,
        )
    except Exception:
        pass