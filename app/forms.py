# app/forms.py
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError
from app.models import User

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    remember_me = BooleanField('Запомнить меня')
    submit = SubmitField('Войти')

class RegistrationForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone = StringField('Телефон', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    password2 = PasswordField('Повторите пароль', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Зарегистрироваться')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('Это имя пользователя уже занято. Используйте другое.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('Этот email уже зарегистрирован. Попробуйте войти.')
    
    def validate_phone(self, phone):
        user = User.query.filter_by(phone=phone.data).first()
        if user is not None:
            raise ValidationError('Этот телефон уже зарегистрирован.')
        
    def validate_username(self, username):
        # 1. Проверка на дубликаты
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('Такое ФИО уже зарегистрировано.')
            
        # 2. Проверка прикрепления к поликлинике (Требование 1.10.1)
        from app.models import AttachedPatient
        attached = AttachedPatient.query.filter_by(full_name=username.data).first()
        if not attached:
            raise ValidationError('Вы не прикреплены к данной поликлинике. Обратитесь в регистратуру или через Госуслуги.')
        
class DoctorForm(FlaskForm):
    username = StringField('ФИО', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone = StringField('Телефон', validators=[DataRequired()])
    specialty = StringField('Специальность', validators=[DataRequired()])
    office_number = StringField('Номер кабинета', validators=[DataRequired()])
    password = PasswordField('Новый пароль (оставьте пустым, чтобы не менять)')
    submit = SubmitField('Сохранить')

    # def validate_email(self, email):
    #     user = User.query.filter_by(email=email.data).first()
    #     if user is not None:
    #         raise ValidationError('Этот email уже зарегистрирован.')        