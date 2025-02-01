from calendar import calendar

from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.conf import settings

from .models import MonthCalendar, Calendar, Activity
from .forms import MonthCalendarForm, CalendarForm, ActivityForm, ActivityFormSet, ActivityEditForm


# ======================================================================================================================
# MONTHCALENDAR CRUD
# ======================================================================================================================
def month_calendar_create(request):
    form = MonthCalendarForm(request.POST or None, request.FILES or None)
    context = {"form": form}
    if request.method == "POST":
        if form.is_valid():
            form.save()
            return redirect(reverse("calendars:month_calendar_list"))
    return render(request, "calendars/month_calendar_create_and_update.html", context)


def month_calendar_update(request, pk):
    month_calendar = get_object_or_404(MonthCalendar, pk=pk)
    form = MonthCalendarForm(request.POST or None, request.FILES or None, instance=month_calendar)
    context = {"form": form}
    if request.method == 'POST':
        if form.is_valid():
            form.save()
            return redirect('calendars:month_calendar_detail', pk=month_calendar.id)
    return render(request, 'calendars/month_calendar_create_and_update.html', context)


def month_calendar_detail(request, pk):
    month_calendar = get_object_or_404(MonthCalendar, pk=pk)
    context = {"month_calendar": month_calendar}
    return render(request, 'calendars/month_calendar_detail.html', context)


def month_calendar_list(request):
    month_calendars = MonthCalendar.objects.all()
    context = {"month_calendars": month_calendars}
    return render(request, 'calendars/month_calendar_list.html', context)


def month_calendar_delete(request, pk):
    calendar = get_object_or_404(MonthCalendar, pk=pk)
    context = {"month_calendar": calendar}
    if request.method == 'POST':
        calendar.delete()
        return redirect('calendars:month_calendar_list')
    return render(request, 'calendars/month_calendar_delete.html', context)


# ======================================================================================================================
# CALENDAR CRUD
# ======================================================================================================================
def calendar_create(request):
    form = CalendarForm(request.POST or None, request.FILES or None)
    context = {"form": form}
    if request.method == "POST":
        if form.is_valid():
            form.save()
            return redirect(reverse("calendars:calendar_list"))
    return render(request, "calendars/calendar_create_and_update.html", context)


def calendar_update(request, pk):
    calendar = get_object_or_404(Calendar, pk=pk)
    form = CalendarForm(request.POST or None, request.FILES or None, instance=calendar)
    context = {"form": form}
    if request.method == 'POST':
        if form.is_valid():
            form.save()
            return redirect('calendars:calendar_detail', pk=calendar.id)
    return render(request, 'calendars/calendar_create_and_update.html', context)


def calendar_detail(request, pk):
    calendar = get_object_or_404(Calendar, pk=pk)
    activities = calendar.activities.all().order_by('date_start')
    serialized_activities = [
        {
            "title": activity.title,
            "date": activity.custom_date if activity.custom_date else "",
            "hour_start": activity.hour_start.strftime("%Hh%M").replace("h00", "h") if activity.hour_start else "",
        }
        for activity in activities
    ]
    context = {"calendar": calendar, "activities": serialized_activities, "media_url": settings.MEDIA_URL, "static_url": settings.STATIC_URL}
    return render(request, 'calendars/calendar_detail.html', context)


def format_hour(hour):
    if hour.minute == 0:
        return f"{hour.hour}h"
    return f"{hour.hour}h{hour.minute}"


def calendar_list(request):
    calendars = Calendar.objects.all()
    context = {"calendars": calendars}
    return render(request, 'calendars/calendar_list.html', context)


def calendar_delete(request, pk):
    calendar = get_object_or_404(Calendar, pk=pk)
    context = {"calendar": calendar}
    if request.method == 'POST':
        calendar.delete()
        return redirect('calendars:calendar_list')
    return render(request, 'calendars/calendar_delete.html', context)


def calendar_download(request, pk):
    wmb_calendar = get_object_or_404(Calendar, pk=pk)
    if wmb_calendar:
        activities = Activity.objects.filter(calendar=wmb_calendar)
        context = {"wmb_calendar": wmb_calendar,
                   "activities": activities,
                   "MEDIA_URL": settings.MEDIA_URL}
        return render(request, "calendars/calendar_download.html", context)




# ======================================================================================================================
# ACTIVITY CRUD
# ======================================================================================================================
def activity_create(request, calendar_id):
    calendar = get_object_or_404(Calendar, pk=calendar_id)
    form = ActivityForm(request.POST or None, initial={"calendar": calendar})
    context = {"form": form, "calendar": calendar}
    if request.method == "POST":
        form.instance.calendar = calendar
        if form.is_valid():
            form.save()
            return redirect(reverse("calendars:calendar_detail", kwargs={"pk": calendar.id}))
    return render(request, "calendars/activity_create_and_update.html", context)


def activity_create_in_bulk(request, calendar_id):
    calendar = get_object_or_404(Calendar, pk=calendar_id)
    if request.method == "POST":
        formset = ActivityFormSet(request.POST, queryset=Activity.objects.none(), initial=[{"calendar": calendar}])

        for form in formset:
            form.instance.calendar = calendar
        if formset.is_valid():
            formset.save()
            return redirect(reverse("calendars:calendar_detail", kwargs={"pk": calendar.id}))
    else:
        formset = ActivityFormSet(queryset=Activity.objects.none())

    context = {"formset": formset, "calendar": calendar}
    return render(request, "calendars/activity_create_in_bulk.html", context)


def activity_update(request, calendar_id, pk):
    activity = get_object_or_404(Activity, pk=pk)
    calendar = get_object_or_404(Calendar, pk=calendar_id)
    form = ActivityEditForm(request.POST or None, instance=activity)
    context = {"form": form, "calendar": calendar}
    if request.method == 'POST':
        if form.is_valid():
            form.save()
            return redirect(reverse('calendars:calendar_detail', kwargs={"pk": calendar.id}))
    return render(request, 'calendars/activity_update.html', context)


def activity_delete(request, calendar_id, pk):
    activity = get_object_or_404(Activity, pk=pk)
    calendar = get_object_or_404(Calendar, pk=calendar_id)
    context = {"activity": activity, "calendar": calendar}
    if request.method == 'POST':
        activity.delete()
        return redirect(reverse('calendars:calendar_detail', kwargs={"pk": calendar.id}))
    return render(request, 'calendars/activity_delete.html', context)
