from django import forms
from .models import Course, Module, Lesson, Domain
from django.core.exceptions import ValidationError
from django.utils.text import slugify

TEXT_INPUT_CLASS = 'form-control'


class DomainForm(forms.ModelForm):
    class Meta:
        model = Domain
        fields = ['name', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Cyber Security'}),
            'description': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Optional short description'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input', 'role': 'switch'}),
        }


class CourseForm(forms.ModelForm):
    domains = forms.ModelMultipleChoiceField(
        queryset=Domain.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        required=True,
        help_text="Select at least one subject area. A domain automatically becomes "
                   "active on the public filter once any published course uses it.",
    )
    is_active = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input', 'role': 'switch'}),
        label="Course is Active",
        help_text="Active courses are visible to learners on the public catalog. Toggle off to keep this as a draft.",
    )

    class Meta:
        model = Course
        fields = [
            'course_name', 'course_description', 'course_banner', 'domains',
            'learning_outcomes', 'pre_requisites', 'info_doc', 'assignment_doc',
        ]
   
        widgets = {
            'course_name': forms.TextInput(attrs={'class': TEXT_INPUT_CLASS, 'placeholder': 'e.g. Python for Beginners'}),
            'course_description': forms.Textarea(attrs={'class': TEXT_INPUT_CLASS, 'rows': 4}),
            'course_banner': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'learning_outcomes': forms.Textarea(attrs={'class': TEXT_INPUT_CLASS, 'rows': 4}),
            'pre_requisites': forms.Textarea(attrs={'class': TEXT_INPUT_CLASS, 'rows': 3}),
            'info_doc': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'assignment_doc': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['domains'].queryset = Domain.objects.all().order_by('name')

        if self.instance.pk:
            self.fields['is_active'].initial = (self.instance.status == Course.Status.ACTIVE)
        else:
            self.fields['is_active'].initial = True   # default to active for brand-new courses

    def clean_domains(self):
        domains = self.cleaned_data.get('domains')
        if not domains or domains.count() == 0:
            raise ValidationError("Select at least one domain for this course.")
        return domains

    def clean_course_name(self):
        name = self.cleaned_data['course_name'].strip()
        candidate_slug = slugify(name)

        existing_qs = Course.objects.filter(slug=candidate_slug)
        if self.instance.pk:
            existing_qs = existing_qs.exclude(pk=self.instance.pk)

        if existing_qs.exists():
            suggestion = self._generate_unique_name_suggestion(name)
            raise ValidationError(
                f"A course named \"{name}\" already exists. Try \"{suggestion}\" instead, "
                f"or choose a different name."
            )
        return name

    def _generate_unique_name_suggestion(self, base_name):
        """
        'Python Programming' -> 'Python Programming 2.0' if that's the first
        collision, then '3.0', '4.0', etc., skipping any that are also taken.
        """
        counter = 2
        while True:
            candidate_name = f"{base_name} {counter}.0"
            candidate_slug = slugify(candidate_name)
            if not Course.objects.filter(slug=candidate_slug).exists():
                return candidate_name
            counter += 1

    def save(self, commit=True):
        course = super().save(commit=False)
        course.status = Course.Status.ACTIVE if self.cleaned_data.get('is_active') else Course.Status.INACTIVE
        if commit:
            course.save()
            self.save_m2m()
        return course


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