from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError
from models import User

class LoginForm(FlaskForm):
    username = StringField('Nume utilizator', validators=[DataRequired()])
    password = PasswordField('Parolă', validators=[DataRequired()])
    submit = SubmitField('Autentificare')

class RegistrationForm(FlaskForm):
    username = StringField('Nume utilizator', validators=[
        DataRequired(message='Acest câmp este obligatoriu'),
        Length(min=3, max=20, message='Numele de utilizator trebuie să aibă între 3 și 20 de caractere')
    ])
    email = StringField('Email', validators=[
        DataRequired(message='Acest câmp este obligatoriu'),
        Email(message='Introdu o adresă de email validă')
    ])
    password = PasswordField('Parolă', validators=[
        DataRequired(message='Acest câmp este obligatoriu'),
        Length(min=6, message='Parola trebuie să aibă cel puțin 6 caractere')
    ])
    password2 = PasswordField('Confirmă parola', validators=[
        DataRequired(message='Acest câmp este obligatoriu'),
        EqualTo('password', message='Parolele nu coincid')
    ])
    submit = SubmitField('Înregistrare')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Acest nume de utilizator este deja folosit. Te rugăm să alegi altul.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Această adresă de email este deja înregistrată. Te rugăm să folosești alta.')

class ProfileForm(FlaskForm):
    clasa = SelectField('Clasa', choices=[
        ('9', 'Clasa a 9-a'),
        ('10', 'Clasa a 10-a'),
        ('11-12', 'Clasele 11-12')
    ]) 