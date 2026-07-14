from django import forms
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from .models import User, AdminProfile


TEXT_INPUT_CLASS = 'form-control'


class AdminLoginForm(forms.Form):
    identifier = forms.CharField(
        label='Email or Contact Number',
        widget=forms.TextInput(attrs={'class': TEXT_INPUT_CLASS, 'placeholder': 'Email or 10-digit mobile number'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': TEXT_INPUT_CLASS, 'placeholder': 'Your password'})
    )


class AdminCreateForm(forms.Form):
    name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': TEXT_INPUT_CLASS, 'placeholder': 'Full name'})
    )
    bio = forms.CharField(
        max_length=255, required=False,
        widget=forms.TextInput(attrs={'class': TEXT_INPUT_CLASS, 'placeholder': 'Designation (optional)'})
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': TEXT_INPUT_CLASS, 'placeholder': 'admin@example.com'})
    )
    contact = forms.CharField(
        max_length=10, min_length=10, required=False,
        widget=forms.TextInput(attrs={'class': TEXT_INPUT_CLASS, 'placeholder': '10-digit mobile number'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': TEXT_INPUT_CLASS, 'placeholder': 'Set a password'})
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': TEXT_INPUT_CLASS, 'placeholder': 'Confirm password'})
    )

    def clean_email(self):
        email = self.cleaned_data['email'].lower().strip()
        if User.objects.filter(email=email).exists():
            raise ValidationError("An account with this email already exists.")
        return email

    def clean_contact(self):
        contact = self.cleaned_data.get('contact', '').strip()
        if contact:
            if not contact.isdigit() or contact[0] not in '6789':
                raise ValidationError("Enter a valid 10-digit Indian mobile number.")
            if User.objects.filter(contact=contact).exists():
                raise ValidationError("An account with this contact number already exists.")
        return contact

    def clean_password(self):
        password = self.cleaned_data.get('password')
        validate_password(password)
        return password

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', "Passwords do not match.")
        return cleaned_data


class AdminEditForm(forms.ModelForm):
    contact = forms.CharField(
        max_length=10, min_length=10, required=False,
        widget=forms.TextInput(attrs={'class': TEXT_INPUT_CLASS, 'placeholder': '10-digit mobile number'})
    )

    class Meta:
        model = AdminProfile
        fields = ['name', 'bio']
        widgets = {
            'name': forms.TextInput(attrs={'class': TEXT_INPUT_CLASS}),
            'bio': forms.TextInput(attrs={'class': TEXT_INPUT_CLASS, 'placeholder': 'Designation'}),
        }

    def clean_contact(self):
        contact = self.cleaned_data.get('contact', '').strip()

        if contact:
            # Accept any 10-digit number
            if not contact.isdigit() or len(contact) != 10:
                raise ValidationError("Enter a valid 10-digit mobile number.")

            # Exclude the current admin's own user row from the uniqueness check
            existing = User.objects.filter(contact=contact)
            if self.instance and self.instance.pk:
                existing = existing.exclude(pk=self.instance.user.pk)

            if existing.exists():
                raise ValidationError("Another account already uses this contact number.")

        return contact