from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.db.models import Q
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse
from django.utils import timezone

from accounts.decorators import admin_required
from admin_dashboard.notifications import notify_users
from course.models import Course
from .models import CertificateDesign, StudentCertificate
from .forms import CertificateDesignForm, ManualIssueForm
from .eligibility import is_eligible_for_certificate
from .utils import get_or_generate_qr_code
import requests


def build_certificate_context(request, certificate):
    """Single source of truth for certificate template context."""
    user = certificate.user
    course = certificate.course
    profile = getattr(user, 'learner_profile', None)
    design = certificate.design or CertificateDesign.objects.filter(is_active=True).first()

    verification_url = request.build_absolute_uri(
        reverse('certificate:verify_certificate', args=[certificate.certificate_number])
    ) if certificate.certificate_number else None

    return {
        'certificate': certificate,
        'design': design,
        'student_name': getattr(profile, 'full_name', None) or user.email,
        'course_name': course.course_name,
        'registration_number': getattr(profile, 'enrollment_number', None) or '',
        'centre_name': user.nielit_centre.centre_name if user.nielit_centre else '',
        'institute_name': design.header_title if design else 'NIELIT Delhi',
        'verification_url': verification_url,
    }


# ══════════════════ STUDENT ══════════════════

@login_required(login_url='user:login')
@require_POST
def request_certificate_view(request, course_slug):
    course = get_object_or_404(Course, slug=course_slug)

    eligible, reason = is_eligible_for_certificate(request.user, course)
    if not eligible:
        messages.error(request, reason)
        return redirect('course:my_courses')

    certificate, created = StudentCertificate.objects.get_or_create(
        user=request.user, course=course,
        defaults={'design': CertificateDesign.objects.filter(is_active=True).first()},
    )

    if not created and certificate.status in (StudentCertificate.Status.DENIED, StudentCertificate.Status.REVOKED):
        certificate.status = StudentCertificate.Status.REQUESTED
        certificate.status_updated_at = None
        certificate.save(update_fields=['status', 'status_updated_at'])
        messages.success(request, "Certificate re-requested. An admin will review your request.")
    elif created:
        messages.success(request, "Certificate requested! An admin will review and approve it shortly.")
    else:
        messages.info(request, f"You already have a certificate request with status: {certificate.get_status_display()}.")

    return redirect('course:my_courses')


@login_required(login_url='user:login')
def view_certificate(request, certificate_number):
    certificate = get_object_or_404(StudentCertificate, certificate_number=certificate_number)

    if certificate.user_id != request.user.id and not getattr(request.user, 'is_admin_role', False):
        messages.error(request, "You don't have permission to view this certificate.")
        return redirect('user_dashboard:home')

    if certificate.status != StudentCertificate.Status.APPROVED:
        messages.error(request, "This certificate is not yet approved.")
        return redirect('course:my_courses')

    context = build_certificate_context(request, certificate)
    return render(request, 'certificate/view_certificate.html', context)


def verify_certificate(request, cert_number):
    """Public certificate verification — no login required."""
    try:
        certificate = StudentCertificate.objects.select_related(
            'user', 'user__learner_profile', 'user__nielit_centre', 'course'
        ).get(certificate_number=cert_number, status=StudentCertificate.Status.APPROVED)
        context = {'is_valid': True, 'certificate': certificate}
    except StudentCertificate.DoesNotExist:
        context = {'is_valid': False, 'certificate_number': cert_number}
    return render(request, 'certificate/verify_certificate.html', context)


@require_GET
def certificate_qr_code(request, cert_number):
    try:
        certificate = StudentCertificate.objects.get(certificate_number=cert_number)
        verification_url = request.build_absolute_uri(
            reverse('certificate:verify_certificate', args=[certificate.certificate_number])
        )
        qr_data = get_or_generate_qr_code(certificate.certificate_number, verification_url)

        response = HttpResponse(qr_data, content_type='image/png')
        response['Content-Disposition'] = f'inline; filename="qr_{certificate.certificate_number}.png"'
        response['Cache-Control'] = 'public, max-age=604800'
        return response
    except StudentCertificate.DoesNotExist:
        return HttpResponse(status=404)


# @csrf_exempt
# def image_proxy(request):
#     """Proxies S3-hosted logos/signatures/QR around CORS restrictions for html2canvas."""
#     import requests
#     url = request.GET.get('url', '')
#     if not url:
#         return HttpResponse(status=400)
#     try:
#         resp = requests.get(url, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
#         content_type = resp.headers.get('Content-Type', 'image/png')
#         response = HttpResponse(resp.content, content_type=content_type)
#         response['Access-Control-Allow-Origin'] = '*'
#         response['Cache-Control'] = 'public, max-age=3600'
#         return response
#     except Exception:
#         return HttpResponse(status=500)


# ══════════════════ ADMIN: Certificate Designs ══════════════════

@admin_required
def design_list(request):
    designs = CertificateDesign.objects.all()
    return render(request, 'certificate/admin/design_list.html', {'designs': designs, 'active_page': 'certificates'})


@admin_required
def design_create(request):
    if request.method == 'POST':
        form = CertificateDesignForm(request.POST, request.FILES)
        if form.is_valid():
            design = form.save()
            messages.success(request, f'Certificate design "{design.certificate_title}" created successfully!')
            return redirect('certificate:design_list')
    else:
        form = CertificateDesignForm()
    return render(request, 'certificate/admin/design_form.html', {'form': form, 'title': 'Create Certificate Design', 'active_page': 'certificates'})


@admin_required
def design_edit(request, pk):
    design = get_object_or_404(CertificateDesign, pk=pk)
    if request.method == 'POST':
        form = CertificateDesignForm(request.POST, request.FILES, instance=design)
        if form.is_valid():
            form.save()
            messages.success(request, f'Certificate design "{design.certificate_title}" updated successfully!')
            return redirect('certificate:design_list')
    else:
        form = CertificateDesignForm(instance=design)
    return render(request, 'certificate/admin/design_form.html', {'form': form, 'title': 'Edit Certificate Design', 'design': design, 'active_page': 'certificates'})


@admin_required
def design_preview(request, pk):
    design = get_object_or_404(CertificateDesign, pk=pk)
    return render(request, 'certificate/admin/design_preview.html', {'design': design, 'active_page': 'certificates'})


@admin_required
def design_delete(request, pk):
    design = get_object_or_404(CertificateDesign, pk=pk)
    if request.method == 'POST':
        design_name = design.certificate_title
        design.delete()
        messages.success(request, f'Certificate design "{design_name}" deleted successfully!')
        return redirect('certificate:design_list')
    return render(request, 'certificate/admin/design_confirm_delete.html', {'design': design, 'active_page': 'certificates'})


# ══════════════════ ADMIN: Manual single-record issue ══════════════════

@admin_required
def issue_certificate_view(request, certificate_id):
    """
    Manual approval/issue for one specific certificate request — the
    single-record counterpart to the bulk-approve action on the
    certificate_management page. Useful when an admin wants to review
    one request in detail (add remarks, pick a specific design) rather
    than bulk-approving.
    """
    certificate = get_object_or_404(StudentCertificate.objects.select_related('user', 'user__learner_profile', 'course'), id=certificate_id)
    design = CertificateDesign.objects.filter(is_active=True).first()

    if request.method == 'POST':
        form = ManualIssueForm(request.POST)
        if form.is_valid():
            certificate.design = design
            certificate.remarks = form.cleaned_data['remarks']
            certificate.issued_by_name = form.cleaned_data['issued_by'] or 'NIELIT Administration'
            certificate.approve(approved_by=request.user)

            notify_users(
                [certificate.user],
                title="Certificate Approved",
                message=f"Your certificate for {certificate.course.course_name} has been approved! You can now view and download it from your dashboard.",
                created_by=request.user,
            )
            messages.success(request, f'Certificate issued! Certificate No: {certificate.certificate_number}')
            return redirect('certificate:certificate_management')
    else:
        form = ManualIssueForm(initial={'issued_by': request.user.email})

    return render(request, 'certificate/admin/issue_certificate.html', {
        'form': form, 'certificate': certificate, 'design': design, 'active_page': 'certificates',
    })


# ══════════════════ ADMIN: Certificate Requests (bulk management) ══════════════════

@admin_required
def certificate_management_view(request):
    certificates = StudentCertificate.objects.select_related(
        'user', 'user__nielit_centre', 'course'
    ).order_by('-requested_at')

    query = request.GET.get('q', '').strip()
    if query:
        certificates = certificates.filter(
            Q(user__email__icontains=query) |
            Q(user__batch_code__icontains=query) |
            Q(course__course_name__icontains=query) |
            Q(certificate_number__icontains=query)
        )

    course_id = request.GET.get('course', '').strip()
    if course_id:
        certificates = certificates.filter(course_id=course_id)

    status_filter = request.GET.get('status', '').strip()
    if status_filter:
        certificates = certificates.filter(status=status_filter)

    centre_id = request.GET.get('centre', '').strip()
    if centre_id:
        certificates = certificates.filter(user__nielit_centre_id=centre_id)

    batch_code = request.GET.get('batch_code', '').strip()
    if batch_code:
        certificates = certificates.filter(user__batch_code__iexact=batch_code)

    base = StudentCertificate.objects.all()
    if query:
        base = base.filter(
            Q(user__email__icontains=query) | Q(user__batch_code__icontains=query) |
            Q(course__course_name__icontains=query) | Q(certificate_number__icontains=query)
        )
    if course_id:
        base = base.filter(course_id=course_id)
    if centre_id:
        base = base.filter(user__nielit_centre_id=centre_id)
    if batch_code:
        base = base.filter(user__batch_code__iexact=batch_code)

    requested_count = base.filter(status=StudentCertificate.Status.REQUESTED).count()
    approved_count = base.filter(status=StudentCertificate.Status.APPROVED).count()
    revoked_count = base.filter(status=StudentCertificate.Status.REVOKED).count()
    denied_count = base.filter(status=StudentCertificate.Status.DENIED).count()

    from admin_dashboard.models import Centre
    from accounts.models import User

    return render(request, 'certificate/admin/certificate_management.html', {
        'certificates': certificates,
        'all_courses': Course.objects.filter(status=Course.Status.ACTIVE).order_by('course_name'),
        'all_centres': Centre.objects.filter(is_active=True).order_by('centre_name'),
        'all_batch_codes': User.objects.filter(role=User.Role.USER).exclude(batch_code='').values_list('batch_code', flat=True).distinct().order_by('batch_code'),
        'selected_course': course_id,
        'selected_status': status_filter,
        'selected_centre': centre_id,
        'selected_batch_code': batch_code,
        'query': query,
        'requested_count': requested_count,
        'approved_count': approved_count,
        'revoked_count': revoked_count,
        'denied_count': denied_count,
        'active_page': 'certificates',
    })


def _bulk_update_certificate_status(request, action):
    cert_ids = request.POST.getlist('certificate_ids[]')
    certificates = list(StudentCertificate.objects.filter(id__in=cert_ids).select_related('user', 'course'))

    for certificate in certificates:
        if action == 'approve':
            certificate.approve(approved_by=request.user)
        elif action == 'revoke':
            certificate.status = StudentCertificate.Status.REVOKED
            certificate.status_updated_at = timezone.now()
            certificate.save(update_fields=['status', 'status_updated_at'])
        elif action == 'deny':
            certificate.status = StudentCertificate.Status.DENIED
            certificate.status_updated_at = timezone.now()
            certificate.save(update_fields=['status', 'status_updated_at'])

    messages_map = {
        'approve': ("Certificate Approved", "Your certificate for {course} has been approved! You can now view and download it from your dashboard."),
        'revoke': ("Certificate Revoked", "Your certificate for {course} has been revoked by an administrator."),
        'deny': ("Certificate Request Denied", "Your certificate request for {course} has been denied. Contact the administrator for details."),
    }
    title, template = messages_map[action]

    for certificate in certificates:
        notify_users(
            [certificate.user],
            title=title,
            message=template.format(course=certificate.course.course_name),
            created_by=request.user,
        )

    return JsonResponse({'success': True, 'count': len(certificates)})


@admin_required
@require_POST
def bulk_approve_certificates_view(request):
    return _bulk_update_certificate_status(request, 'approve')


@admin_required
@require_POST
def bulk_revoke_certificates_view(request):
    return _bulk_update_certificate_status(request, 'revoke')


@admin_required
@require_POST
def bulk_deny_certificates_view(request):
    return _bulk_update_certificate_status(request, 'deny')


@admin_required
@require_POST
def bulk_delete_certificates_view(request):
    cert_ids = request.POST.getlist('certificate_ids[]')
    count = StudentCertificate.objects.filter(id__in=cert_ids).count()
    StudentCertificate.objects.filter(id__in=cert_ids).delete()
    return JsonResponse({'success': True, 'count': count})

@login_required(login_url='user:login')
def my_certificates_view(request):
    certificates = StudentCertificate.objects.filter(user=request.user).select_related('course').order_by('-requested_at')
    return render(request, 'certificate/my_certificates.html', {
        'certificates': certificates,
        'active_page': 'certificates',
    })

@csrf_exempt
def image_proxy(request):
    """
    Proxy images through Django to avoid CORS issues with S3 and other sources.
    No auth required — only serves images, not sensitive data.
    """
    url = request.GET.get('url', '')

    if not url:
        return HttpResponse(status=400)

    try:
        resp = requests.get(
            url,
            timeout=15,
            headers={
                'User-Agent': 'Mozilla/5.0',
            }
        )
        content_type = resp.headers.get('Content-Type', 'image/png')
        response = HttpResponse(resp.content, content_type=content_type)
        response['Access-Control-Allow-Origin'] = '*'
        response['Cache-Control'] = 'public, max-age=3600'
        return response

    except Exception as e:
        print(f'Image proxy error: {e}')
        return HttpResponse(status=500)