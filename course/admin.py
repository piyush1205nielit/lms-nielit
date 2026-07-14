from django.contrib import admin
from django.utils.html import format_html
from .models import Course, Module, Lesson, Enrollment, Progress, Certificate


class LessonInline(admin.TabularInline):
    model = Lesson
    extra = 1
    fields = ('order', 'title', 'video_status', 'duration_seconds', 'thumbnail')
    readonly_fields = ('video_status', 'duration_seconds')
    ordering = ('order',)


class ModuleInline(admin.TabularInline):
    model = Module
    extra = 1
    fields = ('order', 'title', 'description')
    ordering = ('order',)
    show_change_link = True


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = (
        'course_name', 'status', 'is_featured', 'module_count',
        'enrolled_count', 'published_date', 'created_by', 'updated_at',
    )
    list_filter = ('status', 'is_featured', 'created_by', 'published_date')
    search_fields = ('course_name', 'course_description', 'slug', 'id')
    prepopulated_fields = {'slug': ('course_name',)}
    readonly_fields = ('id', 'created_at', 'updated_at')
    autocomplete_fields = ('created_by',)
    date_hierarchy = 'created_at'
    list_editable = ('status', 'is_featured')
    inlines = [ModuleInline]
    list_per_page = 30

    fieldsets = (
        (None, {'fields': ('course_name', 'slug', 'course_description', 'course_banner')}),
        ('Content', {'fields': ('learning_outcomes', 'pre_requisites', 'info_doc', 'assignment_doc')}),
        ('Publishing', {'fields': ('status', 'is_featured', 'published_date', 'created_by')}),
        ('Timestamps', {'fields': ('id', 'created_at', 'updated_at'), 'classes': ('collapse',)}),
    )

    actions = ['make_active', 'make_inactive', 'mark_featured', 'unmark_featured']

    def module_count(self, obj):
        return obj.modules.count()
    module_count.short_description = 'Modules'

    def enrolled_count(self, obj):
        return obj.enrollments.count()
    enrolled_count.short_description = 'Enrollments'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('created_by').prefetch_related('modules', 'enrollments')

    @admin.action(description='Mark selected courses as Active')
    def make_active(self, request, queryset):
        updated = queryset.update(status=Course.Status.ACTIVE)
        self.message_user(request, f"{updated} course(s) marked active.")

    @admin.action(description='Mark selected courses as Inactive')
    def make_inactive(self, request, queryset):
        updated = queryset.update(status=Course.Status.INACTIVE)
        self.message_user(request, f"{updated} course(s) marked inactive.")

    @admin.action(description='Mark selected courses as Featured')
    def mark_featured(self, request, queryset):
        updated = queryset.update(is_featured=True)
        self.message_user(request, f"{updated} course(s) marked featured.")

    @admin.action(description='Remove Featured flag')
    def unmark_featured(self, request, queryset):
        updated = queryset.update(is_featured=False)
        self.message_user(request, f"{updated} course(s) unfeatured.")


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'order', 'lesson_count', 'created_at')
    list_filter = ('course',)
    search_fields = ('title', 'description', 'course__course_name')
    autocomplete_fields = ('course',)
    readonly_fields = ('id', 'created_at', 'updated_at')
    ordering = ('course', 'order')
    inlines = [LessonInline]

    def lesson_count(self, obj):
        return obj.lessons.count()
    lesson_count.short_description = 'Lessons'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('course').prefetch_related('lessons')


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = (
        'title', 'module', 'course_name', 'order',
        'video_status_badge', 'duration_display', 'created_at',
    )
    list_filter = ('video_status', 'module__course')
    search_fields = ('title', 'description', 'module__title', 'module__course__course_name')
    autocomplete_fields = ('module',)
    readonly_fields = (
        'id', 'video_status', 'raw_upload_key', 'hls_manifest_key',
        'duration_seconds', 'created_at', 'updated_at',
    )
    ordering = ('module', 'order')
    list_per_page = 50

    fieldsets = (
        (None, {'fields': ('module', 'title', 'description', 'order', 'thumbnail')}),
        ('Video Pipeline (read-only — set automatically)', {
            'fields': ('video_status', 'raw_upload_key', 'hls_manifest_key', 'duration_seconds'),
        }),
        ('Timestamps', {'fields': ('id', 'created_at', 'updated_at'), 'classes': ('collapse',)}),
    )

    def course_name(self, obj):
        return obj.module.course.course_name
    course_name.short_description = 'Course'
    course_name.admin_order_field = 'module__course__course_name'

    def duration_display(self, obj):
        if not obj.duration_seconds:
            return '—'
        minutes, seconds = divmod(obj.duration_seconds, 60)
        return f"{minutes}m {seconds}s"
    duration_display.short_description = 'Duration'

    def video_status_badge(self, obj):
        colors = {
            'uploading': '#f59e0b',
            'processing': '#3b82f6',
            'ready': '#059669',
            'failed': '#dc2626',
        }
        color = colors.get(obj.video_status, '#6b7280')
        return format_html(
            '<span style="background:{}; color:white; padding:2px 10px; border-radius:10px; font-size:11px; font-weight:600;">{}</span>',
            color, obj.get_video_status_display()
        )
    video_status_badge.short_description = 'Video Status'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('module', 'module__course')


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('user_email', 'course', 'status', 'enrolled_at', 'completed_at')
    list_filter = ('status', 'course', 'enrolled_at')
    search_fields = ('user__email', 'user__contact', 'course__course_name')
    autocomplete_fields = ('user', 'course')
    readonly_fields = ('id', 'enrolled_at')
    date_hierarchy = 'enrolled_at'
    list_per_page = 50

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Learner'
    user_email.admin_order_field = 'user__email'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'course')


@admin.register(Progress)
class ProgressAdmin(admin.ModelAdmin):
    list_display = ('user_email', 'lesson_title', 'course_name', 'completed', 'watched_seconds', 'last_watched_at')
    list_filter = ('completed', 'lesson__module__course', 'last_watched_at')
    search_fields = ('user__email', 'lesson__title', 'lesson__module__course__course_name')
    autocomplete_fields = ('user', 'lesson')
    readonly_fields = ('id', 'last_watched_at')
    list_per_page = 50

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Learner'
    user_email.admin_order_field = 'user__email'

    def lesson_title(self, obj):
        return obj.lesson.title
    lesson_title.short_description = 'Lesson'
    lesson_title.admin_order_field = 'lesson__title'

    def course_name(self, obj):
        return obj.lesson.module.course.course_name
    course_name.short_description = 'Course'
    course_name.admin_order_field = 'lesson__module__course__course_name'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'lesson', 'lesson__module', 'lesson__module__course')


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ('certificate_number', 'user_email', 'course', 'issued_at', 'has_pdf')
    list_filter = ('course', 'issued_at')
    search_fields = ('certificate_number', 'user__email', 'course__course_name')
    autocomplete_fields = ('user', 'course')
    readonly_fields = ('id', 'certificate_number', 'issued_at')
    date_hierarchy = 'issued_at'

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Learner'
    user_email.admin_order_field = 'user__email'

    def has_pdf(self, obj):
        return bool(obj.pdf_file)
    has_pdf.boolean = True
    has_pdf.short_description = 'PDF Ready'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'course')