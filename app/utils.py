# app/utils.py
from functools import wraps
from flask import flash, redirect, url_for, request
from flask_login import current_user
from app.models import ActionLog
from app import db

def role_required(role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))
            if current_user.role != role:
                flash('У вас нет доступа к этой странице.')
                return redirect(url_for('main.index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def log_action(action_type, description):
    """Записывает действие в журнал"""
    log = ActionLog(
        user_id=current_user.id if current_user.is_authenticated else None,
        action_type=action_type,
        description=description,
        ip_address=request.remote_addr
    )
    db.session.add(log)
    db.session.commit()