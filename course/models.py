import uuid
from django.conf import settings
from django.db import models
from django.utils.text import slugify


def course_banner_upload_path(instance, filename):
    return f"courses/{instance.id}/banner/{filename}"


def course_doc_upload_path(instance, filename):
    return f"courses/{instance.id}/docs/{filename}"


def lesson_thumbnail_upload_path(instance, filename):
    return f"lessons/{instance.id}/thumbnail/{filename}"


def certificate_upload_path(instance, filename):
    return f"certificates/{instance.user_id}/{filename}"


class Course(models.Model):
    # ... unchanged, exactly as you have it ...
    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        INACTIVE = 'inactive', 'Inactive'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    course_name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=280, unique=True, blank=True)
    course_description = models.TextField()
    course_banner = models.ImageField(upload_to=course_banner_upload_path, null=True, blank=True)

    learning_outcomes = models.TextField(blank=True)
    pre_requisites = models.TextField(blank=True)

    status = models.CharField(max_length=10, choices=Status.choices, default=Status.INACTIVE)
    is_featured = models.BooleanField(default=False)

    info_doc = models.FileField(upload_to=course_doc_upload_path, null=True, blank=True)
    assignment_doc = models.FileField(upload_to=course_doc_upload_path, null=True, blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='courses_created'
    )

    published_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'course_course'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['is_featured']),
            models.Index(fields=['slug']),
        ]

    def __str__(self):
        return self.course_name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.course_name)[:280]
        super().save(*args, **kwargs)


class Module(models.Model):
    # ... unchanged ...
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='modules')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'course_module'
        ordering = ['course', 'order']
        unique_together = ('course', 'order')

    def __str__(self):
        return f"{self.course.course_name} - {self.title}"


def lesson_video_upload_path(instance, filename):
    return f"lessons/{instance.id}/video/{filename}"


class Lesson(models.Model):
    class VideoStatus(models.TextChoices):
        UPLOADING = 'uploading', 'Uploading'
        PROCESSING = 'processing', 'Processing'
        READY = 'ready', 'Ready'
        FAILED = 'failed', 'Failed'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='lessons')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)

    # Local dev only (USE_S3=False) — direct-to-disk upload via the ordinary form field.
    # In production this field stays empty; raw_upload_key is used instead.
    video_file = models.FileField(
        upload_to=lesson_video_upload_path,
        null=True, blank=True,
    )

    # Production (USE_S3=True) — set once the browser's direct-to-S3 upload completes.
    raw_upload_key = models.CharField(max_length=500, blank=True)
    # Filled in later by the MediaConvert pipeline (Phase 2) once transcoding completes.
    hls_manifest_key = models.CharField(max_length=500, blank=True)

    video_status = models.CharField(max_length=15, choices=VideoStatus.choices, default=VideoStatus.UPLOADING)
    duration_seconds = models.PositiveIntegerField(null=True, blank=True)
    thumbnail = models.ImageField(upload_to=lesson_thumbnail_upload_path, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'course_lesson'
        ordering = ['module', 'order']
        unique_together = ('module', 'order')

    def __str__(self):
        return f"{self.module.title} - {self.title}"

    def get_video_url(self):
        """
        Returns the correct playable video URL regardless of environment,
        so templates/views never need to branch on USE_S3 themselves.

        Local dev: served straight from Django's media storage.
        Production: currently a direct S3 URL to the raw upload (temporary —
        Phase 3 will replace this branch with a signed CloudFront URL once
        the MediaConvert + CDN pipeline is wired up).
        """
        if settings.USE_S3:
            if self.hls_manifest_key:
                # Will be replaced by a CloudFront signed URL in Phase 3
                return f"https://{settings.AWS_PROCESSED_VIDEO_BUCKET}.s3.{settings.AWS_S3_REGION_NAME}.amazonaws.com/{self.hls_manifest_key}"
            if self.raw_upload_key:
                # Temporary — raw bucket has no public/CDN access configured yet
                return f"https://{settings.AWS_RAW_VIDEO_BUCKET}.s3.{settings.AWS_S3_REGION_NAME}.amazonaws.com/{self.raw_upload_key}"
            return None
        else:
            return self.video_file.url if self.video_file else None


class Enrollment(models.Model):
    # ... unchanged, exactly as you have it ...
    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        COMPLETED = 'completed', 'Completed'
        DROPPED = 'dropped', 'Dropped'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='enrollments')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='enrollments')
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.ACTIVE)
    enrolled_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'course_enrollment'
        unique_together = ('user', 'course')
        indexes = [
            models.Index(fields=['user', 'course']),
        ]

    def __str__(self):
        return f"{self.user.email} -> {self.course.course_name}"


class Progress(models.Model):
    # ... unchanged ...
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='lesson_progress')
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='progress_records')
    watched_seconds = models.PositiveIntegerField(default=0)
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    last_watched_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'course_progress'
        unique_together = ('user', 'lesson')
        indexes = [
            models.Index(fields=['user', 'lesson']),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.lesson.title} ({'done' if self.completed else 'in progress'})"


class Certificate(models.Model):
    # ... unchanged ...
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='certificates')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='certificates')
    certificate_number = models.CharField(max_length=30, unique=True, editable=False)
    pdf_file = models.FileField(upload_to=certificate_upload_path, null=True, blank=True)
    issued_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'course_certificate'
        unique_together = ('user', 'course')

    def __str__(self):
        return f"Certificate {self.certificate_number} - {self.user.email}"