from django.shortcuts import render
from accounts.decorators import admin_required
from user.models import LearnerProfile


@admin_required
def dashboard_home(request):
    return render(request, 'admin_dashboard/main_dashboard.html', {'active_page': 'dashboard'})


@admin_required
def registered_users_view(request):
    users = LearnerProfile.objects.select_related('user').order_by('-created_at')
    return render(request, 'admin_dashboard/registered_users_list.html', {
        'users': users,
        'active_page': 'users',
    })