import pandas as pd
from io import StringIO
from datetime import datetime

from django.conf import settings
from django.db import transaction
from django.shortcuts import render, redirect, reverse
from django.utils.translation import gettext_lazy as _
from django.core.files.storage import default_storage
from django.templatetags.static import static
from django.contrib.auth.decorators import permission_required

from certificates.forms import UploadForm
from certificates.utils import validate_csv, certificate_create, download_certificate, download_certificates

from events.forms import EventForm
from events.models import Event


# ======================================================================================================================
# CRUD pages
# ======================================================================================================================
@permission_required('events.add_event', raise_exception=True)
def event_create(request):
    form = EventForm(request.POST or None)
    context = {"form": form}

    if request.method == "POST":
        if form.is_valid():
            event = form.save(commit=False)
            event.created_by = request.user
            event.save()
            return redirect(reverse("events:event_detail", kwargs={"event_id": form.instance.pk}))

    return render(request, "events/event_create.html", context)


@permission_required('events.view_event', raise_exception=True)
def event_list(request):
    events = Event.objects.all().order_by("-date_start")
    context = {"events": events}
    return render(request, "events/event_list.html", context)


@permission_required('events.view_event', raise_exception=True)
def event_detail(request, event_id):
    event = Event.objects.get(pk=event_id)
    context = {"event": event}
    return render(request, "events/event_detail.html", context)


@permission_required('events.change_event', raise_exception=True)
def event_update(request, event_id):
    event = Event.objects.get(pk=event_id)
    form = EventForm(request.POST or None, instance=event)
    context = {"event": event, "form": form}

    if request.method == "POST":
        if form.is_valid():
            form.save()
            return redirect(reverse("events:event_detail", kwargs={"event_id": event_id}))

    return render(request, "events/event_update.html", context)


@permission_required('events.delete_event', raise_exception=True)
def event_delete(request, event_id):
    event = Event.objects.get(pk=event_id)
    context = {"event": event}

    if request.method == "POST":
        event.delete()
        return redirect(reverse("events:event_list"))

    return render(request, "events/event_delete.html", context)


@permission_required('certificates.add_certificate', raise_exception=True)
def event_certificate(request, event_id):
    event = Event.objects.get(pk=event_id)
    if request.method == "POST":
        # Verify if the form is valid, that is, the user try to send a csv file and a background image
        form = UploadForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = request.FILES['certificate_csv']

            # Verify if there are validation errors
            df = pd.read_csv(csv_file)
            df.replace('', pd.NA, inplace=True) # substitute empty strings into Nan values
            errors = validate_csv(df)
            if errors:
                form.add_error(None, _("Errors in the CSV file:"))
                for err in errors:
                    form.add_error(None, err)
                context = {"form": form, "event": event}
                return render(request, 'events/event_certificate_upload.html', context)
            else:
                # Format the dataframe
                df.fillna("-", inplace=True)
                if "with_hours" in df.columns:
                    df["with_hours"] = df["with_hours"].apply(lambda x: bool(x and str(x).strip() != "-" and str(x).lower() != "false"))
                    new_df = df[["name", "username", "pronoun", "hours", "role", "with_hours"]]
                else:
                    new_df = df[["name", "username", "pronoun", "hours", "role"]]

                # Save the background image
                png_file = request.FILES['certificate_background']
                png_filename = datetime.now().strftime("%m-%d-%Y-%H-%M-%S - ") + png_file.name
                background_path = default_storage.save(png_filename, png_file)
                html_file = new_df.to_html(index=False, justify='center', border=0)
                csv_table = new_df.to_csv(index=False)
                request.session['csv_table'] = csv_table
                context = {"event": event, "table": html_file, "background": background_path, "csv_table": csv_table}
                return render(request, 'events/event_certificate_confirm.html', context)
    form = UploadForm(initial={"certificate_event": event_id})
    context = {"event": event, "form": form, "background_link": settings.LINK_BACKGROUND,
               "csv_example": static('csv_example.csv')}
    return render(request, "events/event_certificate_upload.html", context)


def event_download_certificates(request, event_id, certificate_id=None):
        event = Event.objects.get(pk=event_id)

        user = request.user
        if certificate_id:
            return download_certificate(event, certificate_id, user)
        else:
            return download_certificates(event, user)


@permission_required('certificates.add_certificate', raise_exception=True)
def event_confirm_certification(request, event_id):
    event = Event.objects.get(pk=event_id)
    if request.method == "POST":
        try:
            with ((transaction.atomic())):
                csv_table = request.POST.get('csv_table', None)
                background = request.POST.get('background', None)

                if not csv_table or not background:
                    return redirect(reverse("events:event_certificate", kwargs={"event_id": event.id}))
                else:
                    df = pd.read_csv(StringIO(csv_table))

                    for i, row in df.iterrows():
                        certificate_create(row, event, background, request.user)

                    return redirect(reverse("events:event_detail", kwargs={"event_id": event.id}))
        except Exception as e:
            return redirect(reverse("events:event_certificate", kwargs={"event_id": event.id}))
    else:
        return redirect(reverse("events:event_detail", kwargs={"event_id": event.id}))