from django import forms
from django.core.exceptions import ValidationError
from accounts.models import User
from user.models import LearnerProfile

TEXT_INPUT_CLASS = 'form-control'


class AdminUserProfileEditForm(forms.ModelForm):
    """Full profile edit access for admins — used on the admin-side user detail page."""
    class Meta:
        model = LearnerProfile
        fields = [
            'full_name', 'date_of_birth', 'gender', 'aadhar_number',
            'address', 'city', 'state', 'pin_code',
            'highest_qualification', 'profile_image', 'profile_completed',
        ]
        widgets = {
            'full_name': forms.TextInput(attrs={'class': TEXT_INPUT_CLASS}),
            'date_of_birth': forms.DateInput(attrs={'class': TEXT_INPUT_CLASS, 'type': 'date'}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'aadhar_number': forms.TextInput(attrs={'class': TEXT_INPUT_CLASS, 'maxlength': '12'}),
            'address': forms.Textarea(attrs={'class': TEXT_INPUT_CLASS, 'rows': 3}),
            'city': forms.TextInput(attrs={'class': TEXT_INPUT_CLASS}),
            'state': forms.TextInput(attrs={'class': TEXT_INPUT_CLASS}),
            'pin_code': forms.TextInput(attrs={'class': TEXT_INPUT_CLASS, 'maxlength': '6'}),
            'highest_qualification': forms.TextInput(attrs={'class': TEXT_INPUT_CLASS}),
            'profile_image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }


class UserCredentialsForm(forms.ModelForm):
    """Superadmin-only — editing a user's login email/contact. Kept as a
    separate form/view from profile editing since these are login credentials,
    not profile data."""
    class Meta:
        model = User
        fields = ['email', 'contact']
        widgets = {
            'email': forms.EmailInput(attrs={'class': TEXT_INPUT_CLASS}),
            'contact': forms.TextInput(attrs={'class': TEXT_INPUT_CLASS, 'maxlength': '10'}),
        }

    def clean_email(self):
        email = self.cleaned_data['email'].lower().strip()
        existing = User.objects.filter(email=email).exclude(pk=self.instance.pk)
        if existing.exists():
            raise ValidationError("Another account already uses this email.")
        return email

    def clean_contact(self):
        contact = self.cleaned_data.get('contact', '').strip()
        if contact:
            if len(contact) != 10 or not contact.isdigit():
                raise ValidationError("Contact number must be exactly 10 digits.")
            existing = User.objects.filter(contact=contact).exclude(pk=self.instance.pk)
            if existing.exists():
                raise ValidationError("Another account already uses this contact number.")
        return contact