from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect # Импортируем CSRFProtect
from config import Config

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect() # Создаем экземпляр CSRF

login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Инициализация расширений
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app) # Инициализируем CSRF

    # Регистрация Blueprints
    from app.main import bp as main_bp
    app.register_blueprint(main_bp)

    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp)

    from app.patient import bp as patient_bp
    app.register_blueprint(patient_bp, url_prefix='/patient')

    from app.doctor import bp as doctor_bp
    app.register_blueprint(doctor_bp, url_prefix='/doctor')

    from app.admin import bp as admin_bp
    app.register_blueprint(admin_bp, url_prefix='/admin')

    @app.context_processor
    def utility_processor():
        from flask_login import current_user
        from datetime import datetime
        return dict(current_user=current_user, now=datetime.now)

    return app