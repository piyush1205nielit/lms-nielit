from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
import boto3
from django.conf import settings
from accounts.decorators import admin_required
from .utils import generate_presigned_upload
from course.models import *
import json
from django.views.decorators.csrf import csrf_exempt
from course.models import Lesson
from django.template.loader import render_to_string
from .utils import generate_signed_cookies


@login_required(login_url='user:login')
def lesson_player_view(request, slug, lesson_id):
    course = get_object_or_404(Course, slug=slug, status=Course.Status.ACTIVE)
    lesson = get_object_or_404(Lesson, id=lesson_id, module__course=course)

    # access control — the real gate: enrolled learners, or admins previewing content
    is_enrolled = Enrollment.objects.filter(user=request.user, course=course).exists()
    if not is_enrolled and not request.user.is_admin_role:
        messages.error(request, "You need to enroll in this course to access its content.")
        return redirect('course:detail', slug=slug)

    if lesson.video_status != Lesson.VideoStatus.READY or not lesson.get_video_url():
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

    video_manifest_url = f"https://{settings.CLOUDFRONT_DOMAIN}/{lesson.hls_manifest_key}"

    lesson_folder_prefix = '/'.join(lesson.hls_manifest_key.split('/')[:-1]) + '/*'

    context = {
        'course': course,
        'modules': modules,
        'lesson': lesson,
        'next_lesson': next_lesson,
        'completed_lesson_ids': completed_lesson_ids,
        'progress': progress,
        'is_enrolled': is_enrolled,
        'video_manifest_url': video_manifest_url,
    }

    html = render_to_string('course/course_player.html', context, request=request)
    response = HttpResponse(html)

    cookies = generate_signed_cookies(lesson_folder_prefix)
    for cookie_name, cookie_value in cookies.items():
        response.set_cookie(
            cookie_name,
            cookie_value,
            domain=f".{settings.CLOUDFRONT_DOMAIN.split('.', 1)[-1]}" if '.' in settings.CLOUDFRONT_DOMAIN else None,
            secure=True,
            httponly=True,
            samesite='None',
            max_age=settings.CLOUDFRONT_SIGNED_URL_EXPIRY_SECONDS,
        )

    return response


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



@admin_required
@require_POST
def request_video_upload_url(request, lesson_id):
    """Step 1: browser asks Django for permission to upload. Returns instantly —
    no file has been touched, Django just talks to the S3 API for a moment."""
    lesson = get_object_or_404(Lesson, id=lesson_id)

    filename = request.POST.get('filename', 'video.mp4')
    content_type = request.POST.get('content_type', 'video/mp4')

    if not settings.USE_S3:
        return JsonResponse({'error': 'Direct S3 upload is only available when USE_S3 is enabled.'}, status=400)

    upload_data = generate_presigned_upload(lesson.id, filename, content_type)

    lesson.video_status = Lesson.VideoStatus.UPLOADING
    lesson.raw_upload_key = upload_data['key']
    lesson.save(update_fields=['video_status', 'raw_upload_key'])

    return JsonResponse(upload_data)


@admin_required
@require_POST
def confirm_video_upload(request, lesson_id):
    """Step 3: browser tells Django the direct-to-S3 upload finished. This is a
    tiny confirmation call — a few bytes of JSON, not the video itself."""
    lesson = get_object_or_404(Lesson, id=lesson_id)

    if not lesson.raw_upload_key:
        return JsonResponse({'error': 'No upload was initiated for this lesson.'}, status=400)

    # For now: mark ready immediately, since transcoding (Phase 2) isn't wired up yet.
    # Once MediaConvert is added, this becomes 'processing' instead, and the webhook
    # (built in Phase 2) will be what flips it to 'ready'.
    lesson.video_status = Lesson.VideoStatus.READY
    lesson.save(update_fields=['video_status'])

    return JsonResponse({'success': True, 'status': lesson.video_status})



@csrf_exempt
@require_POST
def mediaconvert_webhook(request):
    # Verify this request genuinely came from our pipeline, not a random caller
    provided_secret = request.headers.get('X-Webhook-Secret')
    if provided_secret != settings.MEDIACONVERT_WEBHOOK_SECRET:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    lesson_id = payload.get('lesson_id')
    job_status = payload.get('status')       # 'COMPLETE' or 'ERROR'
    manifest_key = payload.get('manifest_key')
    duration_seconds = payload.get('duration_seconds')

    if not lesson_id:
        return JsonResponse({'error': 'Missing lesson_id'}, status=400)

    try:
        lesson = Lesson.objects.get(id=lesson_id)
    except Lesson.DoesNotExist:
        return JsonResponse({'error': 'Lesson not found'}, status=404)

    if job_status == 'COMPLETE':
        lesson.video_status = Lesson.VideoStatus.READY
        if manifest_key:
            lesson.hls_manifest_key = manifest_key
        if duration_seconds:
            lesson.duration_seconds = int(duration_seconds)
        lesson.save(update_fields=['video_status', 'hls_manifest_key', 'duration_seconds'])
    elif job_status == 'ERROR':
        lesson.video_status = Lesson.VideoStatus.FAILED
        lesson.save(update_fields=['video_status'])

    return JsonResponse({'success': True, 'lesson_id': str(lesson.id), 'new_status': lesson.video_status})