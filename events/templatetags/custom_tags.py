import calendar
import locale
from django.utils.translation import gettext_lazy as _
from django import template


register = template.Library()


@register.filter
def format_date(date_start, date_end):
    d_start, d_end = date_start.day, date_end.day
    m_start, m_end = calendar.month_name[date_start.month], calendar.month_name[date_end.month]
    y_start, y_end = date_start.year, date_end.year

    if date_start == date_end:
        date_formatted = _("{m_start} {d_start}, {y_start}").format(d_start=d_start,
                                                                    m_start=m_start,
                                                                    y_start=y_start)
    elif date_start.year == date_end.year:
        if date_start.month == date_end.month:
            date_formatted = _("{m_start} {d_start} to {d_end}, {y_start}").format(d_start=d_start,
                                                                                   m_start=m_start,
                                                                                   y_start=y_start,
                                                                                   d_end=d_end)
        else:
            date_formatted = _("{m_start} {d_start} to {m_end} {d_end}, {y_start}").format(d_start=d_start,
                                                                                           m_start=m_start,
                                                                                           y_start=y_start,
                                                                                           d_end=d_end,
                                                                                           m_end=m_end)
    else:
        date_formatted = _("{m_start} {d_start}, {y_start} to {m_end} {d_end}, {y_end}").format(d_start=d_start,
                                                                                                m_start=m_start,
                                                                                                y_start=y_start,
                                                                                                d_end=d_end,
                                                                                                m_end=m_end,
                                                                                                y_end=y_end)
    return date_formatted


@register.filter
def get_month_name(month):
    locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
    return calendar.month_name[int(month)]