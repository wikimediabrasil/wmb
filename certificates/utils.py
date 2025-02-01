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


def make_pdf_of_certificate(certificate):
    # Create page
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

    title_phrase = _('CERTIFICATE')
    locale.setlocale(locale.LC_TIME, "pt_BR")  # Setting the language to portuguese for the date
    pdf.cell(w=0, h=10, border=0, ln=1, align='C', txt=str(title_phrase))

    identification_phrase = _('The user group Wiki Movement Brazil (CNPJ 29.801.908/0001-86) certifies that')
    pdf.set_font('Merriweather', '', 13)
    pdf.cell(w=0, h=5, ln=1)  # New line
    pdf.cell(w=0, h=5, border=0, ln=1, align='C', txt=str(identification_phrase))
    pdf.cell(w=0, h=5, ln=1)  # New line

    #######################################################################################################
    # User name
    #######################################################################################################
    name = certificate.name  # User full name
    pdf.set_font('Merriweather', '', 30)
    name_size = pdf.get_string_width(name)

    if name_size > 287:
        # Try to eliminate the prepositions
        name_split = [name_part for name_part in name.split(' ') if not name_part.islower()]
        # There's a first and last names and at least one middle name
        if len(name_split) > 2:
            first_name = name_split[0]
            last_name = name_split[-1]
            middle_names = [md_name[0] + '.' for md_name in name_split[1:-1]]
            name = first_name + ' ' + ' '.join(middle_names) + ' ' + last_name
            name_size = pdf.get_string_width(name)

        # Even abbreviating, there is still the possibility that the name is too big, so
        # we need to adjust it to the proper size
        if name_size > 287:
            pdf.set_font('Merriweather', '', math.floor(287 * 35 / name_size))

    pdf.cell(w=0, h=10, border=0, ln=1, align='C', txt=str(name))
    pdf.cell(w=0, h=5, ln=1)  # New line

    #######################################################################################################
    # participated in the event
    #######################################################################################################
    pdf.set_font('Merriweather', '', 13)
    phrase_participation = _("participated %(role)s in the event") % {"role": build_role(certificate.role)}
    pdf.cell(w=0, h=5, border=0, ln=1, align='C', txt=str(phrase_participation))
    pdf.cell(w=0, h=5, ln=1)  # New line

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

    phrase_date = format_certificate_date(certificate.event.date_start, certificate.event.date_end)
    phrase_time = _("%(date)s (Credit hours: %(hours)s).") % {"date": phrase_date, "hours": certificate.hours}

    pdf.cell(w=0, h=5, border=0, ln=1, align='C', txt=str(phrase_time))
    pdf.cell(w=0, h=15, ln=1)  # New line

    y = pdf.get_y()
    president = _("VALÉRIO ANDRADE MELO")
    president_role = _("President of Wiki Movement Brazil")
    pdf.image(str(os.path.join(settings.BASE_DIR, 'static', 'images', settings.SIGNATURE)), x=131, y=y-5, w=35, h=16)
    pdf.cell(w=0, h=5, border=0, ln=1, align='C', txt="______________________")
    pdf.cell(w=0, h=10, border=0, ln=1, align='C', txt=str(president))
    pdf.set_font('Merriweather', '', 11)
    pdf.cell(w=0, h=5, border=0, ln=1, align='C', txt=str(president_role))

    user_hash = certificate.certificate_hash
    validation_phrase =_('The validity of this document can be checked at https://wmb.toolforge.org/. The hash code for validation is: %(certificate_hash)s') % {"certificate_hash": user_hash}
    pdf.in_footer = 1
    pdf.set_y(-16.5)
    pdf.set_font('Merriweather', '', 8.8)
    pdf.cell(w=0, h=5, border=0, ln=1, align='C', txt=str(validation_phrase))
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


def certificate_create(data, event, background, emitted_by):
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
    certificate_data["role"] = data["role"].strip()
    certificate_data["background"] = background
    certificate_data["certificate_hash"] = certificate_hash
    certificate_data["emitted_by"] = emitted_by

    certificate = Certificate(**certificate_data)
    certificate.save()

    certificate_user.number_of_certificates += 1
    certificate_user.save()
    return certificate


# ======================================================================================================================
# CERTIFICATES DOWNLOAD
# ======================================================================================================================
def make_one_certificate_pdf(certificate):
    pdf = make_pdf_of_certificate(certificate)
    file = pdf.output(dest='S').encode('latin-1')
    response = HttpResponse(file, content_type='application/pdf')
    content_disposition = 'attachment; filename="{} - {}.pdf"'.format(_("Certificate"), clean_string(certificate.name))
    response['Content-Disposition'] = content_disposition
    return response


def download_certificate(event, certificate_id, user):
    if user.has_perm('certificates.download_all'):
        certificate = get_object_or_404(Certificate, event=event, pk=certificate_id)
    else:
        certificate = get_object_or_404(Certificate, event=event, username__participant_username=user.username)

    return make_one_certificate_pdf(certificate)


def download_certificates(event, user):
    if user.has_perm('certificates.download_all'):
        certificates = Certificate.objects.filter(event=event)
        s = io.BytesIO()
        zf = zipfile.ZipFile(s, "w")
        zipfilenames = []

        for certificate in certificates:
            zipfilenames.append(clean_string(str(certificate.event)))
            pdf = make_pdf_of_certificate(certificate)

            file = pdf.output(dest='S').encode('latin-1')
            zf.writestr("{}/{} {}.pdf".format(clean_string(str(certificate.event)), _("Certificate"), clean_string(certificate.name)), file)

        zf.close()
        response = HttpResponse(s.getvalue())
        content_disposition = 'attachment; filename="{} - {}.zip"'.format(_("Certificates"), '; '.join(list(set(zipfilenames))))
        response['Content-Disposition'] = content_disposition
        response['Content-Type'] = 'application/zip'
        return response
    else:
        return redirect(reverse("events:event_detail", kwargs={"event_id": event.id}))