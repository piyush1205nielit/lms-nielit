import uuid
from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone


class AnnouncementQuerySet(models.QuerySet):
    def public_active(self):
        """Public announcements currently visible on the homepage/public site."""
        now = timezone.now()
        return self.filter(
            announcement_type=Announcement.Type.PUBLIC,
            is_active=True,
            publish_at__lte=now,
        ).filter(
            Q(expires_at__isnull=True) | Q(expires_at__gte=now)
        ).order_by('-is_pinned', '-publish_at')

    def for_user(self, user):
        """
        Internal announcements this specific logged-in user should see —
        either broadcast to everyone, scoped to a course they're enrolled
        in, or addressed to them individually.
        """
        now = timezone.now()
        base = self.filter(
            announcement_type=Announcement.Type.INTERNAL,
            is_active=True,
            publish_at__lte=now,
        ).filter(
            Q(expires_at__isnull=True) | Q(expires_at__gte=now)
        )

        enrolled_course_ids = user.enrollments.values_list('course_id', flat=True)

        return base.filter(
            Q(target_type=Announcement.TargetType.ALL_USERS) |
            Q(target_type=Announcement.TargetType.SPECIFIC_COURSE, target_course_id__in=enrolled_course_ids) |
            Q(target_type=Announcement.TargetType.SPECIFIC_USERS, target_users=user)
        ).distinct().order_by('-is_pinned', '-publish_at')


class Announcement(models.Model):
    class Type(models.TextChoices):
        PUBLIC = 'public', 'Public (Homepage)'
        INTERNAL = 'internal', 'Internal (Logged-in Users)'

    class TargetType(models.TextChoices):
        ALL_USERS = 'all_users', 'All Logged-in Users'
        SPECIFIC_COURSE = 'specific_course', 'Students of a Specific Course'
        SPECIFIC_USERS = 'specific_users', 'Specific Student(s)'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    title = models.CharField(max_length=255)
    message = models.TextField()

    announcement_type = models.CharField(max_length=10, choices=Type.choices, default=Type.PUBLIC)

    # Only meaningful when announcement_type == INTERNAL
    target_type = models.CharField(
        max_length=20, choices=TargetType.choices, default=TargetType.ALL_USERS, blank=True
    )
    target_course = models.ForeignKey(
        'course.Course', on_delete=models.CASCADE, null=True, blank=True, related_name='announcements'
    )
    target_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True, related_name='targeted_announcements'
    )

    is_pinned = models.BooleanField(default=False, help_text="Pinned announcements always show first")
    is_active = models.BooleanField(default=True)

    publish_at = models.DateTimeField(default=timezone.now, help_text="Announcement becomes visible at this time")
    expires_at = models.DateTimeField(null=True, blank=True, help_text="Optional — announcement auto-hides after this time")

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='announcements_created'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = AnnouncementQuerySet.as_manager()

    class Meta:
        db_table = 'announcement_announcement'
        ordering = ['-is_pinned', '-publish_at']
        indexes = [
            models.Index(fields=['announcement_type', 'is_active']),
            models.Index(fields=['publish_at']),
        ]

    def __str__(self):
        return f"[{self.get_announcement_type_display()}] {self.title}"

    @property
    def is_currently_visible(self):
        now = timezone.now()
        if not self.is_active or self.publish_at > now:
            return False
        if self.expires_at and self.expires_at < now:
            return False
        return True