from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages


def admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_admin_role:
            messages.error(request, "Please log in with an admin account.")
            return redirect('accounts:admin_login')
        return view_func(request, *args, **kwargs)
    return wrapper


def superadmin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or request.user.role != 'superadmin':
            messages.error(request, "This action requires a super admin account.")
            return redirect('accounts:admin_login')
        return view_func(request, *args, **kwargs)
    return wrapper