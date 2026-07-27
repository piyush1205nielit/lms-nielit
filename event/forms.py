from django import forms

from .models import Event


class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        exclude = ["id", "qr_code", "created_at", "updated_at", "image", "image_size"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "subtitle": forms.TextInput(attrs={"class": "form-control"}),
            "body": forms.Textarea(attrs={"class": "form-control", "rows": 5}),
            "keywords": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "HTML, CSS, Python"}
            ),
            "url": forms.URLInput(attrs={"class": "form-control"}),
            "event_date": forms.DateTimeInput(
                attrs={"type": "datetime-local", "class": "form-control"}
            ),
            "registration_deadline": forms.DateTimeInput(
                attrs={"type": "datetime-local", "class": "form-control"}
            ),
            "logo_size": forms.NumberInput(
                attrs={"class": "form-control", "min": 40, "max": 200, "step": 5}
            ),
            "bg_color": forms.TextInput(attrs={"type": "color"}),
            "gradient_start": forms.TextInput(attrs={"type": "color"}),
            "gradient_end": forms.TextInput(attrs={"type": "color"}),
            "accent_color": forms.TextInput(attrs={"type": "color"}),
            "date_badge_color": forms.TextInput(attrs={"type": "color"}),
            "deadline_badge_color": forms.TextInput(attrs={"type": "color"}),
            "title_color": forms.TextInput(attrs={"type": "color"}),
            "subtitle_color": forms.TextInput(attrs={"type": "color"}),
            "text_color": forms.TextInput(attrs={"type": "color"}),
            "button_color": forms.TextInput(attrs={"type": "color"}),
        }

    def clean_logo1(self):
        return self._validate_image(self.cleaned_data.get("logo1"))

    def clean_logo2(self):
        return self._validate_image(self.cleaned_data.get("logo2"))

    @staticmethod
    def _validate_image(f):
        if f and hasattr(f, "size"):
            if f.size > 1 * 1024 * 1024:
                raise forms.ValidationError("Image must not exceed 1 MB.")
            content_type = getattr(f, "content_type", None)
            if content_type and content_type not in ("image/png", "image/jpeg", "image/jpg"):
                raise forms.ValidationError("Only PNG, JPG, or JPEG files are allowed.")
        return f