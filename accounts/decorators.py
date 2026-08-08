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



def admin_or_faculty_required(view_func):
    """
    For views that BOTH content admins/superadmins AND faculty should reach —
    student management, enrollment/course-access management, assignment
    management and grading. Superadmin- or admin-only pages (courses, domains,
    announcements, centres, bulk upload, certificate designs, admin/faculty
    management, and the destructive user-access actions) must keep using
    admin_required / superadmin_required instead — do not widen those.
    """
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_staff_area_role:
            messages.error(request, "You don't have permission to access this page.")
            return redirect('accounts:admin_login')
        return view_func(request, *args, **kwargs)
    return _wrapped


def faculty_required(view_func):
    """Faculty-only views — e.g. the faculty-specific dashboard landing page."""
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated or request.user.role != request.user.Role.FACULTY:
            messages.error(request, "You don't have permission to access this page.")
            return redirect('accounts:admin_login')
        return view_func(request, *args, **kwargs)
    return _wrapped


def course_management_required(view_func):
    """
    Gates course create/edit/delete/publish actions specifically.
    Superadmin always passes. Content admin passes only if their
    AdminProfile.can_manage_courses is True. Faculty never reaches
    this at all (their sidebar never links here, and course views
    stay outside admin_or_faculty_required).
    """
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        user = request.user
        if not user.is_authenticated:
            messages.error(request, "Please log in.")
            return redirect('accounts:admin_login')

        if user.role == user.Role.SUPERADMIN:
            return view_func(request, *args, **kwargs)

        if user.role == user.Role.ADMIN:
            profile = getattr(user, 'admin_profile', None)
            if profile and profile.can_manage_courses:
                return view_func(request, *args, **kwargs)

        messages.error(request, "You don't have permission to manage courses. Contact a superadmin.")
        return redirect('course:manage_list')
    return _wrapped