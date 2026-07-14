from django.shortcuts import render
from django.contrib.auth.decorators import login_required


@login_required(login_url='user:login')
def dashboard_home(request):
    profile = request.user.learner_profile
    return render(request, 'user_dashboard/home.html', {
        'profile': profile,
        'active_page': 'home',
    })