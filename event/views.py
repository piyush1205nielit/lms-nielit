#event/views.py
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from .forms import EventForm
from .models import Event, EventDisplaySettings
from django.http import JsonResponse
import json


def public_event_list(request):
    """Public list of active event cards (e.g. a dedicated /events/ page)."""
    events = Event.objects.filter(is_active=True)
    return render(request, "event/public_event_list.html", {"events": events})


@staff_member_required
def event_list(request):
    """Admin dashboard grid of ALL events (active + inactive), plus display controls."""
    events = Event.objects.all()
    active_events = Event.objects.filter(is_active=True)
    display_settings = EventDisplaySettings.get_solo()
    return render(request, "event/event_list.html", {
        "events": events,
        "active_events": active_events,
        "display_settings": display_settings,
    })


@staff_member_required
@require_POST
def event_set_display_mode(request, mode):
    """Persist how events should be shown on the public homepage."""
    valid_modes = dict(EventDisplaySettings.DISPLAY_CHOICES)
    if mode not in valid_modes:
        messages.error(request, "Invalid display mode.")
        return redirect("event:event_list")

    settings_obj = EventDisplaySettings.get_solo()
    settings_obj.display_mode = mode
    settings_obj.save(update_fields=["display_mode", "updated_at"])
    messages.success(request, f'Homepage event display set to "{valid_modes[mode]}".')
    return redirect("event:event_list")


@staff_member_required
def event_preview(request, pk):
    """Standalone preview of exactly how the card renders on the homepage."""
    event = get_object_or_404(Event, pk=pk)
    return render(request, "event/event_preview.html", {"event": event})


@staff_member_required
def event_create(request):
    if request.method == "POST":
        form = EventForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Event created successfully.")
            return redirect("event:event_list")
    else:
        form = EventForm()
    return render(request, "event/event_form.html", {"form": form, "title": "Create Event"})


@staff_member_required
def event_update(request, pk):
    event = get_object_or_404(Event, pk=pk)
    if request.method == "POST":
        form = EventForm(request.POST, request.FILES, instance=event)
        if form.is_valid():
            form.save()
            messages.success(request, "Event updated successfully.")
            return redirect("event:event_list")
    else:
        form = EventForm(instance=event)
    return render(request, "event/event_form.html", {"form": form, "title": "Update Event"})


@staff_member_required
def event_delete(request, pk):
    event = get_object_or_404(Event, pk=pk)
    if request.method == "POST":
        event.delete()
        messages.success(request, "Event deleted.")
        return redirect("event:event_list")
    return render(request, "event/event_confirm_delete.html", {"event": event})


@staff_member_required
@require_POST
def event_toggle_active(request, pk):
    """Toggle is_active -> this is what shows/hides the card on the homepage."""
    event = get_object_or_404(Event, pk=pk)
    event.is_active = not event.is_active
    event.save(update_fields=["is_active", "updated_at"])
    state = "activated and now live on the homepage" if event.is_active else "deactivated and hidden from the homepage"
    messages.success(request, f'"{event.title}" has been {state}.')
    return redirect("event:event_list")


@staff_member_required
@require_POST
def event_reorder(request):
    """
    Accepts JSON: {"order": ["<uuid1>", "<uuid2>", ...]}
    Persists the new order for the given events (index in list == order value).
    """
    try:
        payload = json.loads(request.body.decode("utf-8"))
        event_ids = payload.get("order", [])
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"success": False, "error": "Invalid JSON payload."}, status=400)

    if not isinstance(event_ids, list) or not event_ids:
        return JsonResponse({"success": False, "error": "No order data provided."}, status=400)

    # Fetch only events that actually belong to this id set, update in bulk-ish fashion
    events = {str(e.pk): e for e in Event.objects.filter(pk__in=event_ids)}

    updated = []
    for index, event_id in enumerate(event_ids):
        event = events.get(str(event_id))
        if event is not None:
            event.order = index
            updated.append(event)

    Event.objects.bulk_update(updated, ["order"])

    return JsonResponse({"success": True, "count": len(updated)})