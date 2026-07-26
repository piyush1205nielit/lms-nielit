from django.contrib import admin
from .models import Announcement


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ('title', 'announcement_type', 'target_type', 'is_pinned', 'is_active', 'publish_at')
    list_filter = ('announcement_type', 'target_type', 'is_active', 'is_pinned')
    search_fields = ('title', 'message')
    autocomplete_fields = ('target_course', 'created_by')
    filter_horizontal = ('target_users',)
    readonly_fields = ('id', 'created_at', 'updated_at')