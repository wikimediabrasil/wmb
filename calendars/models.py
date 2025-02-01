import calendar
import locale
from datetime import datetime


from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import activate
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

MONTH_CHOICES = {"01": _("January"),
                 "02": _("February"),
                 "03": _("March"),
                 "04": _("April"),
                 "05": _("May"),
                 "06": _("June"),
                 "07": _("July"),
                 "08": _("August"),
                 "09": _("September"),
                 "10": _("October"),
                 "11": _("November"),
                 "12": _("December"), }


class MonthCalendar(models.Model):
    month = models.CharField(_("Month"), max_length=2, choices=MONTH_CHOICES)
    background_image = models.ImageField(_("Background image"), upload_to='month_calendars/')

    def __str__(self):
        month_name = self.get_month_name_in_english()
        return str(_(month_name)).capitalize()

    def get_month_name_in_english(self):
        current_locale = locale.getlocale(locale.LC_TIME)
        try:
            locale.setlocale(locale.LC_TIME, 'en_US.UTF-8')
        except locale.Error:
            locale.setlocale(locale.LC_TIME, 'en_US')

        month_name = calendar.month_name[int(self.month)]
        locale.setlocale(locale.LC_TIME, current_locale)

        return month_name


class Calendar(models.Model):
    calendar = models.ForeignKey(MonthCalendar, on_delete=models.CASCADE)
    year = models.IntegerField(_("Year"), default=datetime.now().year, validators=[MinValueValidator(2013)])
    page = models.IntegerField(_("Page"), default=1, validators=[MinValueValidator(1)])

    def __str__(self):
        return _("%(month_name)s %(year)s") % {"month_name": self.calendar, "year": self.year}


class Activity(models.Model):
    calendar = models.ForeignKey(Calendar, on_delete=models.CASCADE, related_name="activities")
    title = models.CharField(_("Activity title"), max_length=280)
    date_start = models.DateField(_("Start date"), blank=True, null=True)
    date_end = models.DateField(_("End date"), blank=True, null=True)
    custom_date = models.CharField(_("Custom date"), max_length=280, blank=True, null=True)
    hour_start = models.TimeField(_("Hour"), blank=True, null=True)

    def __str__(self):
        return f"{self.title} ({self.calendar})"

    def clean(self):
        if self.date_start:
            if self.date_end and self.date_end < self.date_start:
                raise ValidationError(_("End date must be after start date."))

    def save(self, *args, **kwargs):
        if not self.date_end:
            self.date_end = self.date_start

        if not self.custom_date:
            self.custom_date = self.calculate_custom_date()

        super().save(*args, **kwargs)

    def calculate_custom_date(self):
        d_start, d_end = self.date_start.day, self.date_end.day
        m_start, m_end = self.date_start.month, self.date_end.month

        if self.date_start == self.date_end:
            date_formatted = _("{d_start}").format(d_start=d_start)
        elif self.date_start.month == self.date_end.month:
            date_formatted = _("{d_start} to {d_end}").format(d_start=d_start, d_end=d_end)
        else:
            date_formatted = _("{m_start}/{d_start} to {m_end}/{d_end}").format(d_start=d_start,
                                                                                m_start=m_start,
                                                                                d_end=d_end,
                                                                                m_end=m_end)
        return date_formatted
