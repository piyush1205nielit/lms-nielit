from django import forms
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from .models import User, AdminProfile
from admin_dashboard.models import Centre
from .models import User, FacultyProfile

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
            if not contact.isdigit() or len(contact) != 10:
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



class FacultyForm(forms.ModelForm):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    contact = forms.CharField(
        max_length=10,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '10-digit mobile number'})
    )
    password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Leave blank to keep current password'}),
        help_text="Required when creating a new faculty account. Leave blank when editing to keep the existing password."
    )

    class Meta:
        model = FacultyProfile
        fields = ['full_name', 'designation', 'nielit_centre']
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control'}),
            'designation': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Assistant Professor'}),
            'nielit_centre': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['nielit_centre'].queryset = Centre.objects.filter(is_active=True).order_by('centre_name')
        self.fields['nielit_centre'].required = False

        # self.instance.pk is always truthy for this model, since its UUIDField
        # has default=uuid.uuid4 — the id exists client-side before the row is
        # ever saved. _state.adding is the reliable "is this a real DB row yet?"
        # check regardless of PK type.
        is_existing_record = not self.instance._state.adding

        if is_existing_record:
            try:
                self.fields['email'].initial = self.instance.user.email
                self.fields['contact'].initial = self.instance.user.contact
            except User.DoesNotExist:
                pass

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        qs = User.objects.filter(email=email)
        if not self.instance._state.adding:
            qs = qs.exclude(pk=self.instance.user_id)
        if qs.exists():
            raise ValidationError("A user with this email already exists.")
        return email

    def clean_contact(self):
        contact = self.cleaned_data['contact'].strip()
        if not contact.isdigit() or len(contact) != 10:
            raise ValidationError("Enter a valid 10-digit mobile number.")
        qs = User.objects.filter(contact=contact)
        if not self.instance._state.adding:
            qs = qs.exclude(pk=self.instance.user_id)
        if qs.exists():
            raise ValidationError("A user with this contact number already exists.")
        return contact

    def clean(self):
        cleaned_data = super().clean()
        if self.instance._state.adding and not cleaned_data.get('password'):
            self.add_error('password', "Password is required when creating a new faculty account.")
        return cleaned_data