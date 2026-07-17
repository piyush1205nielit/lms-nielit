from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone

from accounts.decorators import admin_required
from .models import Course, Module, Lesson
from .forms import CourseForm, ModuleForm, LessonForm, CoursePublishForm
from django.contrib.auth.decorators import login_required
from .models import Course, Module, Lesson, Enrollment
from django.conf import settings as django_settings

# ... (all the admin-side views from before stay exactly as they are) ...


# ── Admin: course management list ──────────────────────────

@admin_required
def manage_list_view(request):
    courses = Course.objects.all().select_related('created_by').prefetch_related('modules')
    return render(request, 'course/manage_list.html', {'courses': courses,'active_page': 'courses',})


# ── Step 1: Basic Info ──────────────────────────────────────

@admin_required
def course_create_view(request):
    form = CourseForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        course = form.save(commit=False)
        course.created_by = request.user
        course.status = Course.Status.INACTIVE   # always starts as a draft
        course.save()
        messages.success(request, "Course created. Now add modules and lessons.")
        return redirect('course:modules', course_id=course.id)

    return render(request, 'course/course_form_step1.html', {
        'form': form,
        'active_page': 'courses',
    })


@admin_required
def course_edit_view(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    form = CourseForm(request.POST or None, request.FILES or None, instance=course)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Course details updated.")
        return redirect('course:modules', course_id=course.id)

    return render(request, 'course/course_form_step1.html', {
        'form': form,
        'course': course,
        'active_page': 'courses',
    })


# ── Step 2: Modules & Lessons ───────────────────────────────

@admin_required
def course_modules_view(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    modules = course.modules.prefetch_related('lessons').order_by('order')
    return render(request, 'course/course_modules_step2.html', {
        'course': course,
        'modules': modules,
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

def course_detail_view(request, slug):
    course = get_object_or_404(Course, slug=slug, status=Course.Status.ACTIVE)
    modules = course.modules.prefetch_related('lessons').order_by('order')
    is_enrolled = False
    if request.user.is_authenticated and request.user.role == 'user':
        is_enrolled = course.enrollments.filter(user=request.user).exists()

    return render(request, 'course/course_detail.html', {
        'course': course,
        'modules': modules,
        'is_enrolled': is_enrolled,
    })



def course_detail_view(request, slug):
    course = get_object_or_404(Course, slug=slug, status=Course.Status.ACTIVE)
    modules = course.modules.prefetch_related('lessons').order_by('order')

    is_enrolled = False
    if request.user.is_authenticated and request.user.role == 'user':
        is_enrolled = Enrollment.objects.filter(user=request.user, course=course).exists()

    total_lessons = sum(module.lessons.count() for module in modules)

    return render(request, 'course/course_detail.html', {
        'course': course,
        'modules': modules,
        'is_enrolled': is_enrolled,
        'total_lessons': total_lessons,
    })


@login_required(login_url='user:login')
def course_enroll_view(request, slug):
    course = get_object_or_404(Course, slug=slug, status=Course.Status.ACTIVE)

    if request.user.role != 'user':
        messages.error(request, "Only learner accounts can enroll in courses.")
        return redirect('course:detail', slug=slug)

    if request.method != 'POST':
        # enrollment is a state-changing action — don't allow it via a bare GET link
        return redirect('course:detail', slug=slug)

    enrollment, created = Enrollment.objects.get_or_create(user=request.user, course=course)
    if created:
        messages.success(request, f"You're enrolled in {course.course_name}! You can find it in My Courses.")
    else:
        messages.info(request, "You're already enrolled in this course.")

    return redirect('course:detail', slug=slug)


@login_required(login_url='user:login')
def my_courses_view(request):
    if request.user.role != 'user':
        messages.error(request, "This page is only available for learner accounts.")
        return redirect('public:home')

    enrollments = Enrollment.objects.filter(user=request.user).select_related('course').prefetch_related('course__modules__lessons')

    # attach a lightweight progress percentage to each enrollment for display
    enrollment_data = []
    for enrollment in enrollments:
        total_lessons = Lesson.objects.filter(module__course=enrollment.course).count()
        completed_lessons = enrollment.user.lesson_progress.filter(
            lesson__module__course=enrollment.course, completed=True
        ).count()
        percent = int((completed_lessons / total_lessons) * 100) if total_lessons else 0
        enrollment_data.append({
            'enrollment': enrollment,
            'total_lessons': total_lessons,
            'completed_lessons': completed_lessons,
            'percent': percent,
        })

    return render(request, 'course/my_courses.html', {
        'enrollment_data': enrollment_data,
        'active_page': 'my_courses',
    })