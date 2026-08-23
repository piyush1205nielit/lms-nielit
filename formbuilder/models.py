import uuid

from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify


class Form(models.Model):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    slug = models.SlugField(max_length=255, unique=True, blank=True)

    is_published = models.BooleanField(
        default=False,
        help_text="When ON the form is publicly accessible at its URL.",
    )
    is_pinned = models.BooleanField(
        default=False,
        help_text="Pin this form to the sidebar for quick access.",
    )
    allow_multiple = models.BooleanField(
        default=True,
        help_text="Allow the same visitor to submit more than once.",
    )
    success_message = models.TextField(
        default="Thank you! Your response has been recorded.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title) or "form"
            slug = base
            n = 1
            while Form.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                n += 1
                slug = f"{base}-{n}"
            # add a short unique suffix so slugs are hard to guess
            self.slug = f"{slug}-{uuid.uuid4().hex[:6]}"
        super().save(*args, **kwargs)

    def get_public_url(self):
        return reverse("formbuilder:form_fill", kwargs={"slug": self.slug})

    def get_admin_data_url(self):
        return reverse("formbuilder:form_data", kwargs={"pk": self.pk})

    @property
    def response_count(self):
        return self.responses.count()

    @property
    def ordered_fields(self):
        return self.fields.all().order_by("order", "id")


class FormField(models.Model):
    """A single configurable field belonging to a Form."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class FieldType(models.TextChoices):
        TEXT = "text", "Short text"
        TEXTAREA = "textarea", "Paragraph"
        NUMBER = "number", "Number"
        EMAIL = "email", "Email"
        TEL = "tel", "Contact number"
        URL = "url", "URL"
        SELECT = "select", "Dropdown (single)"
        RADIO = "radio", "Multiple choice (single)"
        CHECKBOX = "checkbox", "Checkboxes (multiple)"
        DATE = "date", "Date"
        DATETIME = "datetime", "Date & time"
        FILE = "file", "File upload"
        IMAGE = "image", "Image upload"

    class Validation(models.TextChoices):
        NONE = "none", "No restriction"
        NUMERIC = "numeric", "Numbers only"
        ALPHA = "alpha", "Letters only"
        ALPHANUMERIC = "alphanumeric", "Letters & numbers only"

    CHOICE_TYPES = {"select", "radio", "checkbox"}
    FILE_TYPES = {"file", "image"}

    form = models.ForeignKey(Form, related_name="fields", on_delete=models.CASCADE)

    label = models.CharField(max_length=255)
    field_name = models.SlugField(
        max_length=100,
        blank=True,
        help_text="Machine name used as the column key. Auto-generated from the label.",
    )
    field_type = models.CharField(
        max_length=20, choices=FieldType.choices, default=FieldType.TEXT
    )
    placeholder = models.CharField(max_length=255, blank=True)
    help_text = models.CharField(max_length=255, blank=True)
    required = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    options = models.TextField(
        blank=True, help_text="One option per line (for dropdown / choice fields)."
    )

    min_length = models.PositiveIntegerField(null=True, blank=True)
    max_length = models.PositiveIntegerField(null=True, blank=True)
    validation_type = models.CharField(
        max_length=20, choices=Validation.choices, default=Validation.NONE
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.label} ({self.get_field_type_display()})"

    def save(self, *args, **kwargs):
        if not self.field_name:
            base = slugify(self.label).replace("-", "_") or "field"
            name = base
            n = 1
            qs = FormField.objects.filter(form=self.form).exclude(pk=self.pk)
            while qs.filter(field_name=name).exists():
                n += 1
                name = f"{base}_{n}"
            self.field_name = name
        super().save(*args, **kwargs)

    @property
    def option_list(self):
        return [o.strip() for o in self.options.splitlines() if o.strip()]

    @property
    def is_choice(self):
        return self.field_type in self.CHOICE_TYPES

    @property
    def is_file(self):
        return self.field_type in self.FILE_TYPES


class FormResponse(models.Model):
    """One submission for a Form. Answers are stored as a JSON map."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    form = models.ForeignKey(Form, related_name="responses", on_delete=models.CASCADE)
    data = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    submitted_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-submitted_at"]

    def __str__(self):
        return f"Response #{self.pk} — {self.form.title}"

    def value_for(self, field):
        """Human-readable value for a given FormField."""
        if field.is_file:
            rf = self.files.filter(field=field).first()
            return rf.file.url if rf and rf.file else ""
        val = self.data.get(field.field_name, "")
        if isinstance(val, list):
            return ", ".join(str(v) for v in val)
        return val


class FormResponseFile(models.Model):
    """Uploaded file/image tied to a response. Uses the project's default
    storage backend, so this transparently lands in S3 when USE_S3=True."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    response = models.ForeignKey(
        FormResponse, related_name="files", on_delete=models.CASCADE
    )
    field = models.ForeignKey(FormField, on_delete=models.CASCADE)
    file = models.FileField(upload_to="form_uploads/%Y/%m/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.file.name