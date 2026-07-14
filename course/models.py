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
    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        INACTIVE = 'inactive', 'Inactive'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)  # used in URLs
    course_name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=280, unique=True, blank=True)   # added: clean public URLs, e.g. /courses/django-basics/
    course_description = models.TextField()
    course_banner = models.ImageField(upload_to=course_banner_upload_path, null=True, blank=True)

    learning_outcomes = models.TextField(blank=True)
    pre_requisites = models.TextField(blank=True)

    status = models.CharField(max_length=10, choices=Status.choices, default=Status.INACTIVE)
    is_featured = models.BooleanField(default=False)

    info_doc = models.FileField(upload_to=course_doc_upload_path, null=True, blank=True)        # notes/info pdf/doc
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
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='modules')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)   # added: controls module display sequence

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

    video_file = models.FileField(upload_to=lesson_video_upload_path, null=True, blank=True)

    # kept for a future upgrade to the full MediaConvert/HLS pipeline — unused for now
    raw_upload_key = models.CharField(max_length=500, blank=True)
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
    


class Enrollment(models.Model):
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
        unique_together = ('user', 'course')   # a user can't enroll in the same course twice
        indexes = [
            models.Index(fields=['user', 'course']),
        ]

    def __str__(self):
        return f"{self.user.email} -> {self.course.course_name}"


class Progress(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='lesson_progress')
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='progress_records')
    watched_seconds = models.PositiveIntegerField(default=0)   # added: needed to resume playback + compute % watched
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
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='certificates')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='certificates')
    certificate_number = models.CharField(max_length=30, unique=True, editable=False)
    pdf_file = models.FileField(upload_to=certificate_upload_path, null=True, blank=True)
    issued_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'course_certificate'
        unique_together = ('user', 'course')   # one certificate per user per course

    def __str__(self):
        return f"Certificate {self.certificate_number} - {self.user.email}"