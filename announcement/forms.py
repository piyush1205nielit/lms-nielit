from django import forms
from django.core.exceptions import ValidationError
from accounts.models import User
from course.models import Course
from .models import Announcement

TEXT_INPUT_CLASS = 'form-control'


class AnnouncementForm(forms.ModelForm):
    target_users = forms.ModelMultipleChoiceField(
        queryset=User.objects.filter(role=User.Role.USER).select_related('learner_profile'),
        widget=forms.SelectMultiple(attrs={'class': 'form-select', 'size': '8'}),
        required=False,
    )

    class Meta:
        model = Announcement
        fields = [
            'title', 'message', 'announcement_type', 'target_type',
            'target_course', 'target_users', 'is_pinned', 'is_active',
            'publish_at', 'expires_at',
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': TEXT_INPUT_CLASS, 'placeholder': 'e.g. Portal maintenance on Sunday'}),
            'message': forms.Textarea(attrs={'class': TEXT_INPUT_CLASS, 'rows': 5}),
            'announcement_type': forms.Select(attrs={'class': 'form-select', 'id': 'id_announcement_type'}),
            'target_type': forms.Select(attrs={'class': 'form-select', 'id': 'id_target_type'}),
            'target_course': forms.Select(attrs={'class': 'form-select'}),
            'is_pinned': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'publish_at': forms.DateTimeInput(attrs={'class': TEXT_INPUT_CLASS, 'type': 'datetime-local'}),
            'expires_at': forms.DateTimeInput(attrs={'class': TEXT_INPUT_CLASS, 'type': 'datetime-local'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['target_course'].queryset = Course.objects.filter(status=Course.Status.ACTIVE)
        self.fields['target_course'].required = False

        # datetime-local inputs need "YYYY-MM-DDTHH:MM" formatted initial values
        if self.instance.pk:
            if self.instance.publish_at:
                self.initial['publish_at'] = self.instance.publish_at.strftime('%Y-%m-%dT%H:%M')
            if self.instance.expires_at:
                self.initial['expires_at'] = self.instance.expires_at.strftime('%Y-%m-%dT%H:%M')

    def clean(self):
        cleaned_data = super().clean()
        announcement_type = cleaned_data.get('announcement_type')
        target_type = cleaned_data.get('target_type')
        target_course = cleaned_data.get('target_course')
        target_users = cleaned_data.get('target_users')

        if announcement_type == Announcement.Type.INTERNAL:
            if target_type == Announcement.TargetType.SPECIFIC_COURSE and not target_course:
                self.add_error('target_course', "Select a course when targeting a specific course's students.")
            if target_type == Announcement.TargetType.SPECIFIC_USERS and not target_users:
                self.add_error('target_users', "Select at least one student when targeting specific students.")

        expires_at = cleaned_data.get('expires_at')
        publish_at = cleaned_data.get('publish_at')
        if expires_at and publish_at and expires_at <= publish_at:
            self.add_error('expires_at', "Expiry time must be after the publish time.")

        return cleaned_data