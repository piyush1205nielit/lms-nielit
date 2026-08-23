from django import forms
from django.core.validators import (
    MaxLengthValidator,
    MinLengthValidator,
    RegexValidator,
)
from django.forms import inlineformset_factory

from .models import Form, FormField


# ---------------------------------------------------------------------------
# Admin-side forms (building / editing a form definition)
# ---------------------------------------------------------------------------
class FormForm(forms.ModelForm):
    class Meta:
        model = Form
        fields = [
            "title",
            "description",
            "is_published",
            "allow_multiple",
            "success_message",
        ]
        widgets = {
            "title": forms.TextInput(
                attrs={"placeholder": "e.g. Webinar Registration", "class": "inp"}
            ),
            "description": forms.Textarea(
                attrs={"rows": 2, "class": "inp", "placeholder": "Optional description"}
            ),
            "success_message": forms.Textarea(attrs={"rows": 2, "class": "inp"}),
        }


class FormFieldForm(forms.ModelForm):
    class Meta:
        model = FormField
        fields = [
            "label",
            "field_type",
            "placeholder",
            "help_text",
            "required",
            "options",
            "min_length",
            "max_length",
            "validation_type",
            "order",
        ]
        widgets = {
            "label": forms.TextInput(attrs={"class": "inp", "placeholder": "Field label"}),
            "field_type": forms.Select(attrs={"class": "inp field-type-select"}),
            "placeholder": forms.TextInput(attrs={"class": "inp"}),
            "help_text": forms.TextInput(attrs={"class": "inp"}),
            "options": forms.Textarea(
                attrs={"class": "inp opt-box", "rows": 3, "placeholder": "One option per line"}
            ),
            "min_length": forms.NumberInput(attrs={"class": "inp", "min": 0}),
            "max_length": forms.NumberInput(attrs={"class": "inp", "min": 0}),
            "validation_type": forms.Select(attrs={"class": "inp"}),
            "order": forms.HiddenInput(),
        }

    def clean(self):
        cleaned = super().clean()
        ftype = cleaned.get("field_type")
        options = (cleaned.get("options") or "").strip()
        if ftype in FormField.CHOICE_TYPES and not options:
            self.add_error("options", "Choice fields need at least one option.")
        mn, mx = cleaned.get("min_length"), cleaned.get("max_length")
        if mn and mx and mn > mx:
            self.add_error("min_length", "Min length cannot exceed max length.")
        return cleaned


# extra=1 lets the "add field" JS clone a blank row; can_delete gives soft delete
FormFieldFormSet = inlineformset_factory(
    Form,
    FormField,
    form=FormFieldForm,
    extra=1,
    can_delete=True,
)


# ---------------------------------------------------------------------------
# Public-side dynamic form (rendered from a Form's fields)
# ---------------------------------------------------------------------------
_VALIDATORS = {
    "numeric": RegexValidator(r"^[0-9]+$", "Enter numbers only."),
    "alpha": RegexValidator(r"^[A-Za-z ]+$", "Enter letters only."),
    "alphanumeric": RegexValidator(r"^[A-Za-z0-9 ]+$", "Enter letters and numbers only."),
}


class DynamicForm(forms.Form):
    """Builds itself from a Form instance's field definitions."""

    def __init__(self, *args, form_instance=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.form_instance = form_instance
        if form_instance is None:
            return
        for f in form_instance.ordered_fields:
            self.fields[f.field_name] = self._build(f)

    def _build(self, f):
        common = {
            "label": f.label,
            "required": f.required,
            "help_text": f.help_text,
        }
        attrs = {"class": "inp"}
        if f.placeholder:
            attrs["placeholder"] = f.placeholder

        validators = []
        if f.validation_type and f.validation_type != "none":
            v = _VALIDATORS.get(f.validation_type)
            if v:
                validators.append(v)
        if f.min_length:
            validators.append(MinLengthValidator(f.min_length))
        if f.max_length:
            validators.append(MaxLengthValidator(f.max_length))

        t = f.field_type

        if t == "textarea":
            attrs["rows"] = 4
            return forms.CharField(
                widget=forms.Textarea(attrs=attrs),
                max_length=f.max_length or None,
                validators=validators,
                **common,
            )
        if t == "number":
            attrs["inputmode"] = "numeric"
            return forms.CharField(
                widget=forms.TextInput(attrs={**attrs, "type": "number"}),
                validators=validators or [_VALIDATORS["numeric"]],
                **common,
            )
        if t == "email":
            return forms.EmailField(widget=forms.EmailInput(attrs=attrs), **common)
        if t == "tel":
            attrs["inputmode"] = "tel"
            return forms.CharField(
                widget=forms.TextInput(attrs={**attrs, "type": "tel"}),
                validators=validators or [_VALIDATORS["numeric"]],
                **common,
            )
        if t == "url":
            return forms.URLField(widget=forms.URLInput(attrs=attrs), **common)
        if t == "date":
            return forms.DateField(
                widget=forms.DateInput(attrs={**attrs, "type": "date"}), **common
            )
        if t == "datetime":
            return forms.DateTimeField(
                widget=forms.DateTimeInput(attrs={**attrs, "type": "datetime-local"}),
                input_formats=["%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"],
                **common,
            )
        if t == "select":
            choices = [("", "— Select —")] + [(o, o) for o in f.option_list]
            return forms.ChoiceField(
                choices=choices, widget=forms.Select(attrs=attrs), **common
            )
        if t == "radio":
            choices = [(o, o) for o in f.option_list]
            return forms.ChoiceField(
                choices=choices, widget=forms.RadioSelect(attrs={"class": "radio"}), **common
            )
        if t == "checkbox":
            choices = [(o, o) for o in f.option_list]
            return forms.MultipleChoiceField(
                choices=choices,
                widget=forms.CheckboxSelectMultiple(attrs={"class": "check"}),
                **common,
            )
        if t == "file":
            return forms.FileField(widget=forms.ClearableFileInput(attrs={"class": "inp"}), **common)
        if t == "image":
            return forms.ImageField(widget=forms.ClearableFileInput(attrs={"class": "inp"}), **common)

        # default: short text
        return forms.CharField(
            widget=forms.TextInput(attrs=attrs),
            max_length=f.max_length or None,
            validators=validators,
            **common,
        )