from flask import Flask, render_template, request, make_response, redirect, url_for
import pandas as pd
import yaml
import os
import zipfile
import io
import csv
import locale
import math
import hashlib
import cryptography
from fpdf import FPDF
from pandas_schema import Schema, Column
from pandas_schema.validation import CustomElementValidation
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy_utils import StringEncryptedType
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.exc import SQLAlchemyError
from flask_bootstrap import Bootstrap
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField
from wtforms.validators import InputRequired, Email, Length
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user

__dir__ = os.path.dirname(__file__)
app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///'
app.config['SQLALCHEMY_BINDS'] = {'users': 'sqlite:///users.db',
                                  'wmb_admin': 'sqlite:///wmb_admin.db'}
app.config.update(yaml.safe_load(open(os.path.join(__dir__, 'config.yaml'))))

bootstrap = Bootstrap(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Initialize the database
db = SQLAlchemy(app)

key = app.config["ENCRYPTION_KEY"]


class LoginForm(FlaskForm):
    username = StringField('Nome de usuário(a)', validators=[InputRequired(), Length(min=4, max=20)])
    password = PasswordField('Senha', validators=[InputRequired(), Length(min=6, max=20)])


class SignupForm(FlaskForm):
    username = StringField('Nome de usuário(a)', validators=[InputRequired(), Length(min=4, max=20)])
    email = StringField('Email', validators=[InputRequired(), Length(max=50)])
    password = PasswordField('Senha', validators=[InputRequired(), Length(min=6, max=20)])


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField('Senha atual', validators=[InputRequired(), Length(min=6, max=20)])
    password = PasswordField('Nova senha', validators=[InputRequired(), Length(min=6, max=20)])
    confirmation_password = PasswordField('Confirme sua nova senha', validators=[InputRequired(), Length(min=6, max=20)])


class WMBUser(UserMixin, db.Model):
    __tablename__ = 'wmb_admin'
    __bind_key__ = 'wmb_admin'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True)
    email = db.Column(db.String(50), unique=True)
    password = db.Column(db.String(80))


@login_manager.user_loader
def load_user(user_id):
    return WMBUser.query.get(int(user_id))


# Create database (db) model
class Users(db.Model):
    __tablename__ = 'users'
    __bind_key__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(StringEncryptedType(db.String(150), key), nullable=False)
    username = db.Column(StringEncryptedType(db.String(150), key), nullable=True)
    pronoun = db.Column(db.String(1), nullable=False)
    event = db.Column(StringEncryptedType(db.String(300), key), nullable=False)
    date = db.Column(db.String(10), default=datetime.utcnow().strftime('%d/%m/%Y'), nullable=False)
    hours = db.Column(db.String(5), nullable=False)
    host = db.Column(StringEncryptedType(db.Boolean, key), nullable=False)
    background = db.Column(StringEncryptedType(db.String(500), key), nullable=False)

    def __repr__(self):
        return '<User %r>' % self.username


class CertificationPDF(FPDF):
    def header(self):
        pass

    def footer(self):
        # user = Users.query.filter_by(username=username).first()
        # date_modified = user.date_modified
        # user_hash = hashlib.sha1(bytes("Certificate " + username + str(date_modified), 'utf-8')).hexdigest()
        # self.set_y(-16.5)
        # self.set_font('Merriweather', '', 8.8)
        # self.cell(w=0, h=6.5, border=0, ln=1, align='C',
        #           txt='A validade deste documento pode ser checada em https://ijc.toolforge.org/. '
        #               'O código de validação é: Eder')
        pass


@app.route('/login', methods=["GET", "POST"])
def login():
    form = LoginForm()

    if form.validate_on_submit():
        user = WMBUser.query.filter_by(username=form.username.data).first()
        if user:
            if check_password_hash(user.password,form.password.data):
                login_user(user, remember=True)
                return redirect(url_for('certificate'))
            else:
                return "<h1>Senha inválida</h1>"
        else:
            return "<h1>Usuário inválido ou não existente</h1>"

    return render_template('login.html', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))


@app.route('/usuarios/criar', methods=["GET", "POST"])
@login_required
def create_wmbuser():
    form = SignupForm()

    if form.validate_on_submit():
        hashed_password = generate_password_hash(form.password.data, method='sha256')
        new_user = WMBUser(username=form.username.data, email=form.email.data, password=hashed_password)
        try:
            db.session.add(new_user)
            db.session.commit()
            return redirect(url_for('create_wmbuser'))
        except:
            return "<h1>Erro na inserção de usuário(a)</h1>"

    return render_template('create_user.html', form=form)


@app.route('/alterarsenha', methods=["GET", "POST"])
@login_required
def mudar_senha_wmbuser():
    form = ChangePasswordForm()

    if form.validate_on_submit():
        user = WMBUser.query.filter_by(id=current_user.id).first()
        if user:
            if check_password_hash(user.password, form.current_password.data):
                if form.password.data == form.confirmation_password.data:
                    hashed_password = generate_password_hash(form.confirmation_password.data, method='sha256')
                    user.password = hashed_password

                    try:
                        db.session.commit()
                        logout_user()
                        return redirect(url_for('login'))
                    except:
                        return "<h1>Não foi possível alterar sua senha</h1>"
                else:
                    return "<h1>Erro na confirmação da senha</h1>"
            else:
                logout_user()
                return "<h1>Senha atual inválida. Faça login novamente e tente de novo"
        else:
            redirect(url_for('home'))
    else:
        return render_template("change_password.html", form=form)


@app.route('/')
def home():
    return render_template('home.html')


@app.route('/certificado', methods=['GET', 'POST'])
@login_required
def certificate():
    if request.method == "POST":
        uploaded_file = request.files['certificate_csv']
        background_file = request.files['background']
        background_file_filename = secure_filename(
            datetime.now().strftime("%m-%d-%Y-%H-%M-%S") + background_file.filename)
        background_file.save(os.path.join(app.config['UPLOAD_FOLDER'], background_file_filename))
        file = pd.read_csv(uploaded_file)

        file["background"] = background_file_filename

        if check_columns(file):
            pronoun_validation = [
                CustomElementValidation(lambda d: check_pronoun(d), 'valores inválidos para a coluna "pronouns"')]
            date_validation = [
                CustomElementValidation(lambda d: check_date(d), 'valores inválidos para a coluna "date"')]
            hour_validation = [
                CustomElementValidation(lambda d: check_hour(d), 'valores inválidos para a coluna "hours"')]
            host_validation = [
                CustomElementValidation(lambda d: check_host(d), 'valores inválidos para a coluna "host"')]

            schema = Schema([
                Column("name", allow_empty=False),
                Column("username", allow_empty=True),
                Column("pronoun", pronoun_validation, allow_empty=False),
                Column("event", allow_empty=False),
                Column("date", date_validation, allow_empty=False),
                Column("hours", hour_validation, allow_empty=False),
                Column("host", host_validation, allow_empty=False),
                Column("background", allow_empty=False),
            ])

            errors = schema.validate(file)

            if errors.__len__() > 0:
                html_file = pd.DataFrame({'erros': errors}).to_html()
                csv_table = ""
            else:
                html_file = file.to_html()
                csv_table = file.to_csv()
            return render_template('generate_certificate.html', table=html_file, csv_table=csv_table)
        else:
            return 'Sua tabela não possui as colunas com os nomes corretos'
    else:
        return render_template('certificate.html', background_link=app.config['LINK_BACKGROUND'])


@app.route('/gerar_certificados', methods=['POST'])
@login_required
def gerar_certificados():
    ids = register_person(request.form['csv_table'])

    # If there is ids, create a zip file
    if ids.__len__() > 0:
        s = io.BytesIO()
        zf = zipfile.ZipFile(s, "w")
        zipfilenames = []

        for id_ in ids:
            user = Users.query.filter_by(id=id_).first()
            zipfilenames.append(clean_string(user.event))
            pdf = make_pdf_of_user(user)

            # Generate the file
            file = pdf.output(dest='S').encode('latin-1')
            zf.writestr(clean_string(user.event) + "/Certificado " + clean_string(user.name) + ".pdf", file)

        # Close the zipfile
        zf.close()

        response = make_response(s.getvalue())
        response.headers.set('Content-Disposition', 'attachment',
                             filename='Certificados - ' + '; '.join(list(set(zipfilenames))) + '.zip')
        response.headers.set('Content-Type', 'application/x-zip-compressed')
        return response


@app.route('/gerar_certificado_individual/<int:id>', methods=['GET'])
@login_required
def gerar_certificado_individual(id):
    user = Users.query.filter_by(id=id).first()
    try:
        pdf = make_pdf_of_user(user)
        file = pdf.output(dest='S').encode('latin-1')

        response = make_response(file)
        response.headers.set(
            'Content-Disposition',
            'attachment',
            filename='Certificado - ' + clean_string(user.event) + ' - ' + clean_string(user.name) + '.pdf')
        response.headers.set('Content-Type', 'application/pdf')
        return response
    except:
        return home


@login_required
def make_pdf_of_user(user):
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


@app.route('/validar', methods=['POST', 'GET'])
def validate_document():
    if request.method == 'POST':
        hash_to_be_checked = request.form["hash"]

        if hash_to_be_checked:
            users = Users.query.all()
            hashs_certificate = [
                hashlib.sha1(bytes("Certificate " + user.name + user.event + user.hours + str(user.host),
                                   'utf-8')).hexdigest() for user in users]
            if hash_to_be_checked in hashs_certificate:
                message = True
            else:
                message = False

            return render_template('validation.html', message=message, success=True)
        else:
            return render_template('validation.html')
    else:
        return render_template('validation.html')


@app.route('/remover', methods=["POST"])
@login_required
def remove_checked():
    ids = request.form.getlist('check')

    for id_ in ids:
        try:
            user = Users.query.filter_by(id=id_).first()
            db.session.delete(user)
            db.session.commit()
        except SQLAlchemyError as e:
            print(str(e))
            db.session.rollback()

    return redirect('/gerenciar_participantes')


@app.route('/gerenciar_participantes', methods=["GET"])
@login_required
def manage_participants():
    users = Users.query.all()
    val = pd.read_sql_query("SELECT * from users", db.get_engine(app, 'users'))
    table = val.to_html()
    return render_template("manage_participants.html", users=users, table=table)


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


def register_person(csv_table):
    data = io.StringIO(csv_table)
    reader = csv.reader(data, delimiter=',')
    next(reader)

    ids = []
    for row in reader:
        temp_id, name, username, pronoun, event, date, hours, host, background = row
        new_subscription = Users(name=name,
                                 username=username,
                                 pronoun=pronoun.lower(),
                                 event=event,
                                 date=date,
                                 hours=hours,
                                 host=tf_host(host),
                                 background=background)

        potential_user = Users.query.filter_by(name=new_subscription.name,
                                               username=new_subscription.username,
                                               pronoun=new_subscription.pronoun,
                                               event=new_subscription.event,
                                               date=new_subscription.date,
                                               hours=new_subscription.hours,
                                               host=new_subscription.host,
                                               background=new_subscription.background).first()

        if potential_user is None:
            try:
                db.session.add(new_subscription)
                db.session.commit()
                ids.append(new_subscription.id)
            except SQLAlchemyError as e:
                print(str(e))
                db.session.rollback()
        else:
            ids.append(potential_user.id)
    return ids


def check_hour(hour):
    try:
        float(hour)
    except ValueError:
        return False
    return True


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


if __name__ == '__main__':
    app.run()
