import uuid
from django.db import models


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