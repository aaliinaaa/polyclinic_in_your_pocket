# app/admin/routes.py
from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.admin import bp
from app.utils import role_required, log_action
from app.models import User, ScheduleSlot, Appointment, ActionLog, db
from app.forms import DoctorForm
import calendar
from datetime import datetime, timedelta

@bp.route('/dashboard')
@login_required
@role_required('admin')
def dashboard():
    doctors_count = User.query.filter_by(role='doctor').count()
    patients_count = User.query.filter_by(role='patient').count()
    logs_count = ActionLog.query.count()
    return render_template('admin/dashboard.html', 
                           title='Панель администратора',
                           doctors_count=doctors_count,
                           patients_count=patients_count,
                           logs_count=logs_count)

@bp.route('/doctors')
@login_required
@role_required('admin')
def manage_doctors():
    doctors = User.query.filter_by(role='doctor').order_by(User.username).all()
    return render_template('admin/manage_doctors.html', title='Управление врачами', doctors=doctors)

@bp.route('/doctors/add', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def add_doctor():
    form = DoctorForm()
    if form.validate_on_submit():
        doctor = User(
            username=form.username.data, # type: ignore
            email=form.email.data, # type: ignore
            phone=form.phone.data, # type: ignore
            role='doctor', # type: ignore
            specialty=form.specialty.data, # type: ignore
            office_number=form.office_number.data # type: ignore
        )
        doctor.set_password(form.password.data)
        db.session.add(doctor)
        db.session.commit()
        log_action('ADD_DOCTOR', f'Админ {current_user.username} добавил врача {doctor.username}')
        flash('Врач успешно добавлен.')
        return redirect(url_for('admin.manage_doctors'))
    return render_template('admin/edit_doctor.html', title='Добавить врача', form=form, doctor=None)

@bp.route('/doctors/<int:doctor_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def edit_doctor(doctor_id):
    doctor = User.query.get_or_404(doctor_id)
    if doctor.role != 'doctor':
        flash('Этот пользователь не является врачом.')
        return redirect(url_for('admin.manage_doctors'))

    form = DoctorForm(obj=doctor)
    if form.validate_on_submit():
        # Проверка email на уникальность (исключая текущего врача)
        if User.query.filter(User.email == form.email.data, User.id != doctor.id).first():
            flash('Этот email уже используется.')
            return render_template('admin/edit_doctor.html', title='Редактировать врача', form=form, doctor=doctor)
            
        doctor.username = form.username.data
        doctor.email = form.email.data
        doctor.phone = form.phone.data
        doctor.specialty = form.specialty.data
        doctor.office_number = form.office_number.data
        if form.password.data:
            doctor.set_password(form.password.data)
            
        db.session.commit()
        log_action('EDIT_DOCTOR', f'Админ {current_user.username} изменил данные врача {doctor.username}')
        flash('Данные врача обновлены.')
        return redirect(url_for('admin.manage_doctors'))
    return render_template('admin/edit_doctor.html', title='Редактировать врача', form=form, doctor=doctor)

@bp.route('/doctors/<int:doctor_id>/delete', methods=['POST'])
@login_required
@role_required('admin')
def delete_doctor(doctor_id):
    doctor = User.query.get_or_404(doctor_id)
    if doctor.role != 'doctor':
        flash('Нельзя удалить не-врача.')
        return redirect(url_for('admin.manage_doctors'))
        
    # Проверка на наличие записей или расписания
    has_appointments = Appointment.query.filter_by(doctor_id=doctor.id).first()
    has_slots = ScheduleSlot.query.filter_by(doctor_id=doctor.id).first()
    
    if has_appointments or has_slots:
        flash('Нельзя удалить врача, у которого есть записи или расписание. Сначала очистите его данные.')
        return redirect(url_for('admin.manage_doctors'))
        
    db.session.delete(doctor)
    db.session.commit()
    log_action('DELETE_DOCTOR', f'Админ {current_user.username} удалил врача {doctor.username}')
    flash('Врач удален.')
    return redirect(url_for('admin.manage_doctors'))

@bp.route('/schedule/<int:doctor_id>')
@login_required
@role_required('admin')
def manage_schedule(doctor_id):
    doctor = User.query.get_or_404(doctor_id)
    if doctor.role != 'doctor':
        flash('Выберите врача для управления расписанием.')
        return redirect(url_for('admin.manage_doctors'))
        
    slots = ScheduleSlot.query.filter_by(doctor_id=doctor.id).order_by(ScheduleSlot.start_time).all()
    return render_template('admin/manage_schedule.html', title=f'Расписание: {doctor.username}', doctor=doctor, slots=slots)

@bp.route('/slot/add', methods=['POST'])
@login_required
@role_required('admin')
def add_slot():
    doctor_id = request.form.get('doctor_id', type=int)
    start_time_str = request.form.get('start_time')
    
    if not doctor_id or not start_time_str:
        flash('Заполните все поля.')
        return redirect(url_for('admin.manage_doctors'))
        
    try:
        start_time = datetime.strptime(start_time_str, '%Y-%m-%dT%H:%M')
    except ValueError:
        flash('Неверный формат даты/времени.')
        return redirect(url_for('admin.manage_schedule', doctor_id=doctor_id))
        
    end_time = start_time + timedelta(minutes=30)
    
    # Проверка пересечений
    overlap = ScheduleSlot.query.filter(
        ScheduleSlot.doctor_id == doctor_id,
        ScheduleSlot.start_time < end_time,
        ScheduleSlot.end_time > start_time
    ).first()
    
    if overlap:
        flash('Этот временной слот пересекается с существующим.')
        return redirect(url_for('admin.manage_schedule', doctor_id=doctor_id))
        
    slot = ScheduleSlot(doctor_id=doctor_id, start_time=start_time, end_time=end_time, is_available=True) # type: ignore
    db.session.add(slot)
    db.session.commit()
    
    log_action('ADD_SLOT', f'Админ {current_user.username} добавил слот для врача {doctor_id}')
    flash('Слот добавлен.')
    return redirect(url_for('admin.manage_schedule', doctor_id=doctor_id))

@bp.route('/slot/<int:slot_id>/delete', methods=['POST'])
@login_required
@role_required('admin')
def delete_slot(slot_id):
    slot = ScheduleSlot.query.get_or_404(slot_id)
    
    if not slot.is_available:
        flash('Нельзя удалить слот, на который уже есть запись. Сначала отмените запись.')
        return redirect(url_for('admin.manage_schedule', doctor_id=slot.doctor_id))
        
    db.session.delete(slot)
    db.session.commit()
    log_action('DELETE_SLOT', f'Админ {current_user.username} удалил слот {slot.start_time}')
    flash('Слот удален.')
    return redirect(url_for('admin.manage_schedule', doctor_id=slot.doctor_id))

@bp.route('/logs')
@login_required
@role_required('admin')
def view_logs():
    # Последние 100 записей
    logs = ActionLog.query.order_by(ActionLog.timestamp.desc()).limit(100).all()
    return render_template('admin/logs.html', title='Журнал действий', logs=logs)

@bp.route('/schedule/<int:doctor_id>/generate', methods=['POST'])
@login_required
@role_required('admin')
def generate_schedule_slots(doctor_id):
    doctor = User.query.get_or_404(doctor_id)
    if doctor.role != 'doctor':
        flash('Выберите врача для управления расписанием.')
        return redirect(url_for('admin.manage_doctors'))

    start_time_str = request.form.get('start_time')
    end_time_str = request.form.get('end_time')
    duration_min = request.form.get('duration', type=int)
    month_str = request.form.get('month')
    selected_days = request.form.getlist('days')

    # Валидация
    if not start_time_str or not end_time_str or not duration_min or not month_str:
        flash('Заполните все поля.')
        return redirect(url_for('admin.manage_schedule', doctor_id=doctor_id))
    if not selected_days:
        flash('Выберите хотя бы один день недели.')
        return redirect(url_for('admin.manage_schedule', doctor_id=doctor_id))

    try:
        year, month = map(int, month_str.split('-'))
        start_h, start_m = map(int, start_time_str.split(':'))
        end_h, end_m = map(int, end_time_str.split(':'))
    except Exception:
        flash('Неверный формат данных.')
        return redirect(url_for('admin.manage_schedule', doctor_id=doctor_id))

    if duration_min <= 0:
        flash('Длительность приема должна быть больше 0.')
        return redirect(url_for('admin.manage_schedule', doctor_id=doctor_id))
        
    if datetime(year, month, 1, start_h, start_m) >= datetime(year, month, 1, end_h, end_m):
        flash('Время начала должно быть раньше времени окончания.')
        return redirect(url_for('admin.manage_schedule', doctor_id=doctor_id))

    work_days = [int(d) for d in selected_days]
    _, num_days = calendar.monthrange(year, month)
    created_count = 0
    skipped_count = 0

    # Генерация по дням месяца
    for day_num in range(1, num_days + 1):
        day_date = datetime(year, month, day_num)
        if day_date.weekday() in work_days:
            current_time = day_date.replace(hour=start_h, minute=start_m)
            day_end = day_date.replace(hour=end_h, minute=end_m)

            while current_time + timedelta(minutes=duration_min) <= day_end:
                slot_start = current_time
                slot_end = current_time + timedelta(minutes=duration_min)

                # Проверка на пересечение с существующими слотами
                overlap = ScheduleSlot.query.filter(
                    ScheduleSlot.doctor_id == doctor_id,
                    ScheduleSlot.start_time < slot_end,
                    ScheduleSlot.end_time > slot_start
                ).first()

                if not overlap:
                    db.session.add(ScheduleSlot(
                        doctor_id=doctor_id, 
                        start_time=slot_start, 
                        end_time=slot_end, 
                        is_available=True
                    ))
                    created_count += 1
                else:
                    skipped_count += 1

                current_time += timedelta(minutes=duration_min)

    db.session.commit()
    log_action('GENERATE_SCHEDULE', f'Админ {current_user.username} сгенерировал {created_count} слотов для врача {doctor.username} на {month_str}')
    flash(f'✅ Успешно создано {created_count} слотов. Пропущено {skipped_count} из-за пересечений.')
    return redirect(url_for('admin.manage_schedule', doctor_id=doctor_id))