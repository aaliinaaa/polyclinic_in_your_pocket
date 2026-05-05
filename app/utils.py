# app/utils.py
from functools import wraps
from flask import flash, redirect, url_for, request
from flask_login import current_user
from app.models import ActionLog, Appointment, ScheduleSlot
from app import db
from datetime import datetime, timedelta

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

def check_appointment_notifications(user):
    """Проверяет ближайшие приёмы и выводит уведомления (требование 1.4.8)"""
    if not user or user.role != 'patient':
        return
        
    now = datetime.now()
    # Ищем запланированные приёмы в ближайшие 24 часа
    upcoming = Appointment.query.join(ScheduleSlot, Appointment.slot_id == ScheduleSlot.id)\
        .filter(
            Appointment.patient_id == user.id,
            Appointment.status == 'scheduled',
            ScheduleSlot.start_time > now,
            ScheduleSlot.start_time <= now + timedelta(hours=24)
        ).all()

    for appt in upcoming:
        diff_hours = (appt.slot.start_time - now).total_seconds() / 3600
        
        # Уведомление за ~24 часа (окно ±1 час, чтобы не пропустить из-за времени входа)
        if 23 <= diff_hours <= 25:
            flash(f"Напоминание: завтра в {appt.slot.start_time.strftime('%H:%M')} у вас приём у врача {appt.doctor.username}.", 'info')
            
        # Уведомление за ~2 часа
        elif 1.5 <= diff_hours <= 2.15:
            flash(f"Внимание: через 2 часа у вас приём у врача {appt.doctor.username}.", 'warning')