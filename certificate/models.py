import uuid
from django.conf import settings
from django.db import models
from django.core.validators import FileExtensionValidator
from django.utils import timezone


class CertificateDesign(models.Model):
    """Fully customizable certificate design — unchanged from your existing project,
    since it never actually depended on the Student model directly."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    header_title = models.CharField(max_length=500, default="NIELIT Delhi")
    header_subtitle = models.CharField(max_length=500, blank=True)

    logo_position = models.CharField(
        max_length=20,
        choices=[('center', 'Center'), ('left', 'Left'), ('right', 'Right'), ('both', 'Both Sides'), ('none', 'No Logo')],
        default='center'
    )
    institute_logo = models.ImageField(upload_to='certificates/logos/', blank=True, null=True,
        validators=[FileExtensionValidator(['png', 'jpg', 'jpeg', 'svg'])])
    secondary_logo = models.ImageField(upload_to='certificates/logos/', blank=True, null=True,
        validators=[FileExtensionValidator(['png', 'jpg', 'jpeg', 'svg'])])
    logo_size = models.IntegerField(default=80)

    certificate_title = models.CharField(max_length=200, default="CERTIFICATE OF COMPLETION")
    title_font_size = models.IntegerField(default=28)
    title_color = models.CharField(max_length=20, default="#1e3a8a")

    line_1_text = models.CharField(max_length=500, default="This certificate is proudly presented to")
    line_2_student_name = models.BooleanField(default=True)
    line_2_custom_text = models.CharField(max_length=200, blank=True)
    line_2_font_size = models.IntegerField(default=32)
    line_2_color = models.CharField(max_length=20, default="#1e3a8a")

    line_3_text = models.CharField(max_length=500, default="for successfully completing the")

    line_4_show_course = models.BooleanField(default=True)
    line_4_custom_text = models.CharField(max_length=200, blank=True)
    line_4_font_size = models.IntegerField(default=20)
    line_4_color = models.CharField(max_length=20, default="#1e3a8a")

    line_5_date_range = models.BooleanField(default=True)
    line_5_custom_text = models.CharField(max_length=200, blank=True)
    line_5_font_size = models.IntegerField(default=14)
    line_5_color = models.CharField(max_length=20, default="#000000")

    signatory_count = models.IntegerField(choices=[(1, 'One Signatory'), (2, 'Two Signatories')], default=2)
    signature_1_position = models.CharField(max_length=20, choices=[('left', 'Left'), ('center', 'Center'), ('right', 'Right')], default='left')
    signature_1_name = models.CharField(max_length=200, blank=True)
    signature_1_designation = models.CharField(max_length=200, blank=True)
    signature_1_image = models.ImageField(upload_to='certificates/signatures/', blank=True, null=True,
        validators=[FileExtensionValidator(['png', 'jpg', 'jpeg', 'svg'])])

    signature_2_name = models.CharField(max_length=200, null=True, blank=True)
    signature_2_designation = models.CharField(max_length=200, null=True, blank=True)
    signature_2_image = models.ImageField(upload_to='certificates/signatures/', blank=True, null=True,
        validators=[FileExtensionValidator(['png', 'jpg', 'jpeg', 'svg'])])

    show_certificate_number = models.BooleanField(default=True)
    show_registration_number = models.BooleanField(default=True)
    show_student_id = models.BooleanField(default=True)
    show_issue_date = models.BooleanField(default=True)
    footer_font_size = models.IntegerField(default=9)

    border_color = models.CharField(max_length=20, default="#1e3a8a")
    border_width = models.IntegerField(default=3)
    background_image = models.ImageField(upload_to='certificates/backgrounds/', blank=True, null=True,
        validators=[FileExtensionValidator(['png', 'jpg', 'jpeg'])])

    show_qr_code = models.BooleanField(default=True)
    qr_code_position = models.CharField(max_length=20,
        choices=[('bottom-left', 'Bottom Left'), ('bottom-right', 'Bottom Right'), ('bottom-center', 'Bottom Center')],
        default='bottom-right')
    qr_code_size = models.IntegerField(default=80)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_active', '-created_at']

    def __str__(self):
        return f"Certificate Design ({self.certificate_title})"

    def save(self, *args, **kwargs):
        if self.is_active:
            CertificateDesign.objects.filter(is_active=True).exclude(id=self.id).update(is_active=False)
        super().save(*args, **kwargs)


class StudentCertificate(models.Model):
    """
    One certificate record per (user, course) — not per user alone, since a
    student can complete and earn certificates for multiple courses. This is
    the key structural change from your previous project's OneToOne(Student).
    """
    class Status(models.TextChoices):
        REQUESTED = 'requested', 'Requested'
        APPROVED = 'approved', 'Approved'
        REVOKED = 'revoked', 'Revoked'
        DENIED = 'denied', 'Denied'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='certificates')
    course = models.ForeignKey('course.Course', on_delete=models.CASCADE, related_name='certificates')
    design = models.ForeignKey(CertificateDesign, on_delete=models.SET_NULL, null=True, blank=True)

    status = models.CharField(max_length=10, choices=Status.choices, default=Status.REQUESTED)
    certificate_number = models.CharField(max_length=100, unique=True, blank=True, null=True)

    requested_at = models.DateTimeField(auto_now_add=True)
    issue_date = models.DateField(null=True, blank=True, help_text="Set automatically when approved")
    status_updated_at = models.DateTimeField(null=True, blank=True)

    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='certificates_approved')
    issued_by_name = models.CharField(max_length=100, blank=True, help_text="Display name of issuing authority")
    remarks = models.TextField(blank=True)

    class Meta:
        db_table = 'certificate_studentcertificate'
        unique_together = ('user', 'course')
        ordering = ['-requested_at']
        indexes = [
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.course.course_name} ({self.get_status_display()})"

    def generate_certificate_number(self):
        year = (self.issue_date or timezone.now().date()).strftime('%Y')
        course_code = self.course.course_name[:15].replace(' ', '_').upper()
        unique_id = str(self.id)[:8]
        return f"NIELIT-{year}-{course_code}-{unique_id}"

    def approve(self, approved_by):
        self.status = self.Status.APPROVED
        self.issue_date = timezone.now().date()
        self.approved_by = approved_by
        self.status_updated_at = timezone.now()
        if not self.certificate_number:
            self.certificate_number = self.generate_certificate_number()
        self.save()