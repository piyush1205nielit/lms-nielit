from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from announcement.models import Announcement
from assignment.models import Assignment, AssignmentSubmission
from django.utils import timezone


@login_required(login_url='user:login')
def dashboard_home(request):
    profile = request.user.learner_profile
    enrolled_course_ids = request.user.enrollments.values_list('course_id', flat=True)
    pending_count = Assignment.objects.filter(
        course_id__in=enrolled_course_ids, is_active=True, deadline__gt=timezone.now()
    ).exclude(submissions__student=request.user).count()

    return render(request, 'user_dashboard/home.html', {
        'profile': profile,
        'pending_assignments_count': pending_count,
        'active_page': 'home',
    })


@login_required(login_url='user:login')
def dashboard_home(request):
    profile = request.user.learner_profile
    my_announcements = Announcement.objects.for_user(request.user)[:5]
    return render(request, 'user_dashboard/home.html', {
        'profile': profile,
        'my_announcements': my_announcements,
        'active_page': 'home',
    })