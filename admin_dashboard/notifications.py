from django.core.mail import send_mail
from django.conf import settings
from announcement.models import Announcement


def get_display_name(user):
    """Best available human name for a user, falling back gracefully."""
    profile = getattr(user, 'learner_profile', None)
    if profile and profile.full_name:
        return profile.full_name
    faculty_profile = getattr(user, 'faculty_profile', None)
    if faculty_profile and faculty_profile.full_name:
        return faculty_profile.full_name
    return user.email


EMAIL_SUBJECT_PREFIX = "NIELIT LMS -- "

EMAIL_SIGNATURE = (
    "\n\n—\n"
    "LMS Admin\n"
    "NIELIT Delhi LMS Team\n"
    "***This is an automated notification. Please do not reply directly to this email."
)


def notify_users(users, title, app_message, email_message=None, created_by=None, is_system_generated=True):
    """
    Sends a short in-app notification (Announcement, shown in the bell/dashboard)
    and a separate, more formal email.

    - title: used as-is for the in-app Announcement title, and prefixed with
      "NIELIT LMS -- " for the email subject specifically.
    - app_message: short, scannable, shown in the notification dropdown/list.
    - email_message: the fuller, formal version. If omitted, falls back to
      app_message. A signature footer is always appended to the email body.
    """
    users = list(users)
    if not users:
        return

    announcement = Announcement.objects.create(
        title=title,
        message=app_message,
        announcement_type=Announcement.Type.INTERNAL,
        target_type=Announcement.TargetType.SPECIFIC_USERS,
        is_system_generated=is_system_generated,
        created_by=created_by,
    )
    announcement.target_users.set(users)

    body_template = email_message if email_message is not None else app_message
    email_subject = f"{EMAIL_SUBJECT_PREFIX}{title}"

    for user in users:
        try:
            send_mail(
                subject=email_subject,
                message=body_template + EMAIL_SIGNATURE,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=True,
            )
        except Exception:
            pass