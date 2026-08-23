# formbuilder/context_processors.py
from .models import Form


def sidebar_forms(request):
    """Only pinned forms are ever sent to the sidebar — filtering happens
    entirely in the DB query, no client-side logic needed."""
    if not (request.user.is_authenticated and request.user.is_staff):
        return {}

    pinned = Form.objects.filter(is_pinned=True).only(
        "id", "title", "is_published"
    ).order_by("title")

    return {
        "fb_pinned_active": [f for f in pinned if f.is_published],
        "fb_pinned_inactive": [f for f in pinned if not f.is_published],
    }