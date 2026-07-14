from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, AdminProfile


class AdminProfileInline(admin.StackedInline):
    model = AdminProfile
    fk_name = 'user'
    extra = 0
    fields = ('name', 'bio', 'created_by', 'created_at', 'updated_at')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    # BaseUserAdmin assumes Django's default fieldsets (username, first_name, etc.)
    # which don't exist on our custom User — so fieldsets/add_fieldsets are fully overridden.
    model = User
    ordering = ('-date_joined',)

    list_display = ('email', 'contact', 'role', 'is_active', 'is_staff', 'date_joined')
    list_filter = ('role', 'is_active', 'is_staff', 'date_joined')
    search_fields = ('email', 'contact', 'id')
    readonly_fields = ('id', 'date_joined', 'updated_at', 'last_login')

    fieldsets = (
        (None, {'fields': ('email', 'contact', 'password')}),
        ('Role & Access', {'fields': ('role', 'is_active', 'is_staff', 'is_superuser')}),
        ('Permissions', {'fields': ('groups', 'user_permissions'), 'classes': ('collapse',)}),
        ('Important dates', {'fields': ('last_login', 'date_joined', 'updated_at')}),
        ('System', {'fields': ('id',), 'classes': ('collapse',)}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'contact', 'role', 'password1', 'password2'),
        }),
    )

    filter_horizontal = ('groups', 'user_permissions')
    inlines = [AdminProfileInline]

    def get_inline_instances(self, request, obj=None):
        # Only show the AdminProfile inline for admin/superadmin users —
        # showing it on every learner account row would be noise, and
        # learner detail data lives in the `user` app's own admin instead.
        if obj and obj.role in [User.Role.ADMIN, User.Role.SUPERADMIN]:
            return super().get_inline_instances(request, obj)
        return []


@admin.register(AdminProfile)
class AdminProfileAdmin(admin.ModelAdmin):
    list_display = ('name', 'user_email', 'bio', 'created_by', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('name', 'user__email', 'bio')
    readonly_fields = ('id', 'created_at', 'updated_at')
    autocomplete_fields = ('user', 'created_by')

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Email'
    user_email.admin_order_field = 'user__email'