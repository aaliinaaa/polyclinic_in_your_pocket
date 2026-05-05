import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from app import create_app, db
from app.models import User, ScheduleSlot, Appointment, ActionLog  # <-- Импорт моделей

@pytest.fixture(scope='module')
def app():
    """Создает Flask-приложение для тестирования с тестовой БД в памяти"""
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['SECRET_KEY'] = 'test-secret-key'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    """Тестовый клиент для отправки HTTP-запросов"""
    return app.test_client()

@pytest.fixture(autouse=True)
def clean_db(app):
    yield
    with app.app_context():
        try:
            ActionLog.query.delete()
            Appointment.query.delete()
            ScheduleSlot.query.delete()
            User.query.delete()
            db.session.commit()
        except Exception:
            db.session.rollback()  