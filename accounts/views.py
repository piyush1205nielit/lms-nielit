from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect,  get_object_or_404
from .decorators import admin_required

from .decorators import superadmin_required
from .forms import AdminLoginForm, AdminCreateForm, AdminEditForm
from .models import User, AdminProfile
from django.contrib.auth.forms import SetPasswordForm





def admin_login_view(request):
    if request.user.is_authenticated and request.user.is_admin_role:
        return redirect('admin_dashboard:home')

    form = AdminLoginForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        identifier = form.cleaned_data['identifier']   # email or contact
        password = form.cleaned_data['password']
        user = authenticate(request, username=identifier, password=password)

        if user is not None and user.is_admin_role:
            login(request, user)
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