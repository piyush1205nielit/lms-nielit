from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from announcement.models import Announcement


@login_required(login_url='user:login')
def dashboard_home(request):
    profile = request.user.learner_profile
    return render(request, 'user_dashboard/home.html', {
        'profile': profile,
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