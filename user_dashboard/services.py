from django.urls import reverse
from django.utils import timezone

from announcement.models import Announcement
from assignment.models import AssignmentSubmission


def get_user_notifications(user, limit=10):
    items = []

    for a in Announcement.objects.for_user(user)[:limit]:
        items.append({
            'type': 'announcement',
            'icon': 'fa-bullhorn',
            'title': a.title,
            'body': a.message,
            'timestamp': a.publish_at,
            'url': reverse('announcement:my_announcements'),
            'is_pinned': a.is_pinned,
        })

    graded_submissions = AssignmentSubmission.objects.filter(
        student=user, status=AssignmentSubmission.Status.GRADED
    ).select_related('assignment').order_by('-graded_at')[:limit]

    for s in graded_submissions:
        items.append({
            'type': 'assignment',
            'icon': 'fa-clipboard-check',
            'title': f"Graded: {s.assignment.title}",
            'body': f"You scored {s.marks_obtained}/{s.assignment.max_marks}",
            'timestamp': s.graded_at,
            'url': reverse('assignment:my_assignments'),
            'is_pinned': False,
        })

    items.sort(key=lambda x: x['timestamp'] or timezone.now(), reverse=True)
    return items[:limit]


def get_unread_notification_count(user):
    profile = getattr(user, 'learner_profile', None)
    if profile is None:
        return 0

    last_seen = profile.notifications_last_seen_at

    announcement_qs = Announcement.objects.for_user(user)
    graded_qs = AssignmentSubmission.objects.filter(
        student=user, status=AssignmentSubmission.Status.GRADED
    )

    if last_seen:
        announcement_count = announcement_qs.filter(publish_at__gt=last_seen).count()
        graded_count = graded_qs.filter(graded_at__gt=last_seen).count()
    else:
        announcement_count = announcement_qs.count()
        graded_count = graded_qs.count()

    return announcement_count + graded_count


def mark_notifications_seen(user):
    """
    Idempotent — safe to call on every dropdown open and every visit to
    the full Announcements/Assignments pages, not just the first time.
    Always advances last_seen to 'now', so anything visible at the moment
    of viewing is considered seen, and only genuinely NEW items (created
    after this exact call) will count as unread again.
    """
    profile = getattr(user, 'learner_profile', None)
    if profile is None:
        return
    profile.notifications_last_seen_at = timezone.now()
    profile.save(update_fields=['notifications_last_seen_at'])