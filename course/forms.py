from django import forms
from .models import Course, Module, Lesson, Domain
from django.core.exceptions import ValidationError

TEXT_INPUT_CLASS = 'form-control'


class DomainForm(forms.ModelForm):
    class Meta:
        model = Domain
        fields = ['name', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': TEXT_INPUT_CLASS, 'placeholder': 'e.g. Cyber Security'}),
            'description': forms.TextInput(attrs={'class': TEXT_INPUT_CLASS, 'placeholder': 'Optional short description'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class CourseForm(forms.ModelForm):
    domains = forms.ModelMultipleChoiceField(
        queryset=Domain.objects.filter(is_active=True),
        widget=forms.CheckboxSelectMultiple,
        required=True,
        help_text="Select at least one subject area this course belongs to.",
    )

    class Meta:
        model = Course
        fields = ['course_name', 'course_description', 'course_banner', 'domains', 'learning_outcomes', 'pre_requisites']
        widgets = {
            'course_name': forms.TextInput(attrs={'class': TEXT_INPUT_CLASS, 'placeholder': 'e.g. Python for Beginners'}),
            'course_description': forms.Textarea(attrs={'class': TEXT_INPUT_CLASS, 'rows': 4}),
            'course_banner': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'learning_outcomes': forms.Textarea(attrs={'class': TEXT_INPUT_CLASS, 'rows': 4}),
            'pre_requisites': forms.Textarea(attrs={'class': TEXT_INPUT_CLASS, 'rows': 3}),
        }

    def clean_domains(self):
        domains = self.cleaned_data.get('domains')
        if not domains or domains.count() == 0:
            raise ValidationError("Select at least one domain for this course.")
        return domains


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