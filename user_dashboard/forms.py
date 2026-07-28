from django import forms


class StatusCheckForm(forms.Form):
    identifier = forms.CharField(
        label="Email or Mobile Number",
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 'placeholder': 'Enter your registered email or mobile number',
        }),
    )