from django.shortcuts import render
from accounts.decorators import admin_required
from user.models import LearnerProfile


from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages

from accounts.decorators import admin_required, superadmin_required
from accounts.models import User
from user.models import LearnerProfile
from .forms import AdminUserProfileEditForm, UserCredentialsForm


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




@admin_required
def user_profile_edit_view(request, user_id):
    target_user = get_object_or_404(User, id=user_id, role=User.Role.USER)
    profile = target_user.learner_profile
    form = AdminUserProfileEditForm(request.POST or None, request.FILES or None, instance=profile)

    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f"Profile updated for {target_user.email}.")
        return redirect('admin_dashboard:registered_users')

    return render(request, 'admin_dashboard/user_profile_edit.html', {
        'form': form,
        'target_user': target_user,
        'active_page': 'users',
    })


@superadmin_required
def user_credentials_edit_view(request, user_id):
    target_user = get_object_or_404(User, id=user_id, role=User.Role.USER)
    form = UserCredentialsForm(request.POST or None, instance=target_user)

    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f"Login credentials updated for {target_user.email}.")
        return redirect('admin_dashboard:registered_users')

    return render(request, 'admin_dashboard/user_credentials_edit.html', {
        'form': form,
        'target_user': target_user,
        'active_page': 'users',
    })