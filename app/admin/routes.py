# app/admin/routes.py
from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.admin import bp
from app.utils import role_required, log_action
from app.models import User, ScheduleSlot, Appointment, ActionLog, db
from app.forms import DoctorForm
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
            username=form.username.data,
            email=form.email.data,
            phone=form.phone.data,
            role='doctor',
            specialty=form.specialty.data,
            office_number=form.office_number.data
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
        
    slot = ScheduleSlot(doctor_id=doctor_id, start_time=start_time, end_time=end_time, is_available=True)
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