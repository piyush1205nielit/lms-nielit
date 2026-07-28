from .services import get_unread_notification_count


def notifications_context(request):
    if request.user.is_authenticated and hasattr(request.user, 'learner_profile'):
        return {'unread_notification_count': get_unread_notification_count(request.user)}
    return {'unread_notification_count': 0}