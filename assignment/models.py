import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone


def assignment_attachment_path(instance, filename):
    return f"assignments/{instance.id}/attachment/{filename}"


def submission_file_path(instance, filename):
    return f"assignments/{instance.assignment_id}/submissions/{instance.student_id}/{filename}"


class Assignment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    course = models.ForeignKey('course.Course', on_delete=models.CASCADE, related_name='assignments')

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    instructions = models.TextField(blank=True)
    attachment = models.FileField(upload_to=assignment_attachment_path, null=True, blank=True)

    max_marks = models.PositiveIntegerField(default=100)
    deadline = models.DateTimeField()

    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='assignments_created'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'assignment_assignment'
        ordering = ['-deadline']
        indexes = [
            models.Index(fields=['course', 'is_active']),
            models.Index(fields=['deadline']),
        ]

    def __str__(self):
        return f"{self.course.course_name} — {self.title}"

    @property
    def is_past_deadline(self):
        return timezone.now() > self.deadline

    def submission_for(self, user):
        return self.submissions.filter(student=user).first()


class AssignmentSubmission(models.Model):
    class Status(models.TextChoices):
        SUBMITTED = 'submitted', 'Submitted'
        GRADED = 'graded', 'Graded'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='submissions')
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='assignment_submissions')

    submission_text = models.TextField(blank=True)
    submission_file = models.FileField(upload_to=submission_file_path, null=True, blank=True)

    is_late = models.BooleanField(default=False)
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    status = models.CharField(max_length=10, choices=Status.choices, default=Status.SUBMITTED)
    marks_obtained = models.PositiveIntegerField(null=True, blank=True)
    feedback = models.TextField(blank=True)
    graded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='assignments_graded'
    )
    graded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'assignment_submission'
        unique_together = ('assignment', 'student')   # one submission record per student per assignment (resubmission overwrites it)
        ordering = ['-submitted_at']
        indexes = [
            models.Index(fields=['assignment', 'status']),
        ]

    def __str__(self):
        return f"{self.student.email} — {self.assignment.title}"