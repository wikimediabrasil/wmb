import datetime

from django import forms
from django.forms import modelformset_factory
from .models import MonthCalendar, Calendar, Activity
from django.utils.translation import gettext_lazy as _


class MonthCalendarForm(forms.ModelForm):
    class Meta:
        model = MonthCalendar
        fields = ['month', 'background_image']
        widgets = {
            "month": forms.Select(attrs={
                "class": "form-control form_value",
                "required": "required",
            })
        }

class CalendarForm(forms.ModelForm):
    class Meta:
        model = Calendar
        fields = ['calendar','year', 'page']
        widgets = {
            "calendar": forms.Select(attrs={
                "class": "form-control form_value",
                "required": "required",
            }),
            "year": forms.NumberInput(attrs={
                "class": "form-control form_value",
                "required": "required",
            }),
            "page": forms.NumberInput(attrs={
                "class": "form-control form_value",
                "required": "required",
            })
        }

class ActivityForm(forms.ModelForm):
    class Meta:
        model = Activity
        fields = ['title', 'date_start', 'date_end', 'custom_date', 'hour_start']
        widgets = {
            "title": forms.TextInput(attrs={
                "class": "form-control form_value",
                "required": "required",
            }),
            "date_start": forms.DateInput(attrs={
                "type": "date",
                "class": "form-control form_value",
                "required": "required",
            }),
            "date_end": forms.DateInput(attrs={
                "type": "date",
                "class": "form-control form_value",
            }),
            "hour_start": forms.TimeInput(attrs={
                "type": "time",
                "class": "form-control form_value",
            }),
            "custom_date": forms.TextInput(attrs={
                "class": "form-control form_value",
            }),
        }
        labels = {
            'title': _("Title of the activity"),
            'date_start': _("Beginning date for this activity"),
            'hour_start': _("Beginning hour for this activity (Optional)"),
            'date_end': _("Ending date for this activity (Optional)"),
            'custom_date': _("Custom date for this activity (Optional)"),
        }

    def clean_date_start(self):
        return self.cleaned_data.get('date_start').strftime("%Y-%m-%d")

class ActivityEditForm(forms.ModelForm):
    keep_custom_date = forms.BooleanField(required=False, label=_("Keep custom date as it is?"))

    class Meta:
        model = Activity
        fields = ['title', 'date_start', 'date_end', 'custom_date', 'hour_start', 'keep_custom_date']
        widgets = {
            "title": forms.TextInput(attrs={
                "class": "form-control form_value",
                "required": "required",
            }),
            "date_start": forms.DateInput(attrs={
                "type": "date",
                "class": "form-control form_value",
                "required": "required",
            }),
            "date_end": forms.DateInput(attrs={
                "type": "date",
                "class": "form-control form_value",
            }),
            "hour_start": forms.TimeInput(attrs={
                "type": "time",
                "class": "form-control form_value",
            }),
            "custom_date": forms.TextInput(attrs={
                "class": "form-control form_value",
            }),
        }
        labels = {
            'title': _("Title of the activity"),
            'date_start': _("Beginning date for this activity"),
            'hour_start': _("Beginning hour for this activity (Optional)"),
            'date_end': _("Ending date for this activity (Optional)"),
            'custom_date': _("Custom date for this activity (Optional)"),
        }

    def clean_date_start(self):
        return self.cleaned_data.get('date_start').strftime("%Y-%m-%d")

    def save(self, commit=True):
        instance = super().save(commit=False)
        if not self.cleaned_data.get("keep_custom_date"):
            instance.custom_date = self.calculate_custom_date()

        if commit:
            instance.save()
        return instance

    def calculate_custom_date(self):
        date_start = datetime.datetime.strptime(self.cleaned_data.get('date_start'),"%Y-%m-%d") or ""
        date_end = self.cleaned_data.get('date_end') or ""

        d_start, d_end = str(date_start.day).zfill(2), str(date_end.day).zfill(2)
        m_start, m_end = str(date_start.month).zfill(2), str(date_end.month).zfill(2)

        if date_start == date_end:
            date_formatted = _("{d_start}").format(d_start=d_start)
        elif date_start.month == date_end.month:
            date_formatted = _("{d_start} to {d_end}").format(d_start=d_start, d_end=d_end)
        else:
            date_formatted = _("{m_start}/{d_start} to {m_end}/{d_end}").format(d_start=d_start,
                                                                                m_start=m_start,
                                                                                d_end=d_end,
                                                                                m_end=m_end)
        return date_formatted


ActivityFormSet = modelformset_factory(Activity, form=ActivityForm, extra=1, can_delete=True, max_num=10)