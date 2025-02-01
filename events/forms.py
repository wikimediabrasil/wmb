from django import forms
from events.models import Event
from gettext import gettext as _


class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        exclude = ['created_by']
        widgets = {
            "event_name": forms.TextInput(attrs={
                "type": "text",
                "class": "form-control",
                "placeholder": _("Enter the event name"),
                "required": "required",
            }),
            "date_start": forms.DateInput(format='%Y-%m-%d', attrs={
                "type": "date",
                "class": "form-control",
                "required": "required",
            }),
            "date_end": forms.DateInput(format='%Y-%m-%d', attrs={
                "type": "date",
                "class": "form-control",
            }),
            "link": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": _("Enter link(s) for the event"),
            })
        }
