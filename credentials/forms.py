from django import forms
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

from .models import Credential


class CredentialForm(forms.ModelForm):
    class Meta:
        model = Credential
        exclude = ("verification_code", "issued_at", "issued_by", "url")

        widgets = {
            "username": forms.TextInput(attrs={
                "class": "form-control form_value",
                "placeholder": _("Enter the username"),
                "required": "required",
            }),
            "full_name": forms.TextInput(attrs={
                "class": "form-control form_value",
                "placeholder": _("Enter the full name"),
                "required": "required",
            }),
            "cpf": forms.TextInput(attrs={
                "class": "form-control form_value",
                "placeholder": _("Enter the CPF (numbers only)"),
            }),
            "cin": forms.TextInput(attrs={
                "class": "form-control form_value",
                "placeholder": _("Enter the CIN"),
            }),
            "photograph": forms.URLInput(attrs={
                "class": "form-control form_value",
                "placeholder": _("Enter the photograph URL"),
                "required": "required",
            }),
            "event": forms.TextInput(attrs={
                "class": "form-control form_value",
                "placeholder": _("Enter event name"),
                "required": "required",
            }),
            "valid_from": forms.DateInput(
                format="%Y-%m-%d",
                attrs={
                    "type": "date",
                    "class": "form-control form_value",
                    "required": "required",
                }),
            "valid_until": forms.DateInput(
                format="%Y-%m-%d",
                attrs={
                    "type": "date",
                    "class": "form-control form_value",
                    "required": "required",
                }),
        }

    def clean(self):
        cleaned_data = super().clean()
        valid_from = cleaned_data.get("valid_from")
        valid_until = cleaned_data.get("valid_until")

        if valid_from and valid_until:
            if valid_until < valid_from:
                raise ValidationError(_("Valid until date cannot be before valid from date."))

        return cleaned_data
