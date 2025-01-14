from flask import Blueprint, render_template, redirect, url_for, flash
from flask_jwt_extended import jwt_required, get_jwt

main_blueprint = Blueprint('main', __name__)

# Trang chủ chung
@main_blueprint.route('/')
@jwt_required()
def home():
    claims = get_jwt()
    is_admin = claims.get('role') == 'admin'
    return render_template('index.html', is_admin=is_admin)

# Trang quản trị (chỉ dành cho admin)
@main_blueprint.route('/admin')
@jwt_required()
def admin_dashboard():
    claims = get_jwt()
    if claims.get('role') != 'admin':
        flash("Bạn không có quyền truy cập!")
        return redirect(url_for('main.home'))
    return render_template('admin.html')
