from django.contrib import admin
from .models import Assignment, AssignmentSubmission

@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'max_marks', 'deadline', 'is_active')
    list_filter = ('is_active', 'course')
    search_fields = ('title', 'course__course_name')
    autocomplete_fields = ('course', 'created_by')

@admin.register(AssignmentSubmission)
class AssignmentSubmissionAdmin(admin.ModelAdmin):
    list_display = ('student', 'assignment', 'status', 'marks_obtained', 'submitted_at', 'is_late')
    list_filter = ('status', 'is_late')
    search_fields = ('student__email', 'assignment__title')
    autocomplete_fields = ('assignment', 'student', 'graded_by')