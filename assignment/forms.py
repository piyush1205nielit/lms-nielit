from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from course.models import Course
from .models import Assignment, AssignmentSubmission

TEXT_INPUT_CLASS = 'form-control'


class AssignmentForm(forms.ModelForm):
    class Meta:
        model = Assignment
        fields = ['course', 'title', 'description', 'instructions', 'attachment', 'max_marks', 'deadline', 'is_active']
        widgets = {
            'course': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={'class': TEXT_INPUT_CLASS, 'placeholder': 'e.g. Week 3 — Python Functions Assignment'}),
            'description': forms.Textarea(attrs={
                'class': TEXT_INPUT_CLASS, 'rows': 6,
                'placeholder': 'Type or paste the assignment questions here, e.g.\n\nQ1. Write a function that...\nQ2. Explain the difference between...'
            }),
            'instructions': forms.Textarea(attrs={
                'class': TEXT_INPUT_CLASS, 'rows': 4,
                'placeholder': 'Submission format, word limit, grading rubric, or any other guidance (optional)'
            }),
            'attachment': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'max_marks': forms.NumberInput(attrs={'class': TEXT_INPUT_CLASS, 'min': 1}),
            'deadline': forms.DateTimeInput(attrs={'class': TEXT_INPUT_CLASS, 'type': 'datetime-local'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        help_texts = {
            'description': "This is treated as the assignment's question paper — type or paste the full questions here. "
                            "If you'd rather share a formatted question paper, attach a PDF below instead (or in addition).",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['course'].queryset = Course.objects.filter(status=Course.Status.ACTIVE).order_by('course_name')
        if self.instance.pk and self.instance.deadline:
            self.initial['deadline'] = self.instance.deadline.strftime('%Y-%m-%dT%H:%M')

    def clean_deadline(self):
        deadline = self.cleaned_data.get('deadline')
        if deadline and not self.instance.pk and deadline <= timezone.now():
            raise ValidationError("Deadline must be in the future for a new assignment.")
        return deadline


MAX_SUBMISSION_FILE_SIZE = 5 * 1024 * 1024 

class SubmissionForm(forms.ModelForm):
    class Meta:
        model = AssignmentSubmission
        fields = ['submission_text', 'submission_file']
        widgets = {
            'submission_text': forms.Textarea(attrs={'class': TEXT_INPUT_CLASS, 'rows': 5, 'placeholder': 'Write your answer or notes here (optional if attaching a file)'}),
            'submission_file': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': '.pdf,.doc,.docx,.zip,.png,.jpg,.jpeg'}),
        }

    def clean_submission_file(self):
        file = self.cleaned_data.get('submission_file')
        if file and hasattr(file, 'size') and file.size > MAX_SUBMISSION_FILE_SIZE:
            size_mb = file.size / (1024 * 1024)
            raise ValidationError(f"File is too large ({size_mb:.1f} MB). Maximum allowed size is 5 MB.")
        return file

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get('submission_text') and not cleaned_data.get('submission_file'):
            raise ValidationError("Provide either a written submission or an uploaded file.")
        return cleaned_data


class GradeSubmissionForm(forms.ModelForm):
    class Meta:
        model = AssignmentSubmission
        fields = ['marks_obtained', 'feedback']
        widgets = {
            'marks_obtained': forms.NumberInput(attrs={'class': TEXT_INPUT_CLASS, 'min': 0}),
            'feedback': forms.Textarea(attrs={'class': TEXT_INPUT_CLASS, 'rows': 3, 'placeholder': 'Optional feedback for the student'}),
        }

    def __init__(self, *args, max_marks=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_marks = max_marks

    def clean_marks_obtained(self):
        marks = self.cleaned_data.get('marks_obtained')
        if marks is not None and self.max_marks and marks > self.max_marks:
            raise ValidationError(f"Marks cannot exceed the maximum of {self.max_marks}.")
        return marks