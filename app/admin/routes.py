from flask import render_template
from flask_login import login_required
from app.admin import bp
from app.utils import role_required

@bp.route('/dashboard')
@login_required
@role_required('admin')
def dashboard():
    return render_template('admin/dashboard.html', title='Панель администратора')