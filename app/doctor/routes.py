from flask import render_template
from flask_login import login_required
from app.doctor import bp
from app.utils import role_required

@bp.route('/dashboard')
@login_required
@role_required('doctor')
def dashboard():
    return render_template('doctor/dashboard.html', title='Кабинет врача')