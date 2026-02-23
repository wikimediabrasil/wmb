from datetime import date
from django.utils.translation import gettext_lazy as _
from django.db import transaction
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, permission_required
from django.urls import reverse

from .models import Credential
from .forms import CredentialForm
from .services.wikimedia import shorten_url


# LIST
def credential_list(request):
    if not request.user.has_perm("credentials.add_credential"):
        return redirect("credentials:credential_validate")

    credentials = Credential.objects.all().order_by("-issued_at")
    return render(request, "credentials/credential_list.html", {"credentials": credentials})


# DETAIL
@permission_required("credentials.view_credential", raise_exception=True)
def credential_detail(request, verification_code):
    credential = get_object_or_404(Credential, verification_code=verification_code)
    return render(request, "credentials/credential_detail.html", {
        "credential": credential
    })


# CREATE
@permission_required("credentials.add_credential")
def credential_create(request):
    if request.method == "POST":
        form = CredentialForm(request.POST)
        if form.is_valid():
            credential = form.save(commit=False)
            credential.issued_by = request.user
            credential.save()

            def generate_short_url():
                long_url = credential.get_wikimedia_profile_url()
                short = shorten_url(long_url)

                if short:
                    credential.url = short
                    credential.save(update_fields=["url"])

            transaction.on_commit(generate_short_url)

            return redirect(reverse("credentials:credential_detail", kwargs={"verification_code":credential.verification_code}))
    else:
        form = CredentialForm()

    return render(request, "credentials/credential_create.html", {
        "form": form
    })


# UPDATE
@permission_required("credentials.change_credential")
def credential_update(request, verification_code):
    credential = get_object_or_404(Credential, verification_code=verification_code)

    if request.method == "POST":
        form = CredentialForm(request.POST, instance=credential)
        if form.is_valid():
            form.save()
            return redirect("credentials:credential_detail", verification_code=verification_code)
    else:
        form = CredentialForm(instance=credential)

    return render(request, "credentials/credential_update.html", {
        "form": form,
        "credential": credential
    })


# DELETE
@permission_required("credentials.delete_credential")
def credential_delete(request, verification_code):
    credential = get_object_or_404(Credential, verification_code=verification_code)

    if request.method == "POST":
        credential.delete()
        return redirect(reverse("credentials:credential_list"))

    return render(request, "credentials/credential_delete.html", {
        "credential": credential
    })


def credential_validate(request):
    if request.method == "POST":
        verification_code = request.POST.get("verification_code", "").strip()

        if verification_code:
            try:
                credential = Credential.objects.get(verification_code=verification_code)
                if credential.valid_until < date.today():
                    return render(request,"credentials/credential_validate.html", {"error": _("This credential verification code has expired.")})
                else:
                    return render(request, "credentials/credential_detail.html", {"credential": credential})
            except Credential.DoesNotExist:
                pass

        return render(request, "credentials/credential_validate.html", {"error": _("Invalid verification code.")})

    return render(request, "credentials/credential_validate.html")
