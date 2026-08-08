import uuid
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.core.validators import RegexValidator
from .managers import CustomUserManager
from django.conf import settings

phone_validator = RegexValidator(
    regex=r'^\d{10}$',
    message="Enter a valid 10-digit mobile number."
)


class User(AbstractBaseUser, PermissionsMixin):
    class Role(models.TextChoices):
        SUPERADMIN = 'superadmin', 'Super Admin'
        ADMIN = 'admin', 'Admin'
        FACULTY = 'faculty', 'Faculty'
        USER = 'user', 'User'

    class AccountStatus(models.TextChoices):
        PENDING = 'pending', 'Pending Approval'
        ACTIVE = 'active', 'Active'
        REVOKED = 'revoked', 'Revoked'
        DISABLED = 'disabled', 'Temporarily Disabled'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    contact = models.CharField(max_length=10, unique=True, null=True, blank=True, validators=[phone_validator])
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.USER)

    nielit_centre = models.ForeignKey(
        'admin_dashboard.Centre', on_delete=models.SET_NULL, null=True, blank=True, related_name='users'
    )
    batch_code = models.CharField(max_length=30, blank=True)
    account_status = models.CharField(max_length=10, choices=AccountStatus.choices, default=AccountStatus.PENDING)
    account_status_updated_at = models.DateTimeField(null=True, blank=True)

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
            models.Index(fields=['account_status']),
        ]

    def __str__(self):
        return f"{self.email} ({self.role})"

    @property
    def is_admin_role(self):
        return self.role in [self.Role.ADMIN, self.Role.SUPERADMIN]

    @property
    def is_staff_area_role(self):
        """Anyone who should be able to log into the admin-side dashboard at all —
        superadmin, content admin, or faculty. Faculty's actual page-level access
        is then narrowed further by admin_or_faculty_required on individual views."""
        return self.role in (self.Role.SUPERADMIN, self.Role.ADMIN, self.Role.FACULTY)


class AdminProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='admin_profile')
    name = models.CharField(max_length=150)
    bio = models.CharField(max_length=255, blank=True, help_text="Designation / short bio")
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='admins_created', limit_choices_to={'role': User.Role.SUPERADMIN}
    )

    can_manage_courses = models.BooleanField(
        default=True,
        help_text="If disabled, this content admin can view courses but cannot create, edit, delete, or publish them."
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'accounts_adminprofile'

    def __str__(self):
        return f"{self.name} - {self.user.role}"


class FacultyProfile(models.Model):
    """
    Profile details for a Faculty-role staff account. Email, contact, and
    date_joined intentionally live on User already (same as AdminProfile
    does for content admins) — not duplicated here, to avoid two sources
    of truth for login credentials.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='faculty_profile')

    full_name = models.CharField(max_length=150)
    designation = models.CharField(max_length=150, blank=True, help_text="e.g. Assistant Professor, Training Coordinator")
    nielit_centre = models.ForeignKey(
        'admin_dashboard.Centre', on_delete=models.SET_NULL, null=True, blank=True, related_name='faculty_members'
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='faculty_created'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'accounts_facultyprofile'
        ordering = ['full_name']

    def __str__(self):
        return f"{self.full_name} ({self.user.email})"