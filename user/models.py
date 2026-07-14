import uuid
from django.db import models
from django.core.validators import RegexValidator
from accounts.models import User
from datetime import timedelta
from django.utils import timezone

aadhar_validator = RegexValidator(regex=r'^\d{12}$', message="Aadhar number must be exactly 12 digits.")
pincode_validator = RegexValidator(regex=r'^\d{6}$', message="Enter a valid 6-digit PIN code.")


def profile_image_upload_path(instance, filename):
    return f"profile_images/{instance.user_id}/{filename}"


class LearnerProfile(models.Model):
    class Gender(models.TextChoices):
        MALE = 'male', 'Male'
        FEMALE = 'female', 'Female'
        OTHER = 'other', 'Other'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='learner_profile')

    enrollment_number = models.CharField(max_length=13, unique=True, editable=False)  # format: YYYYMM-XXXXXX

    full_name = models.CharField(max_length=150, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=Gender.choices, blank=True)

    aadhar_number = models.CharField(max_length=12, blank=True, validators=[aadhar_validator])

    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    pin_code = models.CharField(max_length=6, blank=True, validators=[pincode_validator])

    highest_qualification = models.CharField(max_length=150, blank=True)
    profile_image = models.ImageField(upload_to=profile_image_upload_path, null=True, blank=True)

    profile_completed = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'user_learnerprofile'
        indexes = [
            models.Index(fields=['enrollment_number']),
        ]

    def __str__(self):
        return f"{self.full_name or self.user.email} ({self.enrollment_number})"

class PasswordResetOTP(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='password_reset_otps')
    otp_code = models.CharField(max_length=6)
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'user_passwordresetotp'

    def is_expired(self):
        return timezone.now() > self.created_at + timedelta(minutes=10)

    def __str__(self):
        return f"OTP for {self.user.email} ({'used' if self.is_used else 'active'})"
