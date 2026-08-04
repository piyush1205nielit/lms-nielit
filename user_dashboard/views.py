from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Q, Avg
from django.utils import timezone

from course.models import Enrollment, Progress, Lesson
from assignment.models import Assignment, AssignmentSubmission
from announcement.models import Announcement
from user.forms import ProfileEditForm
from accounts.models import User
from .forms import StatusCheckForm
from .services import *
from django.template.loader import render_to_string
from django.http import JsonResponse


@login_required(login_url='user:login')
def dashboard_home(request):
    user = request.user
    profile = user.learner_profile

    enrollments = Enrollment.objects.filter(user=user).select_related('course')
    granted_enrollments = enrollments.filter(access_status=Enrollment.AccessStatus.GRANTED)

    total_courses = granted_enrollments.count()
    completed_courses = granted_enrollments.filter(status=Enrollment.Status.COMPLETED).count()
    in_progress_courses = total_courses - completed_courses

    # Per-course progress percentage, then averaged for an overall completion figure
    course_progress = []
    for enrollment in granted_enrollments:
        total_lessons = Lesson.objects.filter(module__course=enrollment.course).count()
        completed_lessons = Progress.objects.filter(
            user=user, lesson__module__course=enrollment.course, completed=True
        ).count()
        percent = int((completed_lessons / total_lessons) * 100) if total_lessons else 0
        course_progress.append({
            'course': enrollment.course, 'percent': percent,
            'completed': completed_lessons, 'total': total_lessons,
        })

    overall_progress = int(sum(c['percent'] for c in course_progress) / len(course_progress)) if course_progress else 0

    enrolled_course_ids = enrollments.values_list('course_id', flat=True)
    pending_assignments = Assignment.objects.filter(
        course_id__in=enrolled_course_ids, is_active=True, deadline__gt=timezone.now()
    ).exclude(submissions__student=user).count()

    graded_submissions = AssignmentSubmission.objects.filter(student=user, status=AssignmentSubmission.Status.GRADED)
    graded_count = graded_submissions.count()
    avg_score_pct = None
    if graded_count:
        scores = []
        for s in graded_submissions.select_related('assignment'):
            if s.assignment.max_marks:
                scores.append((s.marks_obtained / s.assignment.max_marks) * 100)
        avg_score_pct = int(sum(scores) / len(scores)) if scores else None

    recent_announcements = Announcement.objects.for_user(user)[:4]

    total_watch_seconds = Progress.objects.filter(user=user).values_list('watched_seconds', flat=True)
    total_hours_learned = round(sum(total_watch_seconds) / 3600, 1) if total_watch_seconds else 0

    return render(request, 'user_dashboard/home.html', {
        'profile': profile,
        'total_courses': total_courses,
        'completed_courses': completed_courses,
        'in_progress_courses': in_progress_courses,
        'overall_progress': overall_progress,
        'course_progress': course_progress[:5],
        'pending_assignments': pending_assignments,
        'graded_count': graded_count,
        'avg_score_pct': avg_score_pct,
        'recent_announcements': recent_announcements,
        'total_hours_learned': total_hours_learned,
        'active_page': 'dashboard',
    })


@login_required(login_url='user:login')
def profile_view(request):
    profile = request.user.learner_profile
    return render(request, 'user_dashboard/profile.html', {
        'profile': profile,
        'active_page': 'profile',
    })


@login_required(login_url='user:login')
def profile_edit_view(request):
    profile = request.user.learner_profile
    form = ProfileEditForm(request.POST or None, request.FILES or None, instance=profile)

    if request.method == 'POST' and form.is_valid():
        updated_profile = form.save(commit=False)
        # once every required field is present, mark the profile complete —
        # this is what lifts ProfileCompletionMiddleware's redirect
        required_filled = all([
            updated_profile.full_name, updated_profile.date_of_birth, updated_profile.gender,
            updated_profile.address, updated_profile.city, updated_profile.state, updated_profile.pin_code,
        ])
        updated_profile.profile_completed = required_filled
        updated_profile.save()
        messages.success(request, "Profile updated successfully.")
        return redirect('user_dashboard:profile')

    return render(request, 'user_dashboard/profile_edit.html', {
        'form': form, 'profile': profile,
        'active_page': 'profile',
    })


@login_required(login_url='user:login')
def my_courses_view(request):
    enrollments = Enrollment.objects.filter(user=request.user).select_related('course').prefetch_related('course__domains').order_by('-enrolled_at')

    course_data = []
    for enrollment in enrollments:
        total_lessons = Lesson.objects.filter(module__course=enrollment.course).count()
        completed_lessons = Progress.objects.filter(
            user=request.user, lesson__module__course=enrollment.course, completed=True
        ).count()
        percent = int((completed_lessons / total_lessons) * 100) if total_lessons else 0
        course_data.append({
            'enrollment': enrollment, 'percent': percent,
            'completed': completed_lessons, 'total': total_lessons,
        })

    return render(request, 'user_dashboard/my_courses.html', {
        'course_data': course_data,
        'active_page': 'my_courses',
    })



@login_required(login_url='user:login')
def notifications_dropdown_view(request):
    items = get_user_notifications(request.user)
    html = render_to_string(
        'user_dashboard/includes/notifications_dropdown.html', {'items': items}, request=request
    )
    mark_notifications_seen(request.user)   # every open, not just the first — see JS fix below
    return JsonResponse({'html': html})



def status_check_view(request):
    form = StatusCheckForm(request.POST or None)
    result = None
    searched = False

    if request.method == 'POST' and form.is_valid():
        searched = True
        identifier = form.cleaned_data['identifier'].strip()

        user = User.objects.filter(
            Q(email__iexact=identifier) | Q(contact=identifier),
            role=User.Role.USER,
        ).select_related('nielit_centre', 'learner_profile').first()

        if user:
            enrollments = Enrollment.objects.filter(user=user).select_related('course').order_by('-enrolled_at')
            result = {
                'found': True,
                'email': user.email,
                'contact': user.contact,
                'full_name': getattr(user.learner_profile, 'full_name', None),
                'centre': user.nielit_centre.centre_name if user.nielit_centre else None,
                'batch_code': user.batch_code,
                'account_status': user.account_status,
                'account_status_display': user.get_account_status_display(),
                'profile_completed': getattr(user.learner_profile, 'profile_completed', False),
                'enrollments': [
                    {
                        'course_name': e.course.course_name,
                        'access_status': e.access_status,
                        'access_status_display': e.get_access_status_display(),
                        'enrolled_at': e.enrolled_at,
                    }
                    for e in enrollments
                ],
            }
        else:
            result = {'found': False}

    return render(request, 'user_dashboard/status_check.html', {
        'form': form,
        'result': result,
        'searched': searched,
    })