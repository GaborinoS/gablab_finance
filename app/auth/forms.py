from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError, Length
from app.models import User
import os

# Master password for registration - in a real application, this should be stored securely
# For now, we'll get it from an environment variable or use a default for development
MASTER_PASSWORD = os.environ.get('REGISTRATION_MASTER_PASSWORD', 'gablab2024')

class LoginForm(FlaskForm):
    username = StringField('Benutzername', validators=[DataRequired()])
    password = PasswordField('Passwort', validators=[DataRequired()])
    remember_me = BooleanField('Angemeldet bleiben')
    submit = SubmitField('Einloggen')

class RegistrationForm(FlaskForm):
    username = StringField('Benutzername', validators=[DataRequired(), Length(min=3, max=64)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Passwort', validators=[DataRequired(), Length(min=8)])
    password2 = PasswordField('Passwort wiederholen', validators=[DataRequired(), EqualTo('password')])
    master_password = PasswordField('Master-Passwort', validators=[DataRequired()])
    submit = SubmitField('Registrieren')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('Bitte verwenden Sie einen anderen Benutzernamen.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('Bitte verwenden Sie eine andere Email-Adresse.')
            
    def validate_master_password(self, master_password):
        if master_password.data != MASTER_PASSWORD:
            raise ValidationError('Ungültiges Master-Passwort. Bitte wenden Sie sich an den Administrator.')