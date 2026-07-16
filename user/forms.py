from django import forms
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.contrib.auth.forms import PasswordChangeForm as DjangoPasswordChangeForm
from accounts.models import User
from .models import LearnerProfile


TEXT_INPUT_CLASS = 'form-control'


class SignupForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': TEXT_INPUT_CLASS, 'placeholder': 'you@example.com'})
    )
    contact = forms.CharField(
        max_length=10, min_length=10,
        widget=forms.TextInput(attrs={'class': TEXT_INPUT_CLASS, 'placeholder': '10-digit mobile number'})
    )
    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={'class': TEXT_INPUT_CLASS, 'placeholder': 'Create a password'})
    )
    password2 = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={'class': TEXT_INPUT_CLASS, 'placeholder': 'Re-enter your password'})
    )

    def clean_email(self):
        email = self.cleaned_data['email'].lower().strip()
        if User.objects.filter(email=email).exists():
            raise ValidationError("An account with this email already exists.")
        return email

    def clean_contact(self):
        contact = self.cleaned_data['contact'].strip()
        if not contact.isdigit():
            raise ValidationError("Contact number must contain digits only.")
        if contact[0] not in '6789':
            raise ValidationError("Enter a valid 10-digit Indian mobile number.")
        if User.objects.filter(contact=contact).exists():
            raise ValidationError("An account with this contact number already exists.")
        return contact

    def clean_password1(self):
        password1 = self.cleaned_data.get('password1')
        validate_password(password1)   # runs AUTH_PASSWORD_VALIDATORS from settings
        return password1

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            self.add_error('password2', "Passwords do not match.")
        return cleaned_data


class UserLoginForm(forms.Form):
    identifier = forms.CharField(
        label='Email or Mobile Number',
        widget=forms.TextInput(attrs={'class': TEXT_INPUT_CLASS, 'placeholder': 'Email or 10-digit mobile number'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': TEXT_INPUT_CLASS, 'placeholder': 'Your password'})
    )


class ProfileCompletionForm(forms.ModelForm):
    class Meta:
        model = LearnerProfile
        fields = [
            'full_name', 'date_of_birth', 'gender', 'aadhar_number',
            'address', 'city', 'state', 'pin_code',
            'highest_qualification', 'profile_image',
        ]
        widgets = {
            'full_name': forms.TextInput(attrs={'class': TEXT_INPUT_CLASS, 'placeholder': 'Full name as per records'}),
            'date_of_birth': forms.DateInput(attrs={'class': TEXT_INPUT_CLASS, 'type': 'date'}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'aadhar_number': forms.TextInput(attrs={'class': TEXT_INPUT_CLASS, 'placeholder': '12-digit Aadhar number', 'maxlength': '12'}),
            'address': forms.Textarea(attrs={'class': TEXT_INPUT_CLASS, 'rows': 3, 'placeholder': 'House no., street, locality'}),
            'city': forms.TextInput(attrs={'class': TEXT_INPUT_CLASS}),
            'state': forms.TextInput(attrs={'class': TEXT_INPUT_CLASS}),
            'pin_code': forms.TextInput(attrs={'class': TEXT_INPUT_CLASS, 'maxlength': '6'}),
            'highest_qualification': forms.TextInput(attrs={'class': TEXT_INPUT_CLASS, 'placeholder': 'e.g. B.Tech, 12th Grade'}),
            'profile_image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }

    def clean_aadhar_number(self):
        aadhar = self.cleaned_data.get('aadhar_number', '').strip()
        if aadhar and (not aadhar.isdigit() or len(aadhar) != 12):
            raise ValidationError("Aadhar number must be exactly 12 digits.")
        return aadhar

    def clean_pin_code(self):
        pin = self.cleaned_data.get('pin_code', '').strip()
        if pin and (not pin.isdigit() or len(pin) != 6):
            raise ValidationError("Enter a valid 6-digit PIN code.")
        return pin

    def save(self, commit=True):
        profile = super().save(commit=False)
        profile.profile_completed = True   # marking this here means the middleware gate lifts the moment this form is saved
        if commit:
            profile.save()
        return profile
    


class ProfileEditForm(forms.ModelForm):
    """Self-service profile editing. Deliberately excludes email and contact —
    those live on the User model and can only be changed by an admin, via the
    separate admin_dashboard credentials-edit page."""
    class Meta:
        model = LearnerProfile
        fields = [
            'full_name', 'date_of_birth', 'gender', 'aadhar_number',
            'address', 'city', 'state', 'pin_code',
            'highest_qualification', 'profile_image',
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

    def clean_aadhar_number(self):
        aadhar = self.cleaned_data.get('aadhar_number', '').strip()
        if aadhar and (not aadhar.isdigit() or len(aadhar) != 12):
            raise ValidationError("Aadhar number must be exactly 12 digits.")
        return aadhar

    def clean_pin_code(self):
        pin = self.cleaned_data.get('pin_code', '').strip()
        if pin and (not pin.isdigit() or len(pin) != 6):
            raise ValidationError("Enter a valid 6-digit PIN code.")
        return pin


class UserPasswordChangeForm(DjangoPasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': TEXT_INPUT_CLASS})


class ForgotPasswordVerifyForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': TEXT_INPUT_CLASS, 'placeholder': 'Registered email address'})
    )
    contact = forms.CharField(
        max_length=10, min_length=10,
        widget=forms.TextInput(attrs={'class': TEXT_INPUT_CLASS, 'placeholder': 'Registered mobile number'})
    )
    date_of_birth = forms.DateField(
        widget=forms.DateInput(attrs={'class': TEXT_INPUT_CLASS, 'type': 'date'})
    )


class OTPVerifyForm(forms.Form):
    otp_code = forms.CharField(
        max_length=6, min_length=6,
        widget=forms.TextInput(attrs={
            'class': 'form-control text-center',
            'style': 'font-size: 1.5rem; letter-spacing: 0.5rem; font-weight: 700;',
            'placeholder': '••••••', 'inputmode': 'numeric', 'autocomplete': 'one-time-code',
        })
    )


class SetNewPasswordForm(forms.Form):
    new_password1 = forms.CharField(
        label='New Password',
        widget=forms.PasswordInput(attrs={'class': TEXT_INPUT_CLASS})
    )
    new_password2 = forms.CharField(
        label='Confirm New Password',
        widget=forms.PasswordInput(attrs={'class': TEXT_INPUT_CLASS})
    )

    def clean_new_password1(self):
        password = self.cleaned_data.get('new_password1')
        validate_password(password)
        return password

    def clean(self):
        cleaned_data = super().clean()
        p1, p2 = cleaned_data.get('new_password1'), cleaned_data.get('new_password2')
        if p1 and p2 and p1 != p2:
            self.add_error('new_password2', "Passwords do not match.")
        return cleaned_data