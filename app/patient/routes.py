# app/patient/routes.py
import calendar
from flask import render_template, redirect, url_for, flash, request # pyright: ignore[reportMissingImports]
from flask_login import login_required, current_user # pyright: ignore[reportMissingImports]
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
    """Просмотр расписания врача в виде календаря (Требование 1.10.6)"""
    doctor = User.query.get_or_404(doctor_id)
    if doctor.role != 'doctor':
        flash('Этот пользователь не является врачом.')
        return redirect(url_for('patient.list_doctors'))
    
    # Получаем год, месяц и день из запроса
    year = request.args.get('year', type=int)
    month = request.args.get('month', type=int)
    selected_day = request.args.get('day', type=int)
    
    now = datetime.now()
    if not year or not month:
        year = now.year
        month = now.month
        
    # Создаем объект календаря
    cal = calendar.Calendar(firstweekday=0) # Понедельник - первый день
    month_days = cal.monthdayscalendar(year, month)
    
    # Диапазон дат для запроса к БД (весь месяц)
    start_date = datetime(year, month, 1)
    if month == 12:
        end_date = datetime(year + 1, 1, 1) - timedelta(seconds=1)
    else:
        end_date = datetime(year, month + 1, 1) - timedelta(seconds=1)
        
    # Загружаем все слоты врача за выбранный месяц
    all_slots = ScheduleSlot.query.filter(
        ScheduleSlot.doctor_id == doctor_id,
        ScheduleSlot.start_time >= start_date,
        ScheduleSlot.start_time <= end_date
    ).order_by(ScheduleSlot.start_time).all()
    
    # Группируем слоты по дням для отображения в календаре
    slots_by_day = {}
    for slot in all_slots:
        day_key = slot.start_time.day
        if day_key not in slots_by_day:
            slots_by_day[day_key] = []
        slots_by_day[day_key].append(slot)

    # Подсчитываем количество свободных слотов для каждого дня
    free_slots_count = {}
    for day, slots in slots_by_day.items():
        free_slots_count[day] = sum(1 for s in slots if s.is_available)

    # Если выбран конкретный день, готовим список слотов для отображения (для совместимости, если нужно)
    selected_slots = []
    if selected_day and selected_day in slots_by_day:
        selected_slots = [s for s in slots_by_day[selected_day] if s.start_time > now]

    # Названия месяцев
    month_names = [
        "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
        "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
    ]
    
    # Ссылки для переключения месяцев
    prev_month = month - 1
    prev_year = year
    if prev_month < 1:
        prev_month = 12
        prev_year -= 1
        
    next_month = month + 1
    next_year = year
    if next_month > 12:
        next_month = 1
        next_year += 1

    return render_template('patient/schedule.html', 
                           title=f'Расписание: {doctor.username}', 
                           doctor=doctor,
                           month_days=month_days,
                           year=year,
                           month=month,
                           month_name=month_names[month-1],
                           free_slots_count=free_slots_count,
                           slots_by_day=slots_by_day, # <-- Добавлено!
                           selected_day=selected_day,
                           selected_slots=selected_slots,
                           prev_year=prev_year, prev_month=prev_month,
                           next_year=next_year, next_month=next_month)

                           
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
    """Просмотр медицинской карты (история приемов)"""
    # Используем join, чтобы иметь доступ к полям таблицы ScheduleSlot для сортировки
    appointments = Appointment.query\
        .join(ScheduleSlot, Appointment.slot_id == ScheduleSlot.id)\
        .filter(Appointment.patient_id == current_user.id)\
        .order_by(ScheduleSlot.start_time.desc())\
        .all()
    
    return render_template('patient/medical_card.html', title='Медицинская карта', appointments=appointments)