from django.contrib import admin
from .models import LearnerProfile


@admin.register(LearnerProfile)
class LearnerProfileAdmin(admin.ModelAdmin):
    list_display = (
        'enrollment_number', 'full_name', 'user_email', 'user_contact',
        'city', 'state', 'profile_completed', 'enrolled_courses_count', 'created_at',
    )
    list_filter = ('profile_completed', 'gender', 'state', 'highest_qualification', 'created_at')
    search_fields = ('enrollment_number', 'full_name', 'user__email', 'user__contact', 'aadhar_number', 'city')
    readonly_fields = ('id', 'enrollment_number', 'created_at', 'updated_at')
    autocomplete_fields = ('user',)
    list_per_page = 50

    fieldsets = (
        ('Account', {'fields': ('user', 'enrollment_number', 'profile_completed')}),
        ('Personal Details', {'fields': ('full_name', 'date_of_birth', 'gender', 'profile_image')}),
        ('Identity', {'fields': ('aadhar_number',)}),
        ('Address', {'fields': ('address', 'city', 'state', 'pin_code')}),
        ('Education', {'fields': ('highest_qualification',)}),
        ('Timestamps', {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Email'
    user_email.admin_order_field = 'user__email'

    def user_contact(self, obj):
        return obj.user.contact
    user_contact.short_description = 'Contact'
    user_contact.admin_order_field = 'user__contact'

    def enrolled_courses_count(self, obj):
        return obj.user.enrollments.count()
    enrolled_courses_count.short_description = 'Courses Enrolled'

    def get_queryset(self, request):
        # avoids N+1 queries for user_email/user_contact/enrolled_courses_count on every row
        return super().get_queryset(request).select_related('user').prefetch_related('user__enrollments')