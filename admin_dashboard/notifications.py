from django.core.mail import send_mail
from django.conf import settings
from announcement.models import Announcement


def notify_users(users, title, message, created_by=None):
    """Sends both an email and an internal (dashboard) announcement to a specific set of users."""
    users = list(users)
    if not users:
        return

    announcement = Announcement.objects.create(
        title=title,
        message=message,
        announcement_type=Announcement.Type.INTERNAL,
        target_type=Announcement.TargetType.SPECIFIC_USERS,
        created_by=created_by,
    )
    announcement.target_users.set(users)

    for user in users:
        try:
            send_mail(
                subject=title,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=True,
            )
        except Exception:
            pass