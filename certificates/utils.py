import io
import os
import re
import math
import locale
import calendar
import hashlib
import pandas as pd
import datetime
import zipfile
from dataclasses import dataclass
from typing import Optional
from fpdf import FPDF

from django.http import HttpResponse
from django.conf import settings
from django.shortcuts import redirect, reverse, get_object_or_404
from django.utils.translation import gettext_lazy as _

from certificates.models import Certificate, PRONOUN_CHOICES
from users.models import Participant


class CertificationPDF(FPDF):
    """
    Class for the PDF to be made
    """

    def header(self):
        pass

    def footer(self):
        pass


def clean_string(text):
    """
    Function to clean strings of invalid filename characters

    :param text: String to be cleaned
    :return: String with invalid filename characters removed
    """
    invalid_characters = '\\/:*?"<>|'
    for ic in invalid_characters:
        text = text.replace(ic, "")
    return text


def build_role(role):
    """
    Function to build the part of the certificate text that
    identifies the type of certificate, if the person was a
    role for the event or not

    :param role: name of the role the person did in the event
    :return: string stating the role the person did
    """
    if role == _("participant"):
        return ""
    else:
        return " como " + role


def format_certificate_date(date_start, date_end):
    d_start, d_end = date_start.day, date_end.day
    m_start, m_end = calendar.month_name[date_start.month], calendar.month_name[date_end.month]
    y_start, y_end = date_start.year, date_end.year

    if date_start == date_end:
        date_formatted = _("on {m_start} {d_start}, {y_start}").format(d_start=d_start,
                                                                       m_start=m_start,
                                                                       y_start=y_start)
    elif date_start.year == date_end.year:
        if date_start.month == date_end.month:
            date_formatted = _("from {m_start} {d_start} to {d_end}, {y_start}").format(d_start=d_start,
                                                                                        m_start=m_start,
                                                                                        y_start=y_start,
                                                                                        d_end=d_end)
        else:
            date_formatted = _("from {m_start} {d_start} to {m_end} {d_end}, {y_start}").format(d_start=d_start,
                                                                                                m_start=m_start,
                                                                                                y_start=y_start,
                                                                                                d_end=d_end,
                                                                                                m_end=m_end)
    else:
        date_formatted = _("from {m_start} {d_start}, {y_start} to {m_end} {d_end}, {y_end}").format(d_start=d_start,
                                                                                                     m_start=m_start,
                                                                                                     y_start=y_start,
                                                                                                     d_end=d_end,
                                                                                                     m_end=m_end,
                                                                                                     y_end=y_end)
    return date_formatted


########################################################################################################################
# BATCH RENDERING CONTEXT
########################################################################################################################

@dataclass
class CertificateRenderContext:
    """
    Pre-computed per-event constants.
    Build once with build_render_context(event) before the certificate loop,
    then pass into every make_pdf_of_certificate() call.
    """
    event_name: str
    event_name_clean: str
    phrase_date: str
    president: str
    president_role: str
    signature_path: str
    font_regular: str
    font_bold: str


_TARGET_DATE = datetime.date(2025, 11, 8)


def build_render_context(event) -> CertificateRenderContext:
    """
    Call once per batch (before the certificate loop).
    Sets the locale, resolves the president/signature, formats the date,
    and resolves font paths — so none of this happens per certificate.
    """
    locale.setlocale(locale.LC_TIME, "pt_BR")

    if event.date_end < _TARGET_DATE:
        president = str(_("VALÉRIO ANDRADE MELO"))
        signature = settings.VALERIOS_SIGNATURE
    else:
        president = str(_("ÉRICA CAMILLO AZZELLINI"))
        signature = settings.ERICAS_SIGNATURE

    event_name = str(event)

    return CertificateRenderContext(
        event_name=event_name,
        event_name_clean=clean_string(event_name),
        phrase_date=format_certificate_date(event.date_start, event.date_end),
        president=president,
        president_role=str(_("President of Wikimedia Brasil")),
        signature_path=str(os.path.join(settings.BASE_DIR, 'static', 'images', signature)),
        font_regular=os.path.join(settings.BASE_DIR, 'static/fonts/Merriweather-Regular.ttf'),
        font_bold=os.path.join(settings.BASE_DIR, 'static/fonts/Merriweather-Bold.ttf'),
    )


########################################################################################################################
# PDF GENERATION
########################################################################################################################

def make_pdf_of_certificate(certificate, ctx: Optional[CertificateRenderContext] = None):
    """
    Renders a single certificate PDF.

    Pass a CertificateRenderContext built with build_render_context(event) when
    generating a batch — it avoids redundant locale, font, date, and
    president/signature work on every call.

    For single-certificate use (e.g. download_certificate), ctx can be omitted
    and a throwaway context will be built automatically.
    """
    if ctx is None:
        ctx = build_render_context(certificate.event)

    pdf = CertificationPDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    pdf.set_text_color(0, 0, 0)

    if certificate.background:
        pdf.image(certificate.background.path, x=0, y=0, w=297, h=210)

    #######################################################################################################
    # Header
    #######################################################################################################
    pdf.set_y(15)  # Start the letter text at the 10x42mm point

    pdf.add_font('Merriweather', '', os.path.join(settings.BASE_DIR, 'static/fonts/Merriweather-Regular.ttf'), uni=True)
    pdf.add_font('Merriweather-Bold', '', os.path.join(settings.BASE_DIR, 'static/fonts/Merriweather-Bold.ttf'), uni=True)
    pdf.set_font('Merriweather', '', 35)  # Text of the body in Times New Roman, regular, 13 pt

    pdf.set_font('Merriweather', '', 13)
    pdf.cell(w=0, h=5, ln=1)
    pdf.cell(w=0, h=5, border=0, ln=1, align='C',
             txt=str(_('The Wikimedia Brasil chapter (CNPJ 29.801.908/0001-86) certifies that')))
    pdf.cell(w=0, h=5, ln=1)

    # ------------------------------------------------------------------
    # Participant name — shrink to fit page width if necessary
    # ------------------------------------------------------------------
    name = certificate.name
    pdf.set_font('Merriweather', '', 30)
    name_size = pdf.get_string_width(name)

    if name_size > 287:
        # Try to eliminate the prepositions
        name_split = [name_part for name_part in name.split(' ') if not name_part.islower()]
        # There's a first and last names and at least one middle name
        if len(name_split) > 2:
            name = name_split[0] + ' ' + ' '.join(p[0] + '.' for p in name_split[1:-1]) + ' ' + name_split[-1]
            name_size = pdf.get_string_width(name)
        if name_size > 287:
            pdf.set_font('Merriweather', '', math.floor(287 * 35 / name_size))

    pdf.cell(w=0, h=10, border=0, ln=1, align='C', txt=str(name))
    pdf.cell(w=0, h=5, ln=1)

    #######################################################################################################
    # participated in the event
    #######################################################################################################
    pdf.set_font('Merriweather', '', 13)
    phrase_participation = _("participated %(role)s in the event") % {"role": build_role(certificate.role)}
    pdf.cell(w=0, h=5, border=0, ln=1, align='C', txt=str(phrase_participation))
    pdf.cell(w=0, h=5, ln=1)

    #######################################################################################################
    # Name of the event
    #######################################################################################################
    event_name = str(certificate.event)
    pdf.set_font('Merriweather-Bold', '', min(20, math.floor(62 * 20 / len(event_name))))
    pdf.cell(w=0, h=10, border=0, ln=1, align='C', txt=event_name)
    pdf.cell(w=0, h=5, ln=1)  # New line

    #######################################################################################################
    # Dates and hours
    #######################################################################################################
    pdf.set_font('Merriweather', '', 13)
    if certificate.with_hours:
        phrase_time = str(_("%(date)s (Credit hours: %(hours)s).") % {
            "date": ctx.phrase_date, "hours": certificate.hours
        })
    else:
        phrase_time = str(_("%(date)s.") % {"date": ctx.phrase_date})

    pdf.cell(w=0, h=5, border=0, ln=1, align='C', txt=phrase_time)
    pdf.cell(w=0, h=15, ln=1)

    # ------------------------------------------------------------------
    # Signature block — all from context
    # ------------------------------------------------------------------
    y = pdf.get_y()
    pdf.image(ctx.signature_path, x=131, y=y - 5, w=35, h=16)
    pdf.cell(w=0, h=5, border=0, ln=1, align='C', txt="______________________")
    pdf.cell(w=0, h=10, border=0, ln=1, align='C', txt=ctx.president)
    pdf.set_font('Merriweather', '', 11)
    pdf.cell(w=0, h=5, border=0, ln=1, align='C', txt=ctx.president_role)

    # ------------------------------------------------------------------
    # Footer — hash is per certificate
    # ------------------------------------------------------------------
    validation_phrase = str(
        _('The validity of this document can be checked at https://wmb.toolforge.org/. '
          'The hash code for validation is: %(certificate_hash)s')
        % {"certificate_hash": certificate.certificate_hash}
    )
    pdf.in_footer = 1
    pdf.set_y(-16.5)
    pdf.set_font('Merriweather', '', 8.8)
    pdf.cell(w=0, h=5, border=0, ln=1, align='C', txt=validation_phrase)
    pdf.in_footer = 0

    return pdf


########################################################################################################################
# CERTIFICATE VALIDATION AND CREATION
########################################################################################################################
def validate_csv(df):
    errors = []

    if not {"name", "username", "pronoun", "hours", "role"}.issubset(df.columns):
        errors.append(_("One or more required columns are missing. Verify and submit again"))
    else:
        if not df.empty:
            for i, row in df.iterrows():
                if pd.isnull(row["name"]) or not isinstance(row["name"], str):
                    errors.append(_("Name invalid! Verify row %(row)s, column 'name'") % {"row": i + 1})
                if pd.isnull(row["pronoun"]) or not isinstance(row["pronoun"], str) or row["pronoun"].lower() not in {pronoun[0] for pronoun in PRONOUN_CHOICES}:
                    errors.append(_("Pronoun invalid! Verify row %(row)s, column 'pronoun'") % {"row": i + 1})
                if pd.isnull(row["hours"]) or not isinstance(row["hours"], str) or not re.match(r"^\d+[h,H]\d+$", str(row["hours"])):
                    errors.append(_("Hours invalid! Verify row %(row)s, column 'hours'") % {"row": i + 1})
                if pd.isnull(row["role"]) or not isinstance(row["role"], str):
                    errors.append(_("Role invalid! Verify row %(row)s, column 'role'") % {"row": i + 1})
        else:
            errors.append(_("Your CSV file is empty. Verify and submit again"))
    return errors


def certificate_create(data, event, background, emitted_by, with_hours=True):
    if "username_string" in data:
        certificate_user = data["username_string"]
    else:
        certificate_user = data["username"]
    full_name = data["name"].strip()

    certificate_data = {}
    if certificate_user and certificate_user != "-":
        if isinstance(certificate_user, str):
            certificate_user, created = Participant.objects.get_or_create(participant_username=certificate_user)
            if created:
                certificate_user.created_by = certificate_user.modified_by = emitted_by
                certificate_user.enrolled_at = datetime.datetime.today()
                certificate_user.save()

        if not certificate_user.participant_full_name:
            certificate_user.participant_full_name = certificate_name = full_name
            certificate_user.save()
        else:
            certificate_name = certificate_user.participant_full_name
    else:
        certificate_user = Participant.objects.create(participant_full_name=full_name)
        certificate_user.created_by = certificate_user.modified_by = emitted_by
        certificate_user.enrolled_at = datetime.datetime.today()
        certificate_user.save()
        certificate_name = certificate_user.participant_full_name

    certificate_data["username"] = certificate_user
    hash_aux = "Certificate " + certificate_name + str(event) + data["hours"] + str(data["role"])
    certificate_hash = hashlib.sha1(bytes(hash_aux, 'utf-8')).hexdigest()

    certificate_data["name"] = full_name
    certificate_data["pronoun"] = data["pronoun"].strip()
    certificate_data["event"] = event
    certificate_data["hours"] = data["hours"].strip()
    certificate_data["with_hours"] = with_hours
    certificate_data["role"] = data["role"].strip()
    certificate_data["background"] = background
    certificate_data["certificate_hash"] = certificate_hash
    certificate_data["emitted_by"] = emitted_by

    certificate = Certificate(**certificate_data)
    certificate.save()

    certificate_user.number_of_certificates += 1
    certificate_user.save()
    return certificate


########################################################################################################################
# CERTIFICATES DOWNLOAD
########################################################################################################################

def make_one_certificate_pdf(certificate):
    # build_render_context called implicitly inside make_pdf_of_certificate
    # when no ctx is passed — fine for single-certificate use.
    pdf = make_pdf_of_certificate(certificate)
    file = pdf.output(dest='S').encode('latin-1')
    response = HttpResponse(file, content_type='application/pdf')
    content_disposition = 'attachment; filename="{} - {}.pdf"'.format(
        _("Certificate"), clean_string(certificate.name)
    )
    response['Content-Disposition'] = content_disposition
    return response


def download_certificate(event, certificate_id, user):
    if user.has_perm('certificates.download_all'):
        certificate = get_object_or_404(Certificate, event=event, pk=certificate_id)
    else:
        certificate = get_object_or_404(Certificate, event=event, username__participant_username=user.username)

    return make_one_certificate_pdf(certificate)


def download_certificates(event, user):
    if not user.has_perm('certificates.download_all'):
        return redirect(reverse("events:event_detail", kwargs={"event_id": event.id}))

    certificates = Certificate.objects.filter(event=event).select_related('event')

    # Build the context once — locale, date, president, fonts resolved here,
    # not inside the loop.
    ctx = build_render_context(event)

    s = io.BytesIO()
    zf = zipfile.ZipFile(s, "w", compression=zipfile.ZIP_DEFLATED)

    for certificate in certificates:
        pdf = make_pdf_of_certificate(certificate, ctx)
        file = pdf.output(dest='S').encode('latin-1')
        zf.writestr("{}/{}/{} {}.pdf".format(ctx.event_name_clean, clean_string(certificate.role), _("Certificate"), clean_string(certificate.name)),file)

    zf.close()

    response = HttpResponse(s.getvalue())
    response['Content-Disposition'] = 'attachment; filename="{} - {}.zip"'.format(_("Certificates"), ctx.event_name_clean)
    response['Content-Type'] = 'application/zip'
    return response