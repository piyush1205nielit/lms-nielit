from django.shortcuts import render
from accounts.decorators import admin_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage
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
    """Renders the page shell only — the table itself loads via AJAX."""
    return render(request, 'admin_dashboard/registered_users_list.html', {
        'all_courses': Course.objects.filter(status=Course.Status.ACTIVE).only('id', 'course_name').order_by('course_name'),
        'all_domains': Domain.objects.filter(is_active=True).only('id', 'name').order_by('name'),
        'active_page': 'users',
    })

@admin_required
def registered_users_data_view(request):
    """
    AJAX endpoint — does all filtering on lightweight fields first,
    paginates the ID list, and only then attaches the expensive
    related data (enrollments) to the single page of results.
    """
    profiles = LearnerProfile.objects.select_related('user')

    query = request.GET.get('q', '').strip()
    if query:
        profiles = profiles.filter(
            Q(full_name__icontains=query) |
            Q(user__email__icontains=query) |
            Q(user__contact__icontains=query) |
            Q(enrollment_number__icontains=query)
        )

    course_id = request.GET.get('course', '').strip()
    if course_id:
        profiles = profiles.filter(user__enrollments__course_id=course_id)

    domain_id = request.GET.get('domain', '').strip()
    if domain_id:
        profiles = profiles.filter(user__enrollments__course__domains__id=domain_id)

    status = request.GET.get('status', '').strip()
    if status == 'complete':
        profiles = profiles.filter(profile_completed=True)
    elif status == 'incomplete':
        profiles = profiles.filter(profile_completed=False)

    # distinct() is only needed when the course/domain filters introduce M2M/FK
    # join duplication — cheap to always apply here since it's on an already-narrowed set
    profiles = profiles.distinct().order_by('-created_at')

    page_number = request.GET.get('page', 1)
    per_page = 20

    paginator = Paginator(profiles.values_list('id', flat=True), per_page)
    try:
        page = paginator.page(page_number)
    except EmptyPage:
        return JsonResponse({'html': '', 'has_next': False, 'total_count': paginator.count})

    # Only now — for this one page's worth of IDs — do the expensive join/prefetch
    page_profile_ids = list(page.object_list)
    page_profiles = LearnerProfile.objects.filter(id__in=page_profile_ids).select_related(
        'user'
    ).prefetch_related(
        Prefetch('user__enrollments', queryset=Enrollment.objects.select_related('course'))
    ).annotate(
        enrollment_count=Count('user__enrollments', distinct=True)
    )
    # preserve the original ordering (created_at desc) — filtering by id__in loses row order
    page_profiles_by_id = {p.id: p for p in page_profiles}
    ordered_page_profiles = [page_profiles_by_id[pid] for pid in page_profile_ids if pid in page_profiles_by_id]

    html = render_to_string('admin_dashboard/includes/students_table_rows.html', {
        'profiles': ordered_page_profiles,
        'request': request,
    })

    return JsonResponse({
        'html': html,
        'has_next': page.has_next(),
        'has_previous': page.has_previous(),
        'current_page': page.number,
        'total_pages': paginator.num_pages,
        'total_count': paginator.count,
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