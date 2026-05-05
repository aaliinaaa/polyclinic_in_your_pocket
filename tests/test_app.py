import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, PropertyMock
from flask_login import login_user, logout_user
from app.models import User, ScheduleSlot, Appointment, ActionLog
from app import db

# 1. Тест: метод возбуждает исключение при нарушении уникальности
def test_duplicate_email_raises_exception(app):
    with app.app_context():
        u1 = User(username='User1', email='test@dup.com', phone='111-unique')
        u1.set_password('pass123')
        db.session.add(u1)
        db.session.commit()

        u2 = User(username='User2', email='test@dup.com', phone='222-unique') 
        u2.set_password('pass123')
        db.session.add(u2)

        # Ожидаем IntegrityError при дублировании email
        with pytest.raises(Exception):
            db.session.commit()
        db.session.rollback()  # Сброс после исключения

# 2. Тест: метод возвращает коллекцию (с изоляцией БД)
def test_get_doctors_returns_collection(app):
    with app.app_context():
        User.query.filter_by(role='doctor').delete()
        db.session.commit()
        
        d1 = User(username='Иванов', email='doc1@test.com', phone='101', role='doctor', specialty='Терапевт')
        d2 = User(username='Петров', email='doc2@test.com', phone='102', role='doctor', specialty='Хирург')
        db.session.add_all([d1, d2])
        db.session.commit()

        doctors = User.query.filter_by(role='doctor').all()
        assert isinstance(doctors, list)
        assert len(doctors) == 2
        assert any(d.username == 'Иванов' for d in doctors)
        assert any(d.username == 'Петров' for d in doctors)

# 3. Тест: метод без возвращаемого значения (void-подобный) 
def test_set_password_void_method(app):
    with app.app_context():
        user = User(username='VoidTest', email='void@test.com', phone='999-void', role='patient')
        initial_hash = user.password_hash
        result = user.set_password('MySecretPass')
        assert result is None
        assert user.password_hash != initial_hash
        assert user.password_hash is not None
        assert user.check_password('MySecretPass') is True
        assert user.check_password('WrongPass') is False

# 4. Тест: использование mock-объекта (исправлен current_user)
def test_log_action_with_mock(client, app):
    with app.app_context():
        user = User(username='MockUser', email='mock@test.com', phone='777-mock', role='patient')
        user.set_password('pass')
        db.session.add(user)
        db.session.commit()

        from app.utils import log_action
        
        # Мокаем current_user и методы сессии БД
        with patch('app.utils.current_user') as mock_current_user, \
             patch('app.utils.db.session.add') as mock_add, \
             patch('app.utils.db.session.commit') as mock_commit:
            
            # Настраиваем mock_current_user
            mock_current_user.is_authenticated = True
            mock_current_user.id = user.id
            
            # Создаём фиктивный request context для request.remote_addr
            with app.test_request_context('/test', environ_base={'REMOTE_ADDR': '127.0.0.1'}):
                log_action('TEST_ACTION', 'Проверка работы mock')
            
            mock_add.assert_called_once()
            mock_commit.assert_called_once()
            
            log_obj = mock_add.call_args[0][0]
            assert log_obj.action_type == 'TEST_ACTION'
            assert log_obj.description == 'Проверка работы mock'
            assert log_obj.user_id == user.id