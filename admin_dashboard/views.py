from django.shortcuts import render
from accounts.decorators import admin_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count, Prefetch
from django.http import JsonResponse
from django.template.loader import render_to_string
from accounts.decorators import admin_required, superadmin_required
from user.models import LearnerProfile
from accounts.models import User
from .forms import AdminUserProfileEditForm, UserCredentialsForm
from course.models import Course, Domain, Enrollment, Progress
from user.forms import ProfileEditForm  # or a dedicated AdminStudentEditForm, see note below

@admin_required
def dashboard_home(request):
    return render(request, 'admin_dashboard/main_dashboard.html', {'active_page': 'dashboard'})



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



@admin_required
def registered_users_view(request):
    profiles = LearnerProfile.objects.select_related('user').prefetch_related(
        Prefetch('user__enrollments', queryset=Enrollment.objects.select_related('course'))
    ).annotate(
        enrollment_count=Count('user__enrollments', distinct=True)
    )

    # ── Search: name, email, contact, enrollment number ──
    query = request.GET.get('q', '').strip()
    if query:
        profiles = profiles.filter(
            Q(full_name__icontains=query) |
            Q(user__email__icontains=query) |
            Q(user__contact__icontains=query) |
            Q(enrollment_number__icontains=query)
        )

    # ── Filter: specific course ──
    course_id = request.GET.get('course', '').strip()
    if course_id:
        profiles = profiles.filter(user__enrollments__course_id=course_id)

    # ── Filter: specific domain (any course under that domain) ──
    domain_id = request.GET.get('domain', '').strip()
    if domain_id:
        profiles = profiles.filter(user__enrollments__course__domains__id=domain_id)

    # ── Filter: profile completion status ──
    status = request.GET.get('status', '').strip()
    if status == 'complete':
        profiles = profiles.filter(profile_completed=True)
    elif status == 'incomplete':
        profiles = profiles.filter(profile_completed=False)

    profiles = profiles.distinct().order_by('-created_at')

    paginator = Paginator(profiles, 20)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'admin_dashboard/registered_users_list.html', {
        'profiles': page_obj,
        'all_courses': Course.objects.filter(status=Course.Status.ACTIVE).order_by('course_name'),
        'all_domains': Domain.objects.filter(is_active=True).order_by('name'),
        'query': query,
        'selected_course': course_id,
        'selected_domain': domain_id,
        'selected_status': status,
        'active_page': 'users',
    })



@admin_required
def student_detail_modal_view(request, user_id):
    """Returns just the modal's inner HTML for the 'View' action (AJAX-loaded)."""
    student = get_object_or_404(User, id=user_id, role=User.Role.USER)
    profile = getattr(student, 'learner_profile', None)

    enrollments = Enrollment.objects.filter(user=student).select_related('course')
    enrollment_data = []
    for enrollment in enrollments:
        total = enrollment.course.modules.aggregate(
            lesson_count=Count('lessons')
        )['lesson_count'] or 0
        completed = Progress.objects.filter(
            user=student, lesson__module__course=enrollment.course, completed=True
        ).count()
        percent = int((completed / total) * 100) if total else 0
        enrollment_data.append({'enrollment': enrollment, 'percent': percent, 'completed': completed, 'total': total})

    html = render_to_string('admin_dashboard/includes/student_detail_modal.html', {
        'student': student,
        'profile': profile,
        'enrollment_data': enrollment_data,
    }, request=request)
    return JsonResponse({'html': html})


@admin_required
def student_edit_modal_view(request, user_id):
    """GET returns the edit form's inner HTML; POST saves and returns success/errors as JSON."""
    student = get_object_or_404(User, id=user_id, role=User.Role.USER)
    profile = getattr(student, 'learner_profile', None)
    if profile is None:
        profile = LearnerProfile.objects.create(user=student, enrollment_number='PENDING')

    if request.method == 'POST':
        form = ProfileEditForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': f"Profile updated for {student.email}."})
        return JsonResponse({'success': False, 'errors': form.errors}, status=400)

    form = ProfileEditForm(instance=profile)
    html = render_to_string('admin_dashboard/includes/student_edit_modal.html', {
        'form': form,
        'student': student,
    }, request=request)
    return JsonResponse({'html': html})


@superadmin_required
def student_delete_view(request, user_id):
    student = get_object_or_404(User, id=user_id, role=User.Role.USER)
    if request.method == 'POST':
        email = student.email
        student.delete()
        return JsonResponse({'success': True, 'message': f"Account for {email} deleted."})
    return JsonResponse({'success': False}, status=405)