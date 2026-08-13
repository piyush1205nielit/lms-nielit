#account/views.py
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect,  get_object_or_404
from .decorators import admin_required

from .decorators import superadmin_required
from .forms import AdminLoginForm, AdminCreateForm, AdminEditForm, FacultyForm
from .models import User, AdminProfile, FacultyProfile
from django.contrib.auth.forms import SetPasswordForm
from django.views.decorators.http import require_POST
from django.utils import timezone
from admin_dashboard.notifications import *






def admin_login_view(request):
    if request.user.is_authenticated and request.user.is_admin_role:
        return redirect('admin_dashboard:home')

    form = AdminLoginForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        identifier = form.cleaned_data['identifier']   # email or contact
        password = form.cleaned_data['password']
        user = authenticate(request, username=identifier, password=password)

        if user is not None and user.is_active and user.is_staff_area_role:
            login(request, user)
            if user.role == User.Role.FACULTY:
                return redirect('admin_dashboard:faculty_home')
            return redirect('admin_dashboard:home')

        messages.error(request, "Invalid credentials or this account doesn't have admin access.")

    return render(request, 'accounts/admin_login.html', {'form': form})


def admin_logout_view(request):
    logout(request)
    return redirect('accounts:admin_login')


@admin_required
def admin_list_view(request):
    admins = AdminProfile.objects.select_related('user').filter(user__role=User.Role.ADMIN)
    return render(request, 'accounts/admin_list.html', {
        'admins': admins,
        'active_page': 'admins',
    })


@superadmin_required
def admin_create_view(request):
    form = AdminCreateForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = User.objects.create_user(
            email=form.cleaned_data['email'],
            contact=form.cleaned_data['contact'],
            password=form.cleaned_data['password'],
            role=User.Role.ADMIN,
            is_staff=True,
        )
        AdminProfile.objects.create(
            user=user,
            name=form.cleaned_data['name'],
            bio=form.cleaned_data['bio'],
            created_by=request.user,
        )
        messages.success(request, f"Admin account created for {user.email}.")
        return redirect('accounts:admin_list')

    return render(request, 'accounts/admin_create.html', {'form': form})



@superadmin_required
def admin_edit_view(request, pk):
    target_user = get_object_or_404(User, pk=pk, role=User.Role.ADMIN)
    profile = target_user.admin_profile
    form = AdminEditForm(request.POST or None, instance=profile, initial={'contact': target_user.contact})

    if request.method == 'POST' and form.is_valid():
        form.save()
        target_user.contact = form.cleaned_data['contact']
        target_user.save(update_fields=['contact'])
        messages.success(request, "Admin details updated.")
        return redirect('accounts:admin_list')

    return render(request, 'accounts/admin_edit.html', {'form': form, 'target_admin': target_user})


@superadmin_required
def admin_change_password_view(request, pk):
    target_user = get_object_or_404(User, pk=pk, role=User.Role.ADMIN)
    form = SetPasswordForm(user=target_user, data=request.POST or None)

    for field in form.fields.values():
        field.widget.attrs.update({'class': 'form-control'})

    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f"Password updated for {target_user.email}.")
        return redirect('accounts:admin_list')

    return render(request, 'accounts/admin_change_password.html', {'form': form, 'target_admin': target_user})


@superadmin_required
def admin_toggle_active_view(request, pk):
    target_user = get_object_or_404(User, pk=pk, role=User.Role.ADMIN)
    target_user.is_active = not target_user.is_active
    target_user.save(update_fields=['is_active'])
    state = "enabled" if target_user.is_active else "disabled"
    messages.success(request, f"Admin account {state}.")
    return redirect('accounts:admin_list')


@superadmin_required
def admin_delete_view(request, pk):
    target_user = get_object_or_404(User, pk=pk, role=User.Role.ADMIN)
    email = target_user.email
    target_user.delete()
    messages.success(request, f"Admin account {email} permanently deleted.")
    return redirect('accounts:admin_list')






@superadmin_required
def faculty_list_view(request):
    faculty_members = FacultyProfile.objects.select_related('user', 'nielit_centre').order_by('full_name')
    return render(request, 'accounts/faculty_list.html', {
        'faculty_members': faculty_members,
        'active_page': 'faculty',
    })


@superadmin_required
def faculty_create_view(request):
    form = FacultyForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = User(
            email=form.cleaned_data['email'],
            contact=form.cleaned_data['contact'],
            role=User.Role.FACULTY,
            is_staff=True,
            is_active=True,
            account_status=User.AccountStatus.ACTIVE,
            account_status_updated_at=timezone.now(),
        )
        user.set_password(form.cleaned_data['password'])
        user.save()

        profile = form.save(commit=False)
        profile.user = user
        profile.created_by = request.user
        profile.save()

        notify_users(
            [user],
            title="Faculty Account Created",
            app_message="Your faculty account has been created. Contact the administrator for your login password.",
            email_message=(
                f"Dear {profile.full_name},\n\n"
                f"A faculty account has been created for you on NIELIT LMS.\n\n"
                f"Login Email: {user.email}\n"
                f"Login Contact: {user.contact}\n\n"
                f"Use the password provided to you separately by the administrator to log in."
            ),
            created_by=request.user,
        )
        messages.success(request, f"Faculty account created for {profile.full_name}.")
        return redirect('accounts:faculty_list')

    return render(request, 'accounts/faculty_form.html', {'form': form, 'active_page': 'faculty'})


@superadmin_required
def faculty_edit_view(request, faculty_id):
    profile = get_object_or_404(FacultyProfile, id=faculty_id)
    form = FacultyForm(request.POST or None, instance=profile)

    if request.method == 'POST' and form.is_valid():
        profile.user.email = form.cleaned_data['email']
        profile.user.contact = form.cleaned_data['contact']
        if form.cleaned_data.get('password'):
            profile.user.set_password(form.cleaned_data['password'])
        profile.user.save()
        form.save()
        messages.success(request, f"Faculty account updated for {profile.full_name}.")
        return redirect('accounts:faculty_list')

    return render(request, 'accounts/faculty_form.html', {
        'form': form, 'profile': profile, 'active_page': 'faculty',
    })


@superadmin_required
@require_POST
def faculty_toggle_active_view(request, faculty_id):
    profile = get_object_or_404(FacultyProfile, id=faculty_id)
    user = profile.user
    if user.account_status == User.AccountStatus.ACTIVE:
        user.account_status = User.AccountStatus.DISABLED
        user.is_active = False
        state = "disabled"
    else:
        user.account_status = User.AccountStatus.ACTIVE
        user.is_active = True
        state = "activated"
    user.account_status_updated_at = timezone.now()
    user.save(update_fields=['account_status', 'is_active', 'account_status_updated_at'])
    messages.success(request, f"{profile.full_name}'s account has been {state}.")
    return redirect('accounts:faculty_list')


@superadmin_required
@require_POST
def faculty_delete_view(request, faculty_id):
    profile = get_object_or_404(FacultyProfile, id=faculty_id)
    name = profile.full_name
    profile.user.delete()   # cascades to FacultyProfile
    messages.success(request, f"Faculty account for {name} deleted.")
    return redirect('accounts:faculty_list')