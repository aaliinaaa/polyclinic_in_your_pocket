from flask import render_template
from flask_login import login_required
from app.patient import bp
from app.utils import role_required

@bp.route('/dashboard')
@login_required
@role_required('patient')
def dashboard():
    return render_template('patient/dashboard.html', title='Кабинет пациента')