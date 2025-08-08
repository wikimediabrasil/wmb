import datetime
from django.shortcuts import render, redirect, reverse
from django.contrib.auth.decorators import permission_required

from certificates.forms import CertificateForm
from certificates.models import Certificate
from certificates.utils import certificate_create, make_one_certificate_pdf

from events.models import Event

from users.models import Participant


@permission_required('certificates.add_certificate', raise_exception=True)
def certificate_create_manually(request, event_id):
    form = CertificateForm(request.POST or None)
    event = Event.objects.get(id=event_id)
    context = {"form": form, "event": event}

    number_of_certificates = Certificate.objects.filter(event=event).count()

    if number_of_certificates > 0:
        if request.method == "POST":
            username = form.data.get('username_string')
            if username:
                Participant.objects.get_or_create(participant_username=username)

            if form.is_valid():
                background = Certificate.objects.filter(event=event).first().background
                certificate_create(form.cleaned_data, event, background, request.user, form.cleaned_data["with_hours"])
                return redirect(reverse("events:event_detail", kwargs={"event_id": event.id}))
        return render(request, "certificates/certificate_create.html", context)
    else:
        return redirect(reverse("events:event_certificate", kwargs={"event_id": event.id}))


@permission_required('certificates.change_certificate', raise_exception=True)
def certificate_update(request, event_id, certificate_id):
    certificate = Certificate.objects.get(pk=certificate_id)
    event = Event.objects.get(pk=event_id)
    form = CertificateForm(request.POST or None, instance=certificate)
    context = {"certificate": certificate, "event": event, "form": form}

    if request.method == "POST":
        if form.is_valid():
            form.save()

            username_string = form.cleaned_data.get('username_string')
            if username_string:
                participant = Participant.objects.filter(participant_username=username_string).first()
                if participant:
                    certificate.username = participant
                    certificate.save()
                else:
                    participant = Participant.objects.create(participant_full_name = form.cleaned_data.get('name'),
                                                             participant_username = username_string,
                                                             enrolled_at = datetime.datetime.today(),
                                                             created_by = request.user,
                                                             modified_by = request.user)
                    participant.save()
                    certificate.username = participant
                    certificate.save()

            return redirect(reverse("events:event_detail", kwargs={"event_id": event_id}))

    return render(request, "certificates/certificate_update.html", context)


@permission_required('certificates.delete_certificate', raise_exception=True)
def certificate_delete(request, event_id, certificate_id):
    certificate = Certificate.objects.get(pk=certificate_id)
    event = Event.objects.get(pk=event_id)
    context = {"certificate": certificate, "event": event}

    if request.method == "POST":
        certificate.delete()
        return redirect(reverse("events:event_detail", kwargs={"event_id": event_id}))

    return render(request, "certificates/certificate_delete.html", context)


def certificate_list(request):
    user = request.user
    certificates = Certificate.objects.filter(username__participant_username=user.username)
    context = {"certificates": certificates}
    return render(request, "certificates/certificate_list.html", context)


def certificate_validate(request):
    if request.method == "POST":
        certificate_hash = request.POST["certificate_hash"]
        certificate = Certificate.objects.filter(certificate_hash=certificate_hash).first()
        if certificate:
            context = {"certificate": certificate}
            return render(request, "certificates/certificate_detail.html", context)
        else:
            return render(request, "certificates/certificate_validate.html")
    else:
        return render(request, "certificates/certificate_validate.html")


def certificate_download_by_hash(request, certificate_hash):
    certificate = Certificate.objects.filter(certificate_hash=certificate_hash).first()

    if certificate:
        return make_one_certificate_pdf(certificate)
    else:
        return redirect(reverse("certificates:certificate_validate"))