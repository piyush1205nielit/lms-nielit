import uuid
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.core.validators import RegexValidator
from .managers import CustomUserManager

phone_validator = RegexValidator(
    regex=r'^\d{10}$',
    message="Enter a valid 10-digit mobile number."
)


class User(AbstractBaseUser, PermissionsMixin):
    class Role(models.TextChoices):
        SUPERADMIN = 'superadmin', 'Super Admin'
        ADMIN = 'admin', 'Admin'
        USER = 'user', 'User'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    contact = models.CharField(max_length=10, unique=True, null=True, blank=True, validators=[phone_validator])
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.USER)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)   # True for admin + superadmin
    # is_superuser comes from PermissionsMixin

    date_joined = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    class Meta:
        db_table = 'accounts_user'
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['contact']),
            models.Index(fields=['role']),
        ]

    def __str__(self):
        return f"{self.email} ({self.role})"

    @property
    def is_admin_role(self):
        return self.role in [self.Role.ADMIN, self.Role.SUPERADMIN]


class AdminProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='admin_profile')
    name = models.CharField(max_length=150)
    bio = models.CharField(max_length=255, blank=True, help_text="Designation / short bio")
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='admins_created', limit_choices_to={'role': User.Role.SUPERADMIN}
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'accounts_adminprofile'

    def __str__(self):
        return f"{self.name} - {self.user.role}"