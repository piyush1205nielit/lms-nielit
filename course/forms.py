from django import forms
from .models import Course, Module, Lesson
from django.core.exceptions import ValidationError


TEXT_INPUT_CLASS = 'form-control'


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['course_name', 'course_description', 'course_banner', 'learning_outcomes', 'pre_requisites']
        widgets = {
            'course_name': forms.TextInput(attrs={'class': TEXT_INPUT_CLASS, 'placeholder': 'e.g. Python for Beginners'}),
            'course_description': forms.Textarea(attrs={'class': TEXT_INPUT_CLASS, 'rows': 4, 'placeholder': 'What is this course about?'}),
            'course_banner': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'learning_outcomes': forms.Textarea(attrs={'class': TEXT_INPUT_CLASS, 'rows': 4, 'placeholder': 'What will learners be able to do after this course?'}),
            'pre_requisites': forms.Textarea(attrs={'class': TEXT_INPUT_CLASS, 'rows': 3, 'placeholder': 'Any prior knowledge required? (optional)'}),
        }


class ModuleForm(forms.ModelForm):
    class Meta:
        model = Module
        fields = ['title', 'description', 'order']
        widgets = {
            'title': forms.TextInput(attrs={'class': TEXT_INPUT_CLASS, 'placeholder': 'e.g. Module 1: Getting Started'}),
            'description': forms.Textarea(attrs={'class': TEXT_INPUT_CLASS, 'rows': 3, 'placeholder': 'Brief description of this module (optional)'}),
            'order': forms.NumberInput(attrs={'class': TEXT_INPUT_CLASS, 'min': 0}),
        }


ALLOWED_VIDEO_EXTENSIONS = ['.mp4', '.webm', '.mov']
MAX_VIDEO_SIZE_BYTES = 1024 * 1024 * 1024   # 1GB, matches the 500-800MB range you're targeting with headroom


# class LessonForm(forms.ModelForm):
#     class Meta:
#         model = Lesson
#         fields = ['title', 'description', 'order', 'thumbnail', 'video_file']
#         widgets = {
#             'title': forms.TextInput(attrs={'class': TEXT_INPUT_CLASS, 'placeholder': 'e.g. Introduction to Variables'}),
#             'description': forms.Textarea(attrs={'class': TEXT_INPUT_CLASS, 'rows': 3, 'placeholder': 'Brief description of this lesson (optional)'}),
#             'order': forms.NumberInput(attrs={'class': TEXT_INPUT_CLASS, 'min': 0}),
#             'thumbnail': forms.ClearableFileInput(attrs={'class': 'form-control'}),
#             'video_file': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'video/mp4,video/webm,video/quicktime'}),
#         }

#     def clean_video_file(self):
#         video = self.cleaned_data.get('video_file')
#         if video and hasattr(video, 'size'):   # only validate on actual new upload, not on an unchanged existing file
#             ext = '.' + video.name.rsplit('.', 1)[-1].lower()
#             if ext not in ALLOWED_VIDEO_EXTENSIONS:
#                 raise ValidationError(f"Unsupported video format. Allowed: {', '.join(ALLOWED_VIDEO_EXTENSIONS)}")
#             if video.size > MAX_VIDEO_SIZE_BYTES:
#                 raise ValidationError(f"Video file is too large. Maximum size is {MAX_VIDEO_SIZE_BYTES // (1024*1024)}MB.")
#         return video

class LessonForm(forms.ModelForm):
    class Meta:
        model = Lesson
        fields = ['title', 'description', 'order', 'thumbnail']   # video_file removed
        widgets = {
            'title': forms.TextInput(attrs={'class': TEXT_INPUT_CLASS, 'placeholder': 'e.g. Introduction to Variables'}),
            'description': forms.Textarea(attrs={'class': TEXT_INPUT_CLASS, 'rows': 3}),
            'order': forms.NumberInput(attrs={'class': TEXT_INPUT_CLASS, 'min': 0}),
            'thumbnail': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }


class CoursePublishForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['status', 'is_featured', 'info_doc', 'assignment_doc']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select'}),
            'info_doc': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'assignment_doc': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }