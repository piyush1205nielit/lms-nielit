from django.contrib import admin
from django.utils.html import format_html
from .models import Event, EventDisplaySettings


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("title", "event_date", "registration_deadline", "is_active", "qr_preview", "created_at")
    list_filter = ("is_active", "bg_type", "card_width", "corner_style")
    search_fields = ("title", "subtitle", "keywords")
    readonly_fields = ("qr_code", "qr_preview", "created_at", "updated_at")

    fieldsets = (
        ("Content", {
            "fields": ("title", "subtitle", "body", "image", "keywords", "is_active")
        }),
        ("Dates", {
            "fields": ("event_date", "registration_deadline")
        }),
        ("Link & QR", {
            "fields": ("url", "show_qr", "qr_code", "qr_preview")
        }),
        ("Logos", {
            "fields": ("logo_count", "logo1", "logo2", "logo_position")
        }),
        ("Card Style", {
            "fields": (
                "card_width", "corner_style", "bg_type", "bg_color",
                "gradient_start", "gradient_end", "accent_color",
                "title_color", "subtitle_color", "text_color", "button_color",
            )
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    def qr_preview(self, obj):
        if obj.qr_code:
            return format_html('<img src="{}" style="height:80px;" />', obj.qr_code.url)
        return "—"
    qr_preview.short_description = "QR Preview"


@admin.register(EventDisplaySettings)
class EventDisplaySettingsAdmin(admin.ModelAdmin):
    list_display = ("display_mode", "updated_at")

    def has_add_permission(self, request):
        # Only one row should ever exist; block adding more once created.
        return not EventDisplaySettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False