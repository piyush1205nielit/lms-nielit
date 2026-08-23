from django.contrib import admin
from django.utils.html import format_html

from .models import Form, FormField, FormResponse, FormResponseFile
from .utils import export_excel


class FormFieldInline(admin.TabularInline):
    model = FormField
    extra = 1
    fields = (
        "order",
        "label",
        "field_type",
        "required",
        "options",
        "validation_type",
        "min_length",
        "max_length",
    )
    ordering = ("order",)


@admin.register(Form)
class FormAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "is_published",
        "response_count",
        "public_link",
        "created_at",
        "updated_at",
    )
    list_filter = ("is_published", "created_at")
    list_editable = ("is_published",)
    search_fields = ("title", "slug")
    readonly_fields = ("slug", "created_at", "updated_at")
    inlines = [FormFieldInline]

    @admin.display(description="Public URL")
    def public_link(self, obj):
        url = obj.get_public_url()
        return format_html('<a href="{}" target="_blank">open</a>', url)


class FormResponseFileInline(admin.TabularInline):
    model = FormResponseFile
    extra = 0
    readonly_fields = ("field", "file", "uploaded_at")
    can_delete = False


@admin.register(FormResponse)
class FormResponseAdmin(admin.ModelAdmin):
    list_display = ("id", "form", "submitted_at", "ip_address")
    list_filter = ("form", "submitted_at")
    search_fields = ("data",)
    readonly_fields = ("form", "data", "ip_address", "submitted_at")
    inlines = [FormResponseFileInline]
    actions = ["export_selected_excel"]

    @admin.action(description="Export responses of the selected form(s) to Excel")
    def export_selected_excel(self, request, queryset):
        form_ids = queryset.values_list("form_id", flat=True).distinct()
        forms = list(Form.objects.filter(id__in=form_ids))
        if len(forms) == 1:
            return export_excel(forms[0])
        self.message_user(request, "Pick responses from a single form to export.")


@admin.register(FormField)
class FormFieldAdmin(admin.ModelAdmin):
    list_display = ("label", "form", "field_type", "required", "order")
    list_filter = ("field_type", "required", "form")
    search_fields = ("label", "field_name")