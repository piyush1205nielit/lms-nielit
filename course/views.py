from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from accounts.decorators import admin_required
from .forms import CourseForm, ModuleForm, LessonForm, CoursePublishForm, DomainForm
from .models import Course, Module, Lesson, Enrollment, Domain
from django.contrib.auth.decorators import login_required
from django.conf import settings as django_settings
from django.core.paginator import Paginator
from django.db.models import Count, Sum
from django.views.decorators.http import require_POST
from accounts.models import User
from admin_dashboard.notifications import notify_users
from django.http import JsonResponse
from django.template.loader import render_to_string
from admin_dashboard.models import Centre
from certificate.models import StudentCertificate
from certificate.eligibility import is_eligible_for_certificate


# ── Admin: domain management ──────────────────────────────

@admin_required
def domain_list_view(request):
    domains = Domain.objects.annotate(course_count=Count('courses', distinct=True)).order_by('name')
    active_count = domains.filter(is_active=True).count()
    inactive_count = domains.filter(is_active=False).count()

    return render(request, 'course/domain_list.html', {
        'domains': domains,
        'active_count': active_count,
        'inactive_count': inactive_count,
        'active_page': 'domains',
    })


@admin_required
def domain_modal_view(request, domain_id=None):
    """GET returns the modal's inner HTML (create or edit); POST saves it."""
    domain = get_object_or_404(Domain, id=domain_id) if domain_id else None

    if request.method == 'POST':
        form = DomainForm(request.POST, instance=domain)
        if form.is_valid():
            saved = form.save()
            saved.sync_active_status()   # re-derive immediately in case course associations already exist
            return JsonResponse({'success': True})
        return JsonResponse({'success': False, 'errors': form.errors}, status=400)

    form = DomainForm(instance=domain)
    html = render_to_string('course/includes/domain_form_modal.html', {
        'form': form, 'domain': domain,
    }, request=request)
    return JsonResponse({'html': html})


@admin_required
@require_POST
def domain_toggle_active_view(request, domain_id):
    domain = get_object_or_404(Domain, id=domain_id)
    domain.is_active = not domain.is_active
    domain.save(update_fields=['is_active'])
    return JsonResponse({'success': True, 'is_active': domain.is_active})


@admin_required
@require_POST
def domain_delete_view(request, domain_id):
    domain = get_object_or_404(Domain, id=domain_id)
    if domain.courses.exists():
        return JsonResponse({
            'success': False,
            'message': f"Cannot delete — {domain.courses.count()} course(s) still use this domain.",
        }, status=400)
    domain.delete()
    return JsonResponse({'success': True})


# ── Admin: course management list ──────────────────────────

@admin_required
def manage_list_view(request):
    courses = Course.objects.annotate(
        module_count=Count('modules', distinct=True),
        lesson_count=Count('modules__lessons', distinct=True),
        enrollment_count=Count('enrollments', distinct=True),
        total_duration=Sum('modules__lessons__duration_seconds'),
    ).select_related('created_by').prefetch_related('domains').order_by('-created_at')

    return render(request, 'course/manage_list.html', {
        'courses': courses,
        'active_page': 'courses',
    })


# ── Step 1: Basic Info ──────────────────────────────────────
def courses_view(request):
    course_list = Course.objects.filter(status=Course.Status.ACTIVE).prefetch_related('domains').order_by('-published_date')

    domain_slug = request.GET.get('domain')
    if domain_slug:
        course_list = course_list.filter(domains__slug=domain_slug)

    search_query = request.GET.get('q')
    if search_query:
        course_list = course_list.filter(course_name__icontains=search_query)

    all_domains = Domain.objects.filter(is_active=True).order_by('name')

    paginator = Paginator(course_list.distinct(), 12)
    page_number = request.GET.get('page')
    courses = paginator.get_page(page_number)

    return render(request, 'public/courses.html', {
        'courses': courses,
        'all_domains': all_domains,
        'selected_domain': domain_slug,
    })

@admin_required
def course_create_view(request):
    form = CourseForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        course = form.save(commit=False)
        course.created_by = request.user
        if course.status == Course.Status.ACTIVE:
            course.published_date = timezone.now()
        course.save()
        form.save_m2m()
        messages.success(request, f"'{course.course_name}' created. Now add modules and lessons.")
        return redirect('course:modules', course_id=course.id)

    domain_active_map = {str(d.id): d.is_active for d in Domain.objects.all()}
    return render(request, 'course/course_form.html', {
        'form': form, 'domain_active_map': domain_active_map, 'active_page': 'courses',
    })


@admin_required
def course_edit_view(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    was_active_before = course.status == Course.Status.ACTIVE

    form = CourseForm(request.POST or None, request.FILES or None, instance=course)
    if request.method == 'POST' and form.is_valid():
        updated_course = form.save(commit=False)
        if updated_course.status == Course.Status.ACTIVE and not was_active_before:
            updated_course.published_date = timezone.now()
        updated_course.save()
        form.save_m2m()
        messages.success(request, "Course details updated.")
        return redirect('course:manage_list')

    domain_active_map = {str(d.id): d.is_active for d in Domain.objects.all()}
    return render(request, 'course/course_form.html', {
        'form': form, 'course': course, 'domain_active_map': domain_active_map, 'active_page': 'courses',
    })

# ── Quick actions, used directly from the manage-list row ──────────────

@admin_required
@require_POST
def course_toggle_active_view(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    if course.status == Course.Status.ACTIVE:
        course.status = Course.Status.INACTIVE
    else:
        course.status = Course.Status.ACTIVE
        if not course.published_date:
            course.published_date = timezone.now()
    course.save(update_fields=['status', 'published_date'])
    messages.success(request, f"'{course.course_name}' is now {course.get_status_display()}.")
    return redirect('course:manage_list')


@admin_required
@require_POST
def course_toggle_featured_view(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    course.is_featured = not course.is_featured
    course.save(update_fields=['is_featured'])
    state = "featured on the homepage" if course.is_featured else "removed from featured"
    messages.success(request, f"'{course.course_name}' is now {state}.")
    return redirect('course:manage_list')


@admin_required
@require_POST
def course_delete_view(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    name = course.course_name
    course.delete()
    messages.success(request, f"'{name}' has been permanently deleted.")
    return redirect('course:manage_list')


# ── Step 2: Modules & Lessons (enhanced with duration + status) ──────────

@admin_required
def course_modules_view(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    modules = course.modules.prefetch_related('lessons').order_by('order')

    total_lessons = Lesson.objects.filter(module__course=course).count()
    total_duration = Lesson.objects.filter(module__course=course).aggregate(
        total=Sum('duration_seconds')
    )['total']
    ready_lessons = Lesson.objects.filter(module__course=course, video_status=Lesson.VideoStatus.READY).count()

    return render(request, 'course/course_modules_step2.html', {
        'course': course,
        'modules': modules,
        'total_lessons': total_lessons,
        'total_duration': total_duration,
        'ready_lessons': ready_lessons,
        'active_page': 'courses',
    })

@admin_required
def module_create_view(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    next_order = course.modules.count()   # auto-suggest next order number
    form = ModuleForm(request.POST or None, initial={'order': next_order})

    if request.method == 'POST' and form.is_valid():
        module = form.save(commit=False)
        module.course = course
        module.save()
        messages.success(request, f"Module '{module.title}' added.")
        return redirect('course:modules', course_id=course.id)

    return render(request, 'course/module_form.html', {
        'form': form,
        'course': course,
        'active_page': 'courses',
    })


@admin_required
def module_edit_view(request, module_id):
    module = get_object_or_404(Module, id=module_id)
    form = ModuleForm(request.POST or None, instance=module)

    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Module updated.")
        return redirect('course:modules', course_id=module.course.id)

    return render(request, 'course/module_form.html', {
        'form': form,
        'course': module.course,
        'module': module,
        'active_page': 'courses',
    })


@admin_required
def module_delete_view(request, module_id):
    module = get_object_or_404(Module, id=module_id)
    course_id = module.course.id
    module.delete()
    messages.success(request, "Module and its lessons deleted.")
    return redirect('course:modules', course_id=course_id)


# ── Lessons (within a module) ───────────────────────────────

@admin_required
def lesson_create_view(request, module_id):
    module = get_object_or_404(Module, id=module_id)
    next_order = module.lessons.count()
    form = LessonForm(request.POST or None, request.FILES or None, initial={'order': next_order})

    if request.method == 'POST' and form.is_valid():
        lesson = form.save(commit=False)
        lesson.module = module
        lesson.save()
        messages.success(request, f"Lesson '{lesson.title}' added. Now upload its video.")
        return redirect('course:lesson_edit', lesson_id=lesson.id)   # go straight to the video upload step

    return render(request, 'course/lesson_form.html', {
        'form': form,
        'module': module,
        'active_page': 'courses',
    })


@admin_required
def lesson_edit_view(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)

    # Local-dev-only video upload path (separate from the main details form)
    if request.method == 'POST' and 'upload_local_video' in request.POST:
        video_file = request.FILES.get('video_file_local')
        if video_file:
            lesson.video_file = video_file
            lesson.video_status = Lesson.VideoStatus.READY
            lesson.save(update_fields=['video_file', 'video_status'])
            messages.success(request, "Video uploaded.")
        return redirect('course:lesson_edit', lesson_id=lesson.id)

    form = LessonForm(request.POST or None, request.FILES or None, instance=lesson)

    if request.method == 'POST' and 'title' in request.POST and form.is_valid():
        form.save()
        messages.success(request, "Lesson updated.")
        return redirect('course:modules', course_id=lesson.module.course.id)

    return render(request, 'course/lesson_form.html', {
        'form': form,
        'module': lesson.module,
        'lesson': lesson,
        'active_page': 'courses',
        'settings_use_s3': django_settings.USE_S3,
    })


@admin_required
def lesson_delete_view(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)
    course_id = lesson.module.course.id
    lesson.delete()
    messages.success(request, "Lesson deleted.")
    return redirect('course:modules', course_id=course_id)


# ── Step 3: Publish Settings ─────────────────────────────────

@admin_required
def course_publish_view(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    was_active_before = course.status == Course.Status.ACTIVE

    form = CoursePublishForm(request.POST or None, request.FILES or None, instance=course)

    if request.method == 'POST' and form.is_valid():
        updated_course = form.save(commit=False)
        # set published_date only the first time it goes active — never overwrite it on later edits
        if updated_course.status == Course.Status.ACTIVE and not was_active_before:
            updated_course.published_date = timezone.now()
        updated_course.save()
        messages.success(request, "Course publish settings saved.")
        return redirect('course:manage_list')

    return render(request, 'course/course_publish_step3.html', {
        'form': form,
        'course': course,
        'active_page': 'courses',
    })


# ── Public: course detail page ──────────────────────────────

# def course_detail_view(request, slug):
#     course = get_object_or_404(Course, slug=slug, status=Course.Status.ACTIVE)
#     modules = course.modules.prefetch_related('lessons').order_by('order')
#     is_enrolled = False
#     if request.user.is_authenticated and request.user.role == 'user':
#         is_enrolled = course.enrollments.filter(user=request.user).exists()

#     return render(request, 'course/course_detail.html', {
#         'course': course,
#         'modules': modules,
#         'is_enrolled': is_enrolled,
#     })

@login_required(login_url='user:login')
def course_detail_view(request, slug):
    course = get_object_or_404(Course, slug=slug, status=Course.Status.ACTIVE)
    modules = course.modules.prefetch_related('lessons').order_by('order')
    total_lessons = Lesson.objects.filter(module__course=course).count()

    enrollment = None
    if request.user.is_authenticated:
        enrollment = Enrollment.objects.filter(user=request.user, course=course).first()

    is_enrolled = bool(enrollment and enrollment.access_status == Enrollment.AccessStatus.GRANTED)

    return render(request, 'course/course_detail.html', {
        'course': course,
        'modules': modules,
        'total_lessons': total_lessons,
        'enrollment': enrollment,       
        'is_enrolled': is_enrolled,     
    })


def course_detail_view(request, slug):
    course = get_object_or_404(Course, slug=slug, status=Course.Status.ACTIVE)
    modules = course.modules.prefetch_related('lessons').order_by('order')

    is_enrolled = False
    if request.user.is_authenticated and request.user.role == 'user':
        is_enrolled = is_enrolled = Enrollment.objects.filter(
            user=request.user, course=course, access_status=Enrollment.AccessStatus.GRANTED
            ).exists()

    total_lessons = sum(module.lessons.count() for module in modules)

    return render(request, 'course/course_detail.html', {
        'course': course,
        'modules': modules,
        'is_enrolled': is_enrolled,
        'total_lessons': total_lessons,
    })


# @login_required(login_url='user:login')
# def course_enroll_view(request, slug):
#     course = get_object_or_404(Course, slug=slug, status=Course.Status.ACTIVE)

#     if request.user.account_status != User.AccountStatus.ACTIVE:
#         messages.error(request, "Your account access must be approved by an admin before you can enroll in courses.")
#         return redirect('course:detail', slug=slug)

#     enrollment, created = Enrollment.objects.get_or_create(user=request.user, course=course)
#     if created:
#         messages.success(request, "Enrollment request submitted. You'll get access once approved by an admin.")
#     else:
#         messages.info(request, f"You already have a {enrollment.get_access_status_display().lower()} enrollment for this course.")
#     return redirect('course:detail', slug=slug)

@login_required(login_url='user:login')
def course_enroll_view(request, slug):
    course = get_object_or_404(Course, slug=slug, status=Course.Status.ACTIVE)

    if request.user.account_status != User.AccountStatus.ACTIVE:
        messages.error(request, "Your account access must be approved by an admin before you can enroll in courses.")
        return redirect('course:detail', slug=slug)

    enrollment, created = Enrollment.objects.get_or_create(user=request.user, course=course)
    if created:
        messages.success(request, "Enrollment request submitted! An admin will review and approve your access shortly.")
    else:
        status_messages = {
            Enrollment.AccessStatus.PENDING: "You already have a pending enrollment request for this course.",
            Enrollment.AccessStatus.GRANTED: "You already have access to this course.",
            Enrollment.AccessStatus.HOLD: "Your access to this course is currently on hold. Contact the administrator.",
            Enrollment.AccessStatus.REVOKED: "Your access to this course has been revoked. Contact the administrator.",
        }
        messages.info(request, status_messages.get(enrollment.access_status, "You already have an enrollment record for this course."))

    return redirect('course:detail', slug=slug)


from certificate.models import StudentCertificate
from certificate.eligibility import is_eligible_for_certificate

@login_required(login_url='user:login')
def my_courses_view(request):
    enrollments = Enrollment.objects.filter(user=request.user).select_related('course').prefetch_related('course__domains').order_by('-enrolled_at')

    pending_courses = []
    in_progress_courses = []
    completed_courses = []

    for enrollment in enrollments:
        total_lessons = Lesson.objects.filter(module__course=enrollment.course).count()
        completed_lessons = Progress.objects.filter(
            user=request.user, lesson__module__course=enrollment.course, completed=True
        ).count()
        percent = int((completed_lessons / total_lessons) * 100) if total_lessons else 0

        item = {
            'enrollment': enrollment, 'percent': percent,
            'completed': completed_lessons, 'total': total_lessons,
        }

        if enrollment.access_status == Enrollment.AccessStatus.PENDING:
            pending_courses.append(item)
        elif enrollment.access_status == Enrollment.AccessStatus.GRANTED and enrollment.status == Enrollment.Status.COMPLETED:
            certificate = StudentCertificate.objects.filter(user=request.user, course=enrollment.course).first()
            can_request_cert = False
            if not certificate:
                can_request_cert, _ = is_eligible_for_certificate(request.user, enrollment.course)
            item['certificate'] = certificate
            item['can_request_certificate'] = can_request_cert
            completed_courses.append(item)
        elif enrollment.access_status == Enrollment.AccessStatus.GRANTED:
            in_progress_courses.append(item)
        else:
            # hold / revoked — still worth showing, grouped with pending so the
            # student sees *something* explaining why they can't access it
            pending_courses.append(item)

    return render(request, 'course/my_courses.html', {
        'pending_courses': pending_courses,
        'in_progress_courses': in_progress_courses,
        'completed_courses': completed_courses,
        'total_enrolled': len(enrollments),
        'completed_count': len(completed_courses),
        'active_page': 'my_courses',
    })

from django.db.models import Count, Sum, Q
from course.models import Progress


@admin_required
def course_students_view(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    total_lessons = Lesson.objects.filter(module__course=course).count()

    enrollments = Enrollment.objects.filter(course=course).select_related(
        'user', 'user__learner_profile'
    ).order_by('-enrolled_at')

    enrollment_data = []
    for enrollment in enrollments:
        completed_lessons = Progress.objects.filter(
            user=enrollment.user, lesson__module__course=course, completed=True
        ).count()
        percent = int((completed_lessons / total_lessons) * 100) if total_lessons else 0

        last_activity = Progress.objects.filter(
            user=enrollment.user, lesson__module__course=course
        ).order_by('-last_watched_at').first()

        enrollment_data.append({
            'enrollment': enrollment,
            'completed_lessons': completed_lessons,
            'total_lessons': total_lessons,
            'percent': percent,
            'last_activity': last_activity.last_watched_at if last_activity else None,
        })

    return render(request, 'course/course_students.html', {
        'course': course,
        'enrollment_data': enrollment_data,
        'active_page': 'courses',
    })


@admin_required
def course_overview_view(request, course_id):
    course = get_object_or_404(
        Course.objects.prefetch_related('domains', 'modules__lessons'),
        id=course_id
    )
    modules = course.modules.prefetch_related('lessons').order_by('order')

    total_lessons = Lesson.objects.filter(module__course=course).count()
    total_duration = Lesson.objects.filter(module__course=course).aggregate(total=Sum('duration_seconds'))['total']
    ready_lessons = Lesson.objects.filter(module__course=course, video_status=Lesson.VideoStatus.READY).count()
    failed_lessons = Lesson.objects.filter(module__course=course, video_status=Lesson.VideoStatus.FAILED).count()

    enrollment_count = Enrollment.objects.filter(course=course).count()
    completed_count = Enrollment.objects.filter(course=course, status=Enrollment.Status.COMPLETED).count()

    return render(request, 'course/course_overview.html', {
        'course': course,
        'modules': modules,
        'total_lessons': total_lessons,
        'total_duration': total_duration,
        'ready_lessons': ready_lessons,
        'failed_lessons': failed_lessons,
        'enrollment_count': enrollment_count,
        'completed_count': completed_count,
        'active_page': 'courses',
    })


@admin_required
def enrollment_management_view(request):
    enrollments = Enrollment.objects.select_related(
        'user', 'user__nielit_centre', 'course'
    ).order_by('-enrolled_at')

    course_id = request.GET.get('course', '').strip()
    if course_id:
        enrollments = enrollments.filter(course_id=course_id)

    status_filter = request.GET.get('access_status', '').strip()
    if status_filter:
        enrollments = enrollments.filter(access_status=status_filter)

    centre_id = request.GET.get('centre', '').strip()
    if centre_id:
        enrollments = enrollments.filter(user__nielit_centre_id=centre_id)

    batch_code = request.GET.get('batch_code', '').strip()
    if batch_code:
        enrollments = enrollments.filter(user__batch_code__iexact=batch_code)

    query = request.GET.get('q', '').strip()
    if query:
        enrollments = enrollments.filter(
            Q(user__email__icontains=query) |
            Q(user__batch_code__icontains=query) |
            Q(course__course_name__icontains=query)
        )

    # counts reflect the CURRENT filter set (course/centre/batch/search), so the
    # stat cards stay meaningful when an admin narrows the view — only the status
    # filter itself is excluded from each count's own base queryset, since each
    # card IS a specific status count
    base = Enrollment.objects.all()
    if course_id:
        base = base.filter(course_id=course_id)
    if centre_id:
        base = base.filter(user__nielit_centre_id=centre_id)
    if batch_code:
        base = base.filter(user__batch_code__iexact=batch_code)
    if query:
        base = base.filter(
            Q(user__email__icontains=query) |
            Q(user__batch_code__icontains=query) |
            Q(course__course_name__icontains=query)
        )

    pending_count = base.filter(access_status=Enrollment.AccessStatus.PENDING).count()
    granted_count = base.filter(access_status=Enrollment.AccessStatus.GRANTED).count()
    hold_count = base.filter(access_status=Enrollment.AccessStatus.HOLD).count()
    revoked_count = base.filter(access_status=Enrollment.AccessStatus.REVOKED).count()

    all_batch_codes = (
        User.objects.filter(role=User.Role.USER)
        .exclude(batch_code='')
        .values_list('batch_code', flat=True)
        .distinct()
        .order_by('batch_code')
    )

    return render(request, 'course/enrollment_management.html', {
        'enrollments': enrollments,
        'all_courses': Course.objects.filter(status=Course.Status.ACTIVE).order_by('course_name'),
        'all_centres': Centre.objects.filter(is_active=True).order_by('centre_name'),
        'all_batch_codes': all_batch_codes,
        'selected_course': course_id,
        'selected_status': status_filter,
        'selected_centre': centre_id,
        'selected_batch_code': batch_code,
        'query': query,
        'pending_count': pending_count,
        'granted_count': granted_count,
        'hold_count': hold_count,
        'revoked_count': revoked_count,
        'active_page': 'enrollments',
    })


def _bulk_update_enrollment_status(request, new_status, title, message_template):
    enrollment_ids = request.POST.getlist('enrollment_ids[]')
    enrollments = list(Enrollment.objects.filter(id__in=enrollment_ids).select_related('user', 'course'))
    Enrollment.objects.filter(id__in=[e.id for e in enrollments]).update(
        access_status=new_status, access_status_updated_at=timezone.now()
    )
    users = [e.user for e in enrollments]
    notify_users(users, title=title, message=message_template, created_by=request.user)
    return JsonResponse({'success': True, 'count': len(enrollments)})


@admin_required
@require_POST
def bulk_grant_enrollment_view(request):
    return _bulk_update_enrollment_status(
        request, Enrollment.AccessStatus.GRANTED,
        "Course Access Granted", "Your enrollment request has been approved. You can now access the course content.",
    )


@admin_required
@require_POST
def bulk_hold_enrollment_view(request):
    return _bulk_update_enrollment_status(
        request, Enrollment.AccessStatus.HOLD,
        "Course Access On Hold", "Your access to a course has been temporarily put on hold by an administrator.",
    )


@admin_required
@require_POST
def bulk_revoke_enrollment_view(request):
    return _bulk_update_enrollment_status(
        request, Enrollment.AccessStatus.REVOKED,
        "Course Access Revoked", "Your access to a course has been revoked by an administrator.",
    )


@admin_required
@require_POST
def bulk_deny_enrollment_view(request):
    enrollment_ids = request.POST.getlist('enrollment_ids[]')
    count = Enrollment.objects.filter(id__in=enrollment_ids).count()
    Enrollment.objects.filter(id__in=enrollment_ids).delete()
    return JsonResponse({'success': True, 'count': count})


from certificate.models import StudentCertificate
from certificate.eligibility import is_eligible_for_certificate

@login_required(login_url='user:login')
def my_courses_view(request):
    enrollments = Enrollment.objects.filter(user=request.user).select_related('course').prefetch_related('course__domains').order_by('-enrolled_at')

    pending_courses = []
    in_progress_courses = []
    completed_courses = []

    for enrollment in enrollments:
        total_lessons = Lesson.objects.filter(module__course=enrollment.course).count()
        completed_lessons = Progress.objects.filter(
            user=request.user, lesson__module__course=enrollment.course, completed=True
        ).count()
        percent = int((completed_lessons / total_lessons) * 100) if total_lessons else 0

        item = {
            'enrollment': enrollment, 'percent': percent,
            'completed': completed_lessons, 'total': total_lessons,
        }

        if enrollment.access_status == Enrollment.AccessStatus.PENDING:
            pending_courses.append(item)
        elif enrollment.access_status == Enrollment.AccessStatus.GRANTED and enrollment.status == Enrollment.Status.COMPLETED:
            certificate = StudentCertificate.objects.filter(user=request.user, course=enrollment.course).first()
            can_request_cert = False
            if not certificate:
                can_request_cert, _ = is_eligible_for_certificate(request.user, enrollment.course)
            item['certificate'] = certificate
            item['can_request_certificate'] = can_request_cert
            completed_courses.append(item)
        elif enrollment.access_status == Enrollment.AccessStatus.GRANTED:
            in_progress_courses.append(item)
        else:
            # hold / revoked — grouped with pending so the student sees
            # something explaining why they can't access it
            pending_courses.append(item)

    return render(request, 'course/my_courses.html', {
        'pending_courses': pending_courses,
        'in_progress_courses': in_progress_courses,
        'completed_courses': completed_courses,
        'total_enrolled': len(enrollments),
        'completed_count': len(completed_courses),
        'active_page': 'my_courses',
    })