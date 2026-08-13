import uuid
from django.db import models
from django.conf import settings


class Centre(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    centre_name = models.CharField(max_length=400, unique=True)
    centre_address = models.TextField(null=True, blank=True)
    centre_email = models.EmailField(null=True,blank=True)
    centre_contact = models.CharField(max_length=15,null=True, blank=True)
    centre_desc = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'admin_dashboard_centre'
        ordering = ['centre_name']

    def __str__(self):
        return self.centre_name


class MaintenanceMode(models.Model):
    """
    Singleton — exactly one row ever exists. Toggled by superadmin only.
    When is_enabled=True, every request outside the admin panel is shown a
    maintenance page instead of the real response, enforced by
    MaintenanceModeMiddleware.
    """
    id = models.AutoField(primary_key=True)
    is_enabled = models.BooleanField(default=False)
    message = models.TextField(
        blank=True,
        default="We're currently performing scheduled maintenance. Please check back shortly.",
        help_text="Shown to visitors on the maintenance page."
    )
    estimated_end_time = models.DateTimeField(
        null=True, blank=True,
        help_text="Optional — shown to visitors as an estimated return time."
    )
    enabled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+'
    )
    enabled_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'admin_dashboard_maintenancemode'

    def save(self, *args, **kwargs):
        self.pk = 1   # force singleton — always the same row
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass   # never allow deletion — this row must always exist

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return "Maintenance Mode: ON" if self.is_enabled else "Maintenance Mode: OFF"