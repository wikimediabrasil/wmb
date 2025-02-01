from django import forms
from django.core.exceptions import ValidationError

from certificates.models import Certificate
from events.models import Event
from gettext import gettext as _

from users.models import Participant



class UploadForm(forms.Form):
    certificate_csv = forms.FileField()
    certificate_background = forms.FileField()

    def clean_certificate_csv(self):
        certificate_csv = self.cleaned_data.get("certificate_csv")
        if certificate_csv:
            if not certificate_csv.name.endswith('.csv'):
                raise ValidationError("The uploaded file must be a CSV.")
        return certificate_csv

    def clean_certificate_background(self):
        certificate_background = self.cleaned_data.get("certificate_background")
        if certificate_background:
            if not certificate_background.name.endswith('.png'):
                raise ValidationError("The uploaded file must be a PNG.")
        return certificate_background

    def clean(self):
        cleaned_data = super().clean()
        certificate_csv = cleaned_data.get("certificate_csv")
        certificate_background = cleaned_data.get("certificate_background")

        if not certificate_csv or not certificate_background:
            raise ValidationError(_("Both certificate files are required."))

        return cleaned_data


class CertificateForm(forms.ModelForm):
    username_string = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={"type": "text", "class": "form-control form_value",
                                      "placeholder": _("Enter the Wikimedia username of the individual"), }),
        required=False
    )

    class Meta:
        model = Certificate
        exclude = ['event', 'background', 'certificate_hash', 'emitted_by', 'emitted_at', 'username']
        widgets = {
            "name": forms.TextInput(attrs={
                "type": "text",
                "class": "form-control form_value",
                "placeholder": _("Enter the real name of the individual"),
                "required": "required",
            }),
            "pronoun": forms.Select(attrs={
                "class": "form-control form_value",
                "required": "required"
            }),
            "hours": forms.TextInput(attrs={
                "type": "text",
                "class": "form-control form_value",
                "placeholder": _("Hours worked in the event by the individual. Format: (HHhMM)"),
                "required": "required"
            }),
            "role": forms.TextInput(attrs={
                "type": "text",
                "class": "form-control form_value",
                "placeholder": _("Role of the individual in the event"),
                "required": "required"
            }),
        }
    # def clean_username(self):
    #     username = self.cleaned_data.get('username', None)
    #     if username:
    #         participant, created = Participant.objects.get_or_create(participant_username=username)
    #         return participant
    #     else:
    #         return None

    def clean_name(self):
        name = self.cleaned_data['name'] or ""
        return name.strip()

    def clean_role(self):
        role = self.cleaned_data['role'] or "ouvinte"
        return role.strip()

    def clean_hours(self):
        hours = self.cleaned_data['hours'] or ""
        return hours.strip()

    def clean_pronoun(self):
        pronoun = self.cleaned_data['pronoun'] or "o"
        return pronoun.strip()


class ValidateForm(forms.Form):
    certificate_hash = forms.CharField(
        required=True,
        strip=True,
        max_length=500,
        error_messages={
            'required': _('This field is required.'),
            'max_length': _('Ensure this field has at most 256 characters.'),
        }
    )
