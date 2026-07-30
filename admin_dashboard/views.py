from django.shortcuts import render
from accounts.decorators import admin_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage
from django.db.models import Q, Count, Prefetch
from django.http import JsonResponse
from django.template.loader import render_to_string
from accounts.decorators import admin_required, superadmin_required
from django.views.decorators.http import require_POST
from user.models import LearnerProfile
from accounts.models import User
from .forms import AdminUserProfileEditForm, UserCredentialsForm
from course.models import Course, Domain, Enrollment, Progress
from user.forms import ProfileEditForm  
from .models import Centre
from .forms import CentreForm
from django.utils import timezone
from .notifications import notify_users
from user.utils import generate_enrollment_number 


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
        'all_centres': Centre.objects.filter(is_active=True).only('id', 'centre_name').order_by('centre_name'),
        'all_batch_codes': (
            User.objects.filter(role=User.Role.USER)
            .exclude(batch_code='')
            .values_list('batch_code', flat=True)
            .distinct()
            .order_by('batch_code')
        ),
        'active_page': 'users',
    })


@admin_required
def registered_users_data_view(request):
    """
    AJAX endpoint — does all filtering on lightweight fields first,
    paginates the ID list, and only then attaches the expensive
    related data (enrollments) to the single page of results.
    """
    profiles = LearnerProfile.objects.select_related('user', 'user__nielit_centre')

    query = request.GET.get('q', '').strip()
    if query:
        profiles = profiles.filter(
            Q(full_name__icontains=query) |
            Q(user__email__icontains=query) |
            Q(user__contact__icontains=query) |
            Q(user__batch_code__icontains=query) |
            Q(enrollment_number__icontains=query)
        )

    course_id = request.GET.get('course', '').strip()
    if course_id:
        profiles = profiles.filter(user__enrollments__course_id=course_id)

    domain_id = request.GET.get('domain', '').strip()
    if domain_id:
        profiles = profiles.filter(user__enrollments__course__domains__id=domain_id)

    centre_id = request.GET.get('centre', '').strip()
    if centre_id:
        profiles = profiles.filter(user__nielit_centre_id=centre_id)

    batch_code = request.GET.get('batch_code', '').strip()
    if batch_code:
        profiles = profiles.filter(user__batch_code__iexact=batch_code)

    status = request.GET.get('status', '').strip()
    if status == 'complete':
        profiles = profiles.filter(profile_completed=True)
    elif status == 'incomplete':
        profiles = profiles.filter(profile_completed=False)

    profiles = profiles.distinct().order_by('-created_at')

    # stat counts reflect the current filter set (minus the status filter itself,
    # since complete/incomplete IS what those two counts represent)
    status_agnostic = profiles
    if status:
        # re-derive without the status filter so both counts stay meaningful together
        status_agnostic = LearnerProfile.objects.select_related('user', 'user__nielit_centre')
        if query:
            status_agnostic = status_agnostic.filter(
                Q(full_name__icontains=query) |
                Q(user__email__icontains=query) |
                Q(user__contact__icontains=query) |
                Q(user__batch_code__icontains=query) |
                Q(enrollment_number__icontains=query)
            )
        if course_id:
            status_agnostic = status_agnostic.filter(user__enrollments__course_id=course_id)
        if domain_id:
            status_agnostic = status_agnostic.filter(user__enrollments__course__domains__id=domain_id)
        if centre_id:
            status_agnostic = status_agnostic.filter(user__nielit_centre_id=centre_id)
        if batch_code:
            status_agnostic = status_agnostic.filter(user__batch_code__iexact=batch_code)
        status_agnostic = status_agnostic.distinct()

    complete_count = status_agnostic.filter(profile_completed=True).count()
    incomplete_count = status_agnostic.filter(profile_completed=False).count()

    page_number = request.GET.get('page', 1)
    per_page = 20

    paginator = Paginator(profiles.values_list('id', flat=True), per_page)
    try:
        page = paginator.page(page_number)
    except EmptyPage:
        return JsonResponse({
            'html': '', 'has_next': False, 'total_count': paginator.count,
            'complete_count': complete_count, 'incomplete_count': incomplete_count,
        })

    page_profile_ids = list(page.object_list)
    page_profiles = LearnerProfile.objects.filter(id__in=page_profile_ids).select_related(
        'user', 'user__nielit_centre'
    ).prefetch_related(
        Prefetch('user__enrollments', queryset=Enrollment.objects.select_related('course'))
    ).annotate(
        enrollment_count=Count('user__enrollments', distinct=True)
    )
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
        'complete_count': complete_count,
        'incomplete_count': incomplete_count,
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
        profile = LearnerProfile.objects.create(
            user=student, 
            enrollment_number=generate_enrollment_number(),
        )

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


@admin_required
def centre_list_view(request):
    centres = Centre.objects.annotate(user_count=Count('users')).order_by('centre_name')
    return render(request, 'admin_dashboard/centre_manage.html', {
        'centres': centres, 'active_page': 'centres',
    })


@admin_required
def centre_modal_view(request, centre_id=None):
    centre = get_object_or_404(Centre, id=centre_id) if centre_id else None

    if request.method == 'POST':
        form = CentreForm(request.POST, instance=centre)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True})
        return JsonResponse({'success': False, 'errors': form.errors}, status=400)

    form = CentreForm(instance=centre)
    html = render_to_string('admin_dashboard/includes/centre_form_modal.html', {
        'form': form, 'centre': centre,
    }, request=request)
    return JsonResponse({'html': html})


@admin_required
@require_POST
def centre_delete_view(request, centre_id):
    centre = get_object_or_404(Centre, id=centre_id)
    if centre.users.exists():
        return JsonResponse({'success': False, 'message': 'Cannot delete — students are still linked to this centre.'}, status=400)
    centre.delete()
    return JsonResponse({'success': True})

@admin_required
def registration_requests_view(request):
    users = User.objects.filter(
        role=User.Role.USER, account_status=User.AccountStatus.PENDING
    ).select_related('nielit_centre').order_by('-date_joined')

    query = request.GET.get('q', '').strip()
    if query:
        users = users.filter(
            Q(email__icontains=query) |
            Q(contact__icontains=query) |
            Q(batch_code__icontains=query)
        )

    batch_code = request.GET.get('batch_code', '').strip()
    if batch_code:
        users = users.filter(batch_code__iexact=batch_code)

    centre_id = request.GET.get('centre', '').strip()
    if centre_id:
        users = users.filter(nielit_centre_id=centre_id)

    # distinct batch codes among currently-pending users, for the filter dropdown —
    # only shows codes that are actually relevant right now, not every code ever used
    all_batch_codes = (
        User.objects.filter(role=User.Role.USER, account_status=User.AccountStatus.PENDING)
        .exclude(batch_code='')
        .values_list('batch_code', flat=True)
        .distinct()
        .order_by('batch_code')
    )

    return render(request, 'admin_dashboard/registration_requests.html', {
        'users': users,
        'all_batch_codes': all_batch_codes,
        'all_centres': Centre.objects.filter(is_active=True).order_by('centre_name'),
        'query': query,
        'selected_batch_code': batch_code,
        'selected_centre': centre_id,
        'active_page': 'registrations',
    })


@admin_required
@require_POST
def bulk_approve_registrations_view(request):
    user_ids = request.POST.getlist('user_ids[]')
    users = list(User.objects.filter(id__in=user_ids, account_status=User.AccountStatus.PENDING))

    User.objects.filter(id__in=[u.id for u in users]).update(
        account_status=User.AccountStatus.ACTIVE, is_active=True, account_status_updated_at=timezone.now()
    )
    notify_users(
        users,
        title="Your account has been approved",
        message="Your NIELIT LMS account has been approved. You can now log in and enroll in courses.",
        created_by=request.user,
    )
    return JsonResponse({'success': True, 'count': len(users)})


@admin_required
@require_POST
def bulk_deny_registrations_view(request):
    user_ids = request.POST.getlist('user_ids[]')
    count = User.objects.filter(id__in=user_ids, account_status=User.AccountStatus.PENDING).count()
    User.objects.filter(id__in=user_ids, account_status=User.AccountStatus.PENDING).delete()
    return JsonResponse({'success': True, 'count': count})

@admin_required
def user_access_management_view(request):
    users = User.objects.filter(role=User.Role.USER).select_related('nielit_centre').order_by('-date_joined')

    query = request.GET.get('q', '').strip()
    if query:
        users = users.filter(
            Q(email__icontains=query) |
            Q(contact__icontains=query) |
            Q(batch_code__icontains=query)
        )

    status_filter = request.GET.get('status', '').strip()
    if status_filter:
        users = users.filter(account_status=status_filter)

    centre_id = request.GET.get('centre', '').strip()
    if centre_id:
        users = users.filter(nielit_centre_id=centre_id)

    batch_code = request.GET.get('batch_code', '').strip()
    if batch_code:
        users = users.filter(batch_code__iexact=batch_code)

    # counts reflect the current filter set (search/centre/batch), excluding
    # the status filter itself, since the four cards ARE the status breakdown
    base = User.objects.filter(role=User.Role.USER)
    if query:
        base = base.filter(
            Q(email__icontains=query) |
            Q(contact__icontains=query) |
            Q(batch_code__icontains=query)
        )
    if centre_id:
        base = base.filter(nielit_centre_id=centre_id)
    if batch_code:
        base = base.filter(batch_code__iexact=batch_code)

    active_count = base.filter(account_status=User.AccountStatus.ACTIVE).count()
    pending_count = base.filter(account_status=User.AccountStatus.PENDING).count()
    disabled_count = base.filter(account_status=User.AccountStatus.DISABLED).count()
    revoked_count = base.filter(account_status=User.AccountStatus.REVOKED).count()

    all_batch_codes = (
        User.objects.filter(role=User.Role.USER)
        .exclude(batch_code='')
        .values_list('batch_code', flat=True)
        .distinct()
        .order_by('batch_code')
    )

    return render(request, 'admin_dashboard/user_access_management.html', {
        'users': users,
        'all_centres': Centre.objects.filter(is_active=True).order_by('centre_name'),
        'all_batch_codes': all_batch_codes,
        'query': query,
        'selected_status': status_filter,
        'selected_centre': centre_id,
        'selected_batch_code': batch_code,
        'active_count': active_count,
        'pending_count': pending_count,
        'disabled_count': disabled_count,
        'revoked_count': revoked_count,
        'active_page': 'user_access',
    })


def _bulk_update_account_status(request, new_status, is_active_flag, title, message_template):
    user_ids = request.POST.getlist('user_ids[]')
    users = list(User.objects.filter(id__in=user_ids, role=User.Role.USER))
    User.objects.filter(id__in=[u.id for u in users]).update(
        account_status=new_status, is_active=is_active_flag, account_status_updated_at=timezone.now()
    )
    notify_users(users, title=title, message=message_template, created_by=request.user)
    return JsonResponse({'success': True, 'count': len(users)})


@admin_required
@require_POST
def bulk_grant_access_view(request):
    return _bulk_update_account_status(
        request, User.AccountStatus.ACTIVE, True,
        "Account Access Granted", "Your account access has been granted. You can now log in.",
    )


@superadmin_required
@require_POST
def bulk_revoke_access_view(request):
    return _bulk_update_account_status(
        request, User.AccountStatus.REVOKED, False,
        "Account Access Revoked", "Your account access has been revoked. Contact the administrator for details.",
    )


@superadmin_required
@require_POST
def bulk_disable_access_view(request):
    return _bulk_update_account_status(
        request, User.AccountStatus.DISABLED, False,
        "Account Temporarily Disabled", "Your account has been temporarily disabled by an administrator.",
    )


@superadmin_required
@require_POST
def bulk_delete_accounts_view(request):
    user_ids = request.POST.getlist('user_ids[]')
    count = User.objects.filter(id__in=user_ids, role=User.Role.USER).count()
    User.objects.filter(id__in=user_ids, role=User.Role.USER).delete()
    return JsonResponse({'success': True, 'count': count})

from django.http import HttpResponse
from .forms import BulkUserUploadForm
from .utils import build_upload_template, parse_and_validate_upload, create_users_from_rows
from .notifications import notify_users


@admin_required
def bulk_user_upload_view(request):
    form = BulkUserUploadForm(request.POST or None, request.FILES or None)
    errors = []
    created_count = 0

    if request.method == 'POST' and form.is_valid():
        valid_rows, errors = parse_and_validate_upload(form.cleaned_data['excel_file'])

        if not errors:
            created_users, common_password = create_users_from_rows(valid_rows, created_by=request.user)
            created_count = len(created_users)

            _send_credential_emails(created_users, common_password)
            notify_users(
                created_users,
                title="Your NIELIT LMS account has been created",
                message=(
                    f"An account has been created for you on NIELIT LMS.\n\n"
                    f"Login using your registered email or contact number with the password "
                    f"sent to your email. Please complete your profile after logging in to "
                    f"access courses."
                ),
                created_by=request.user,
            )
            messages.success(request, f"{created_count} student account(s) created and notified successfully.")
            return redirect('admin_dashboard:bulk_user_upload')

    return render(request, 'admin_dashboard/bulk_user_upload.html', {
        'form': form,
        'errors': errors,
        'active_page': 'bulk_upload',
    })


@admin_required
def download_upload_template_view(request):
    buffer = build_upload_template()
    response = HttpResponse(
        buffer.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="student_upload_template.xlsx"'
    return response


def _send_credential_emails(users, common_password):
    from django.core.mail import send_mail
    from django.conf import settings

    for user in users:
        try:
            send_mail(
                subject="Your NIELIT LMS Login Credentials",
                message=(
                    f"Your NIELIT LMS account has been created.\n\n"
                    f"Login Email: {user.email}\n"
                    f"Login Contact: {user.contact}\n"
                    f"Password: {common_password}\n\n"
                    f"Log in at the LMS portal using either your email or contact number, "
                    f"along with the password above. For security, we recommend completing "
                    f"your profile immediately after your first login.\n\n"
                    f"Note: this is a shared initial password. Please do not share it further."
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=True,
            )
        except Exception:
            pass