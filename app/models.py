from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app import db, login_manager

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    phone = db.Column(db.String(20), index=True, unique=True)
    password_hash = db.Column(db.String(256))
    role = db.Column(db.String(20), index=True, default='patient')
    
    # Специфичные поля
    specialty = db.Column(db.String(100), nullable=True) # Для врача
    office_number = db.Column(db.String(10), nullable=True) # Для врача
    oms_number = db.Column(db.String(20), nullable=True) # Для пациента
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Связи
    appointments_as_patient = db.relationship('Appointment', foreign_keys='Appointment.patient_id', backref='patient', lazy='dynamic')
    appointments_as_doctor = db.relationship('Appointment', foreign_keys='Appointment.doctor_id', backref='doctor', lazy='dynamic')
    schedule_slots = db.relationship('ScheduleSlot', backref='doctor', lazy='dynamic')
    action_logs = db.relationship('ActionLog', backref='user', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'

class ScheduleSlot(db.Model):
    """Временной слот в расписании врача"""
    __tablename__ = 'schedule_slots'

    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False, index=True)
    end_time = db.Column(db.DateTime, nullable=False)
    is_available = db.Column(db.Boolean, default=True) # True - свободно, False - занято/отменено
    
    # Связь с записью (если слот занят)
    appointment = db.relationship('Appointment', uselist=False, backref='slot')

    def __repr__(self):
        return f'<Slot {self.start_time} for Doctor {self.doctor_id}>'

class Appointment(db.Model):
    """Запись на прием"""
    __tablename__ = 'appointments'

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    slot_id = db.Column(db.Integer, db.ForeignKey('schedule_slots.id'), nullable=False)
    
    status = db.Column(db.String(20), default='scheduled') # scheduled, completed, cancelled
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Данные, которые врач заполнит позже (из медкарты)
    diagnosis = db.Column(db.Text, nullable=True)
    prescription = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f'<Appointment {self.id} Patient:{self.patient_id} Doctor:{self.doctor_id}>'

class ActionLog(db.Model):
    """Журнал действий (Требование 1.4.10)"""
    __tablename__ = 'action_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True) # Может быть NULL для системных действий
    action_type = db.Column(db.String(50), nullable=False) # e.g., 'LOGIN', 'BOOK_APPOINTMENT', 'CANCEL_APPOINTMENT'
    description = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    ip_address = db.Column(db.String(45), nullable=True)

    def __repr__(self):
        return f'<Log {self.action_type} by User {self.user_id}>'