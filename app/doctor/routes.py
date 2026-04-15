# app/doctor/routes.py
import calendar
from flask import render_template, redirect, url_for, flash, request # type: ignore
from flask_login import login_required, current_user # type: ignore
from app.doctor import bp
from app.utils import role_required, log_action
from app.models import User, ScheduleSlot, Appointment, db
from datetime import datetime, timedelta

@bp.route('/dashboard')
@login_required
@role_required('doctor')
def dashboard():
    """Главная страница врача: записи на сегодня"""
    appointments = current_user.get_today_appointments()
    return render_template('doctor/dashboard.html', title='Кабинет врача', appointments=appointments)

@bp.route('/schedule')
@login_required
@role_required('doctor')
def schedule():
    """Просмотр расписания врача в виде календаря на месяц"""
    
    # Получаем год и месяц из запроса, по умолчанию - текущие
    year = request.args.get('year', type=int)
    month = request.args.get('month', type=int)
    
    now = datetime.now()
    if not year or not month:
        year = now.year
        month = now.month
    
    # Создаем объект календаря
    cal = calendar.Calendar(firstweekday=0) # Понедельник - первый день
    month_days = cal.monthdayscalendar(year, month)
    
    # Диапазон дат для запроса к БД (начало и конец месяца)
    start_date = datetime(year, month, 1)
    if month == 12:
        end_date = datetime(year + 1, 1, 1) - timedelta(seconds=1)
    else:
        end_date = datetime(year, month + 1, 1) - timedelta(seconds=1)
        
    # Загружаем все слоты врача за выбранный месяц одним запросом
    slots = ScheduleSlot.query.filter(
        ScheduleSlot.doctor_id == current_user.id,
        ScheduleSlot.start_time >= start_date,
        ScheduleSlot.start_time <= end_date
    ).order_by(ScheduleSlot.start_time).all()
    
    # Группируем слоты по дням для удобного доступа в шаблоне
    # Ключ: дата (datetime.date), Значение: список слотов
    slots_by_day = {}
    for slot in slots:
        day_key = slot.start_time.date()
        if day_key not in slots_by_day:
            slots_by_day[day_key] = []
        slots_by_day[day_key].append(slot)
        
    # Названия месяцев и дней недели для отображения
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

    return render_template('doctor/schedule.html', 
                           title='Мое расписание', 
                           month_days=month_days,
                           year=year,
                           month=month,
                           month_name=month_names[month-1],
                           slots_by_day=slots_by_day,
                           prev_year=prev_year, prev_month=prev_month,
                           next_year=next_year, next_month=next_month)


@bp.route('/appointment/<int:appointment_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('doctor')
def edit_appointment(appointment_id):
    """Редактирование записи / Заполнение медкарты (Требование 1.10.4)"""
    appointment = Appointment.query.get_or_404(appointment_id)
    
    # Проверка прав: только врач, к которому запись, или админ может редактировать
    if appointment.doctor_id != current_user.id:
        flash('У вас нет прав для редактирования этой записи.')
        return redirect(url_for('doctor.dashboard'))

    if request.method == 'POST':
        diagnosis = request.form.get('diagnosis')
        prescription = request.form.get('prescription')
        status = request.form.get('status') # scheduled, completed, cancelled
        
        appointment.diagnosis = diagnosis
        appointment.prescription = prescription
        if status:
            appointment.status = status
            
        db.session.commit()
        
        log_action('EDIT_MEDICAL_CARD', f'Врач {current_user.username} обновил данные приема #{appointment.id}')
        flash('Данные сохранены.')
        return redirect(url_for('doctor.dashboard'))

    return render_template('doctor/edit_appointment.html', title='Прием пациента', appointment=appointment)

@bp.route('/cancel-slot/<int:slot_id>', methods=['POST'])
@login_required
@role_required('doctor')
def cancel_slot(slot_id):
    """Отмена слота врачом (освобождение времени)"""
    slot = ScheduleSlot.query.get_or_404(slot_id)
    
    if slot.doctor_id != current_user.id:
        flash('Ошибка доступа.')
        return redirect(url_for('doctor.schedule'))
        
    if not slot.is_available:
        flash('Нельзя удалить слот, на который уже есть запись. Сначала отмените запись.')
        return redirect(url_for('doctor.schedule'))
        
    # Просто удаляем слот или помечаем как недоступный? 
    # Для простоты пометим как недоступный или удалим. Давайте удалим.
    db.session.delete(slot)
    db.session.commit()
    
    log_action('CANCEL_SLOT', f'Врач {current_user.username} удалил слот {slot.start_time}')
    flash('Слот удален.')
    return redirect(url_for('doctor.schedule'))