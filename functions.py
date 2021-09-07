import hashlib
import locale
import math
import os
import re
from datetime import datetime
from flask_login import login_required
from fpdf import FPDF


class CertificationPDF(FPDF):
    def header(self):
        pass

    def footer(self):
        pass


def clean_string(text):
    invalid_characters = '\\/:*?"<>|'
    for ic in invalid_characters:
        text = text.replace(ic, "")
    return text


def role(host, pronoun):
    if host == "verdadeiro" or host == "true":
        if pronoun.lower() == "a":
            return "palestrante convidada"
        else:
            return "palestrante convidado"
    else:
        return "ouvinte"


def check_hour(hour):
    try:
        if re.compile(r"\d{2}h\d{2}").match(hour):
            return True
        else:
            return False
    except ValueError:
        return False


def check_pronoun(pronoun):
    pronouns = ['a', 'o']
    try:
        if not pronoun.lower() in pronouns:
            return False
    except ValueError:
        return False
    return True


def check_date(date_text):
    try:
        datetime.strptime(date_text, '%d/%m/%Y')
    except ValueError:
        return False
    return True


def check_host(host):
    possible_values = ["verdadeiro", "falso", "true", "false"]

    try:
        if host.lower() not in possible_values:
            return False
    except ValueError:
        return False
    return True


def tf_host(host):
    positive_values = ["verdadeiro", "true"]
    if host.lower() in positive_values:
        return True
    else:
        return False


def check_columns(table):
    columns = ["name", "username", "pronoun", "event", "date", "hours"]
    for col in columns:
        if col not in list(table.columns):
            return False
    return True


@login_required
def make_pdf_of_user(user, app):
    # Create page
    pdf = CertificationPDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    pdf.set_text_color(0, 0, 0)
    pdf.image(os.path.join(app.config['UPLOAD_FOLDER'], user.background), x=0, y=0, w=297, h=210)

    #######################################################################################################
    # Header
    #######################################################################################################
    pdf.set_y(20)  # Start the letter text at the 10x42mm point

    pdf.add_font('Merriweather', '', os.path.join(app.static_folder, 'fonts/Merriweather-Regular.ttf'), uni=True)
    pdf.add_font('Merriweather-Bold', '', os.path.join(app.static_folder, 'fonts/Merriweather-Bold.ttf'), uni=True)
    pdf.set_font('Merriweather', '', 37)  # Text of the body in Times New Roman, regular, 13 pt

    locale.setlocale(locale.LC_TIME, "pt_BR")  # Setting the language to portuguese for the date
    pdf.cell(w=0, h=10, border=0, ln=1, align='C', txt='CERTIFICADO')

    pdf.set_font('Merriweather', '', 14.5)
    pdf.cell(w=0, h=10, ln=1)  # New line
    pdf.cell(w=0, h=10, border=0, ln=1, align='C', txt='O grupo de usuários Wiki Movimento Brasil '
                                                       '(CNPJ 29.801.908/0001-86), certifica que')
    pdf.cell(w=0, h=10, ln=1)  # New line

    #######################################################################################################
    # User name
    #######################################################################################################
    name = user.name  # User full name
    pdf.set_font('Merriweather', '', 35)
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

    pdf.cell(w=0, h=10, border=0, ln=1, align='C', txt=name)
    pdf.cell(w=0, h=10, ln=1)  # New line

    #######################################################################################################
    # por ter completado as leituras e as 6 tarefas do curso online
    #######################################################################################################
    pdf.set_font('Merriweather', '', 14.5)
    phrase_participation = "participou como " + role(user.host, user.pronoun) + " do evento"
    pdf.cell(w=0, h=10, border=0, ln=1, align='C', txt=phrase_participation)
    pdf.cell(w=0, h=8, ln=1)  # New line

    #######################################################################################################
    # Introdução ao Jornalismo Científico
    #######################################################################################################
    pdf.set_font('Merriweather-Bold', '', 21)
    pdf.cell(w=0, h=10, border=0, ln=1, align='C', txt=user.event)
    pdf.cell(w=0, h=8, ln=1)  # New line

    #######################################################################################################
    # no dia X (Carga horária: Y horas)
    #######################################################################################################
    pdf.set_font('Merriweather', '', 14.5)
    date = datetime.strptime(user.date, "%d/%m/%Y").date()
    phrase_time = "no dia " + date.strftime("%d de %B de %Y") + " (Carga horária: " + user.hours + ")."
    pdf.cell(w=0, h=10, border=0, ln=1, align='C', txt=phrase_time)
    pdf.cell(w=0, h=8, ln=1)  # New line

    user_hash = hashlib.sha1(
        bytes("Certificate " + user.name + user.event + user.hours + str(user.host), 'utf-8')).hexdigest()
    pdf.in_footer = 1
    pdf.set_y(-16.5)
    pdf.set_font('Merriweather', '', 8.8)
    pdf.cell(w=0, h=6.5, border=0, ln=1, align='C',
             txt='A validade deste documento pode ser checada em https://wmb.toolforge.org/. '
                 'O código de validação é:' + user_hash)
    pdf.in_footer = 0

    return pdf
