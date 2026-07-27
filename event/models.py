import uuid
from io import BytesIO

from django.core.exceptions import ValidationError
from django.core.files import File
from django.core.validators import FileExtensionValidator, MinValueValidator, MaxValueValidator
from django.db import models


def validate_image_size(value):
    """Reject images larger than 1 MB."""
    limit_bytes = 1 * 1024 * 1024
    if value.size > limit_bytes:
        raise ValidationError("Image file too large. Maximum size allowed is 1 MB.")


IMAGE_VALIDATORS = [
    FileExtensionValidator(allowed_extensions=["png", "jpg", "jpeg"]),
    validate_image_size,
]


class Event(models.Model):
    WIDTH_FULL = "full"
    WIDTH_80 = "80"
    WIDTH_CHOICES = [
        (WIDTH_FULL, "Full Screen Width"),
        (WIDTH_80, "80% of Screen Width"),
    ]

    CORNER_SHARP = "sharp"
    CORNER_ROUND = "round"
    CORNER_CHOICES = [
        (CORNER_SHARP, "Sharp"),
        (CORNER_ROUND, "Round"),
    ]

    BG_SOLID = "solid"
    BG_GRADIENT = "gradient"
    BG_TYPE_CHOICES = [
        (BG_SOLID, "Solid Color"),
        (BG_GRADIENT, "Gradient"),
    ]

    LOGO_LEFT = "left"
    LOGO_CENTER = "center"
    LOGO_RIGHT = "right"
    LOGO_POSITION_CHOICES = [
        (LOGO_LEFT, "Left"),
        (LOGO_CENTER, "Center"),
        (LOGO_RIGHT, "Right"),
    ]

    LOGO_COUNT_CHOICES = [
        (1, "One Logo"),
        (2, "Two Logos"),
    ]

    # ---------- Identity ----------
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # ---------- Required ----------
    title = models.CharField(max_length=255, help_text="Event title (required)")

    # ---------- Content (all optional) ----------
    event_date = models.DateTimeField(null=True, blank=True)
    registration_deadline = models.DateTimeField(null=True, blank=True)

    subtitle = models.CharField(max_length=500, null=True, blank=True)
    body = models.TextField(null=True, blank=True)

    image = models.ImageField(
        upload_to="events/images/", null=True, blank=True, validators=IMAGE_VALIDATORS
    )
    image_size = models.PositiveIntegerField(
        default=360,
        validators=[MinValueValidator(120), MaxValueValidator(800)],
        help_text="Event image max-height in px (recommended 250-450)",
    )

    keywords = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        help_text="Comma-separated skill chips, e.g. HTML, CSS, Python",
    )

    url = models.URLField(null=True, blank=True, help_text="Link shown as the CTA button")

    show_qr = models.BooleanField(
        default=False, help_text="Generate & show a QR code that points to the URL above"
    )
    qr_code = models.ImageField(
        upload_to="events/qrcodes/", null=True, blank=True, editable=False
    )

    logo_count = models.PositiveSmallIntegerField(
        choices=LOGO_COUNT_CHOICES, null=True, blank=True, default=1
    )
    logo1 = models.ImageField(
        upload_to="events/logos/", null=True, blank=True, validators=IMAGE_VALIDATORS
    )
    logo2 = models.ImageField(
        upload_to="events/logos/", null=True, blank=True, validators=IMAGE_VALIDATORS
    )
    logo_size = models.PositiveIntegerField(
        default=100,
        validators=[MinValueValidator(40), MaxValueValidator(200)],
        help_text="Logo height in px (recommended 80-120)",
    )

    is_active = models.BooleanField(default=True)

    # ---------- Card customization ----------
    card_width = models.CharField(max_length=10, choices=WIDTH_CHOICES, default=WIDTH_80)
    corner_style = models.CharField(max_length=10, choices=CORNER_CHOICES, default=CORNER_ROUND)

    bg_type = models.CharField(max_length=10, choices=BG_TYPE_CHOICES, default=BG_GRADIENT)
    bg_color = models.CharField(
        max_length=20, default="#ffffff", help_text="Used only when Background Type = Solid"
    )
    gradient_start = models.CharField(max_length=20, default="#0f172a")
    gradient_end = models.CharField(max_length=20, default="#1d4ed8")

    accent_color = models.CharField(max_length=20, default="#eab308")  # yellow
    date_badge_color = models.CharField(max_length=20, default="#86efac")       # green, like the mockup
    deadline_badge_color = models.CharField(max_length=20, default="#e9d5ff")    # lavender, like the mockup
    title_color = models.CharField(max_length=20, default="#ffffff")
    subtitle_color = models.CharField(max_length=20, default="#e2e8f0")
    text_color = models.CharField(max_length=20, default="#334155")
    button_color = models.CharField(max_length=20, default="#1d4ed8")  # blue

    logo_position = models.CharField(
        max_length=10, choices=LOGO_POSITION_CHOICES, default=LOGO_CENTER
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    def get_keywords_list(self):
        if not self.keywords:
            return []
        return [k.strip() for k in self.keywords.split(",") if k.strip()]

    def save(self, *args, **kwargs):
        should_generate_qr = bool(self.show_qr and self.url and not self.qr_code)
        super().save(*args, **kwargs)
        if should_generate_qr:
            self._generate_qr_code()

    def _generate_qr_code(self):
        import qrcode

        qr = qrcode.QRCode(box_size=8, border=2)
        qr.add_data(self.url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        buffer = BytesIO()
        img.save(buffer, format="PNG")
        filename = f"qr_{self.id}.png"

        self.qr_code.save(filename, File(buffer), save=False)
        Event.objects.filter(pk=self.pk).update(qr_code=self.qr_code)


class EventDisplaySettings(models.Model):
    """
    Singleton model controlling how active events are shown on the public homepage.
    Only one row ever exists (pk=1).
    """
    DISPLAY_STACKED = "stacked"
    DISPLAY_CAROUSEL = "carousel"
    DISPLAY_HIDDEN = "hidden"
    DISPLAY_CHOICES = [
        (DISPLAY_STACKED, "Stacked — one below another"),
        (DISPLAY_CAROUSEL, "Carousel — auto-scrolling, one at a time"),
        (DISPLAY_HIDDEN, "Hidden — do not show on homepage"),
    ]

    display_mode = models.CharField(
        max_length=10, choices=DISPLAY_CHOICES, default=DISPLAY_STACKED
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Event Display Settings"
        verbose_name_plural = "Event Display Settings"

    def __str__(self):
        return f"Event display mode: {self.get_display_mode_display()}"

    def save(self, *args, **kwargs):
        self.pk = 1  # enforce singleton
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass  # prevent deletion

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj