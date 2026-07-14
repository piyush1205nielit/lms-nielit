from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone

from course.models import Course, Module, Lesson, Enrollment, Progress


@login_required(login_url='user:login')
def lesson_player_view(request, slug, lesson_id):
    course = get_object_or_404(Course, slug=slug, status=Course.Status.ACTIVE)
    lesson = get_object_or_404(Lesson, id=lesson_id, module__course=course)

    # access control — the real gate: enrolled learners, or admins previewing content
    is_enrolled = Enrollment.objects.filter(user=request.user, course=course).exists()
    if not is_enrolled and not request.user.is_admin_role:
        messages.error(request, "You need to enroll in this course to access its content.")
        return redirect('course:detail', slug=slug)

    if lesson.video_status != Lesson.VideoStatus.READY or not lesson.video_file:
        messages.error(request, "This lesson's video isn't available yet.")
        return redirect('course:detail', slug=slug)

    modules = course.modules.prefetch_related('lessons').order_by('order')

    completed_lesson_ids = set()
    if is_enrolled:
        completed_lesson_ids = set(
            Progress.objects.filter(user=request.user, lesson__module__course=course, completed=True)
            .values_list('lesson_id', flat=True)
        )

    progress, _ = Progress.objects.get_or_create(user=request.user, lesson=lesson) if is_enrolled else (None, None)

    # figure out "next lesson" for the continue button
    all_lessons = list(Lesson.objects.filter(module__course=course).order_by('module__order', 'order'))
    current_index = next((i for i, l in enumerate(all_lessons) if l.id == lesson.id), None)
    next_lesson = all_lessons[current_index + 1] if current_index is not None and current_index + 1 < len(all_lessons) else None

    return render(request, 'course/course_player.html', {
        'course': course,
        'modules': modules,
        'lesson': lesson,
        'next_lesson': next_lesson,
        'completed_lesson_ids': completed_lesson_ids,
        'progress': progress,
        'is_enrolled': is_enrolled,
    })


@login_required(login_url='user:login')
@require_POST
def mark_lesson_progress(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)
    course = lesson.module.course

    if not Enrollment.objects.filter(user=request.user, course=course).exists():
        return JsonResponse({'error': 'Not enrolled in this course.'}, status=403)

    completed = request.POST.get('completed') == 'true'
    watched_seconds = request.POST.get('watched_seconds')

    progress, _ = Progress.objects.get_or_create(user=request.user, lesson=lesson)

    if watched_seconds:
        try:
            progress.watched_seconds = max(progress.watched_seconds, int(float(watched_seconds)))
        except ValueError:
            pass

    if completed and not progress.completed:
        progress.completed = True
        progress.completed_at = timezone.now()

    progress.save()

    # check if the whole course is now complete for this learner
    total_lessons = Lesson.objects.filter(module__course=course).count()
    completed_lessons = Progress.objects.filter(
        user=request.user, lesson__module__course=course, completed=True
    ).count()

    course_completed = total_lessons > 0 and completed_lessons == total_lessons
    if course_completed:
        Enrollment.objects.filter(user=request.user, course=course).update(
            status=Enrollment.Status.COMPLETED,
            completed_at=timezone.now()
        )
        # Certificate generation would be triggered here (Celery task) — not built yet,
        # left as a clear next step once the certificate app's PDF generation is wired up.

    return JsonResponse({
        'success': True,
        'completed_lessons': completed_lessons,
        'total_lessons': total_lessons,
        'course_completed': course_completed,
    })