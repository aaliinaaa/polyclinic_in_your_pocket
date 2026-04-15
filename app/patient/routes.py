# app/patient/routes.py
from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.patient import bp
from app.utils import role_required, log_action
from app.models import User, ScheduleSlot, Appointment, db
from datetime import datetime, timedelta

@bp.route('/dashboard')
@login_required
@role_required('patient')
def dashboard():
    return render_template('patient/dashboard.html', title='Кабинет пациента')

@bp.route('/doctors')
@login_required
@role_required('patient')
def list_doctors():
    """Просмотр списка врачей (Требование 1.10.5)"""
    doctors = User.query.filter_by(role='doctor').all()
    return render_template('patient/doctors.html', title='Список врачей', doctors=doctors)

@bp.route('/doctors/<int:doctor_id>/schedule')
@login_required
@role_required('patient')
def view_schedule(doctor_id):
    """Просмотр расписания врача (Требование 1.10.6)"""
    doctor = User.query.get_or_404(doctor_id)
    if doctor.role != 'doctor':
        flash('Этот пользователь не является врачом.')
        return redirect(url_for('patient.list_doctors'))
    
    # Получаем слоты на ближайшие 7 дней
    today = datetime.now().date()
    next_week = today + timedelta(days=7)
    
    slots = ScheduleSlot.query.filter(
        ScheduleSlot.doctor_id == doctor_id,
        ScheduleSlot.start_time >= datetime.combine(today, datetime.min.time()),
        ScheduleSlot.start_time <= datetime.combine(next_week, datetime.max.time())
    ).order_by(ScheduleSlot.start_time).all()
    
    return render_template('patient/schedule.html', title=f'Расписание: {doctor.username}', doctor=doctor, slots=slots)

@bp.route('/book/<int:slot_id>', methods=['POST'])
@login_required
@role_required('patient')
def book_appointment(slot_id):
    """Запись на прием (Требование 1.10.7)"""
    slot = ScheduleSlot.query.get_or_404(slot_id)
    
    # Проверки
    if not slot.is_available:
        flash('Это время уже занято.')
        return redirect(url_for('patient.view_schedule', doctor_id=slot.doctor_id))
    
    if slot.start_time < datetime.now():
        flash('Нельзя записаться на прошедшее время.')
        return redirect(url_for('patient.view_schedule', doctor_id=slot.doctor_id))

    # Создание записи
    appointment = Appointment(
        patient_id=current_user.id,
        doctor_id=slot.doctor_id,
        slot_id=slot.id,
        status='scheduled'
    )
    
    # Занимаем слот
    slot.is_available = False
    
    db.session.add(appointment)
    db.session.commit()
    
    # Логирование
    log_action('BOOK_APPOINTMENT', f'Пациент {current_user.username} записался к врачу {slot.doctor.username} на {slot.start_time}')
    
    flash('Вы успешно записаны на прием!')
    return redirect(url_for('patient.my_appointments'))

@bp.route('/my-appointments')
@login_required
@role_required('patient')
def my_appointments():
    """Просмотр своих записей (Требование 1.10.8)"""
    appointments = Appointment.query.filter_by(patient_id=current_user.id).order_by(Appointment.created_at.desc()).all()
    return render_template('patient/my_appointments.html', title='Мои записи', appointments=appointments)

@bp.route('/cancel/<int:appointment_id>', methods=['POST'])
@login_required
@role_required('patient')
def cancel_appointment(appointment_id):
    """Отмена записи (Требование 1.10.9)"""
    appointment = Appointment.query.get_or_404(appointment_id)
    
    if appointment.patient_id != current_user.id:
        flash('У вас нет прав на отмену этой записи.')
        return redirect(url_for('patient.my_appointments'))
        
    # Проверка: отмена не позднее чем за 24 часа (упрощенно: просто нельзя отменить прошедшие)
    if appointment.slot.start_time < datetime.now():
        flash('Нельзя отменить прошедший или текущий прием.')
        return redirect(url_for('patient.my_appointments'))

    # Освобождаем слот
    slot = ScheduleSlot.query.get(appointment.slot_id)
    if slot:
        slot.is_available = True
        
    appointment.status = 'cancelled'
    db.session.commit()
    
    log_action('CANCEL_APPOINTMENT', f'Пациент {current_user.username} отменил запись к врачу {appointment.doctor.username}')
    
    flash('Запись отменена.')
    return redirect(url_for('patient.my_appointments'))

@bp.route('/medical-card')
@login_required
@role_required('patient')
def medical_card():
    """Просмотр медицинской карты (Требование 1.10.3)"""
    # В будущем здесь будет запрос к БД за историей болезни
    # Пока просто отображаем шаблон
    return render_template('patient/medical_card.html', title='Медицинская карта')