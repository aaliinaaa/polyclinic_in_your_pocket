from datetime import datetime
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
    role = db.Column(db.String(20), index=True, default='patient') # 'patient', 'doctor', 'admin'
    
    # Специфичные поля для Врача (если роль doctor)
    specialty = db.Column(db.String(100), nullable=True) # Специальность
    office_number = db.Column(db.String(10), nullable=True) # Номер кабинета
    
    # Специфичные поля для Пациента (если роль patient)
    oms_number = db.Column(db.String(20), nullable=True) # Полис ОМС
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'