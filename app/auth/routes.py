# app/auth/routes.py
from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user
from urllib.parse import urlparse, urljoin  # Исправленный импорт
from app import db
from app.auth import bp
from app.forms import LoginForm, RegistrationForm
from app.models import User

def is_safe_url(target):
    """Проверка безопасности URL для перенаправления после входа"""
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and \
           ref_url.netloc == test_url.netloc

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Неверный email или пароль')
            return redirect(url_for('auth.login'))
        
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        
        if not next_page or url_parse(next_page).netloc != '': # используем старую проверку или is_safe_url
             if user.role == 'patient':
                 next_page = url_for('patient.dashboard')
             elif user.role == 'doctor':
                 next_page = url_for('doctor.dashboard')
             elif user.role == 'admin':
                 next_page = url_for('admin.dashboard')
             else:
                 next_page = url_for('main.index')
                 
        return redirect(next_page)
    
    return render_template('auth/login.html', title='Вход', form=form)

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        # Согласно ТЗ 1.10.1: при регистрации роль по умолчанию 'patient'
        user = User(username=form.username.data, email=form.email.data, phone=form.phone.data, role='patient')
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Поздравляем, вы зарегистрированы!')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html', title='Регистрация', form=form)

@bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('main.index'))