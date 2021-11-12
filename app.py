import cryptography
import csv
import hashlib
import io
import json
import os
import pandas as pd
import zipfile
import yaml
from datetime import datetime
from flask import Flask, render_template, request, make_response, redirect, url_for
from flask_bootstrap import Bootstrap
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from pandas_schema import Schema, Column
from pandas_schema.validation import CustomElementValidation
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy_utils import StringEncryptedType
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from wtforms import StringField, PasswordField
from wtforms.validators import InputRequired, Length
from functions import check_columns, check_role, check_hour, check_date, check_pronoun, clean_string, \
    make_pdf_of_user

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
roles = app.config["ROLES"]


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
    confirmation_password = PasswordField('Confirme sua nova senha',
                                          validators=[InputRequired(), Length(min=6, max=20)])


class WMBUser(UserMixin, db.Model):
    __tablename__ = 'wmb_admin'
    __bind_key__ = 'wmb_admin'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True)
    email = db.Column(db.String(50), unique=True)
    password = db.Column(db.String(80))
    users = db.relationship("Users")


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
    date_start = db.Column(db.String(10), default=datetime.utcnow().strftime('%d/%m/%Y'), nullable=False)
    date_end = db.Column(db.String(10), default=datetime.utcnow().strftime('%d/%m/%Y'), nullable=True)
    hours = db.Column(db.String(5), nullable=False)
    role = db.Column(StringEncryptedType(db.String(), key), nullable=False)
    background = db.Column(StringEncryptedType(db.String(500), key), nullable=False)
    wmb_user = db.Column(db.String(20), db.ForeignKey('wmb_admin.username'))

    def __repr__(self):
        return '<User %r>' % self.username


@app.route('/login', methods=["GET", "POST"])
def login():
    form = LoginForm()

    if form.validate_on_submit():
        user = WMBUser.query.filter_by(username=form.username.data).first()
        if user:
            if check_password_hash(user.password, form.password.data):
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
            date_start_validation = [
                CustomElementValidation(lambda d: check_date(d), 'valores inválidos para a coluna "date_start"')]
            date_end_validation = [
                CustomElementValidation(lambda d: check_date(d), 'valores inválidos para a coluna "date_end"')]
            hour_validation = [
                CustomElementValidation(lambda d: check_hour(d), 'valores inválidos para a coluna "hours"')]
            role_validation = [
                CustomElementValidation(lambda d: check_role(d, roles),
                                        'valores inválidos para a coluna "role". Valores válidos são: ' + "/".join(
                                            roles))]

            schema = Schema([
                Column("name", allow_empty=False),
                Column("username", allow_empty=True),
                Column("pronoun", pronoun_validation, allow_empty=False),
                Column("event", allow_empty=False),
                Column("date_start", date_start_validation, allow_empty=False),
                Column("date_end", date_end_validation, allow_empty=True),
                Column("hours", hour_validation, allow_empty=False),
                Column("role", role_validation, allow_empty=False),
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
        users = [user for user in Users.query.all() if user.id in ids]
        s = io.BytesIO()
        zf = zipfile.ZipFile(s, "w")
        zipfilenames = []

        for user in users:
            zipfilenames.append(clean_string(user.event))
            pdf = make_pdf_of_user(user, app)

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


@app.route('/gerar_certificado_individual/<int:id>', methods=['GET', 'POST'])
@login_required
def gerar_certificado_individual(id):
    user = Users.query.get(id)
    try:
        pdf = make_pdf_of_user(user, app)
        file = pdf.output(dest='S').encode('latin-1')

        response = make_response(file)
        response.headers.set(
            'Content-Disposition',
            'attachment',
            filename='Certificado - ' + clean_string(user.event) + ' - ' + clean_string(user.name) + '.pdf')
        response.headers.set('Content-Type', 'application/pdf')
        return response
    except:
        return redirect(url_for("home"))


@app.route('/validar', methods=['POST', 'GET'])
def validate_document():
    if request.method == 'POST':
        hash_to_be_checked = request.form["hash"]

        if hash_to_be_checked:
            users = Users.query.all()
            hashs_certificate = [
                hashlib.sha1(bytes("Certificate " + user.name + user.event + user.hours + str(user.role),
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


@app.route('/calendar', methods=["POST", "GET"])
def calendar():
    return render_template('calendar.html')



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

    table_obj = []
    for user in users:
        table_obj.append({"id": user.id,
                          "name": user.name,
                          "username": user.username,
                          "pronoun": user.pronoun,
                          "event": user.event,
                          "date_start": user.date_start,
                          "date_end": user.date_end,
                          "hours": user.hours,
                          "role": user.role,
                          "background": user.background})

    # val = pd.read_sql_query("SELECT * from users", db.get_engine(app, 'users'))
    table_json = json.dumps(table_obj)
    val = pd.read_json(table_json)
    table = val.to_html()
    return render_template("manage_participants.html", users=users, table=table)


def register_person(csv_table):
    data = io.StringIO(csv_table)
    reader = csv.reader(data, delimiter=',')
    next(reader)

    ids = []
    for row in reader:
        temp_id, name, username, pronoun, event, date_start, date_end, hours, role, background = row
        new_subscription = Users(name=name,
                                 username=username,
                                 pronoun=pronoun.lower(),
                                 event=event,
                                 date_start=date_start,
                                 date_end=date_end,
                                 hours=hours,
                                 role=role.lower(),
                                 background=background,
                                 wmb_user=WMBUser.query.get(current_user.id).username)

        potential_user = Users.query.filter_by(name=new_subscription.name,
                                               username=new_subscription.username,
                                               pronoun=new_subscription.pronoun,
                                               event=new_subscription.event,
                                               date_start=new_subscription.date_start,
                                               date_end=new_subscription.date_end,
                                               hours=new_subscription.hours,
                                               role=new_subscription.role,
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


@app.route('/update_participant', methods=["POST"])
@login_required
def update_participant():
    form = request.form
    user = Users.query.get(form["user_id"])
    user.name = form["edit_name"]
    user.username = form["edit_username"]
    user.pronoun = form["edit_pronoun"]
    user.event = form["edit_event"]
    user.date_start = format(datetime.strptime(form["edit_date_start"], "%Y-%m-%d"), "%d/%m/%Y")
    user.date_end = format(datetime.strptime(form["edit_date_end"], "%Y-%m-%d"), "%d/%m/%Y") if form["edit_date_end"] else None
    user.hours = form["edit_hours"]
    user.role = form["edit_role"]
    user.wmb_user = WMBUser.query.get(current_user.id).username

    try:
        db.session.commit()
    except SQLAlchemyError as e:
        print(str(e))
        db.session.rollback()
    return redirect(url_for('manage_participants'))


if __name__ == '__main__':
    app.run()
