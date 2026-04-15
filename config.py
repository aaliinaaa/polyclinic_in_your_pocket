import os

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    # Секретный ключ для защиты сессий и CSRF-токенов
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Настройки базы данных (SQLite для разработки)
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'instance', 'polyclinic.db')
    
    # Отключаем отслеживание изменений объектов (экономит ресурсы)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Настройки для Flask-Login (необязательно, но полезно)
    REMEMBER_COOKIE_DURATION = 3600  # Запоминать на 1 час