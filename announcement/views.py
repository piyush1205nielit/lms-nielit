#announcement/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from accounts.decorators import admin_required
from .models import Announcement
from .forms import AnnouncementForm


# ── Admin: manage announcements ─────────────────────────────

from django.db.models import Q

@admin_required
def announcement_list_view(request):
    show_system = request.GET.get('show_system') == '1'

    announcements = Announcement.objects.select_related('target_course', 'created_by')
    if not show_system:
        announcements = announcements.filter(is_system_generated=False)

    query = request.GET.get('q', '').strip()
    if query:
        announcements = announcements.filter(
            Q(title__icontains=query) | Q(message__icontains=query)
        )

    type_filter = request.GET.get('type', '').strip()
    if type_filter:
        announcements = announcements.filter(announcement_type=type_filter)

    target_filter = request.GET.get('target', '').strip()
    if target_filter:
        announcements = announcements.filter(target_type=target_filter)

    status_filter = request.GET.get('status', '').strip()
    if status_filter == 'active':
        announcements = announcements.filter(is_active=True)
    elif status_filter == 'inactive':
        announcements = announcements.filter(is_active=False)

    announcements = announcements.order_by('-is_pinned', '-publish_at')

    system_count = Announcement.objects.filter(is_system_generated=True).count()
    public_count = Announcement.objects.filter(is_system_generated=False, announcement_type=Announcement.Type.PUBLIC).count()
    internal_count = Announcement.objects.filter(is_system_generated=False, announcement_type=Announcement.Type.INTERNAL).count()
    pinned_count = Announcement.objects.filter(is_system_generated=False, is_pinned=True).count()

    return render(request, 'announcement/manage_list.html', {
        'announcements': announcements,
        'show_system': show_system,
        'system_count': system_count,
        'public_count': public_count,
        'internal_count': internal_count,
        'pinned_count': pinned_count,
        'query': query,
        'selected_type': type_filter,
        'selected_target': target_filter,
        'selected_status': status_filter,
        'active_page': 'announcements',
    })


@admin_required
def announcement_create_view(request):
    form = AnnouncementForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        announcement = form.save(commit=False)
        announcement.created_by = request.user
        announcement.save()
        form.save_m2m()
        messages.success(request, "Announcement created.")
        return redirect('announcement:manage_list')
    return render(request, 'announcement/form.html', {'form': form, 'active_page': 'announcements'})


@admin_required
def announcement_edit_view(request, announcement_id):
    announcement = get_object_or_404(Announcement, id=announcement_id)
    form = AnnouncementForm(request.POST or None, instance=announcement)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Announcement updated.")
        return redirect('announcement:manage_list')
    return render(request, 'announcement/form.html', {
        'form': form, 'announcement': announcement, 'active_page': 'announcements',
    })


@admin_required
def announcement_delete_view(request, announcement_id):
    announcement = get_object_or_404(Announcement, id=announcement_id)
    if request.method == 'POST':
        title = announcement.title
        announcement.delete()
        messages.success(request, f"Announcement '{title}' deleted.")
    return redirect('announcement:manage_list')


@admin_required
def announcement_toggle_active_view(request, announcement_id):
    announcement = get_object_or_404(Announcement, id=announcement_id)
    announcement.is_active = not announcement.is_active
    announcement.save(update_fields=['is_active'])
    state = "activated" if announcement.is_active else "deactivated"
    messages.success(request, f"Announcement {state}.")
    return redirect('announcement:manage_list')


# ── Learner: full announcement inbox (beyond the dashboard widget) ──

from user_dashboard.services import mark_notifications_seen

@login_required(login_url='user:login')
def my_announcements_view(request):
    announcements = Announcement.objects.for_user(request.user)
    mark_notifications_seen(request.user)   # visiting this page = seen, same as opening the bell
    return render(request, 'announcement/my_announcements.html', {
        'announcements': announcements,
        'active_page': 'announcements',
    })