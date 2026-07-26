from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from accounts.decorators import admin_required
from .models import Announcement
from .forms import AnnouncementForm


# ── Admin: manage announcements ─────────────────────────────

@admin_required
def announcement_list_view(request):
    announcements = Announcement.objects.select_related('target_course', 'created_by').all()
    return render(request, 'announcement/manage_list.html', {
        'announcements': announcements,
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

@login_required(login_url='user:login')
def my_announcements_view(request):
    announcements = Announcement.objects.for_user(request.user)
    return render(request, 'announcement/my_announcements.html', {
        'announcements': announcements,
        'active_page': 'announcements',
    })