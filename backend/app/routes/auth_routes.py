# backend/app/routes/auth_routes.py
from flask import Blueprint, request, render_template, redirect, url_for, flash, make_response, jsonify, session
from backend.app.db import db
from backend.app.models import User
from flask_jwt_extended import create_access_token, jwt_required, unset_jwt_cookies, set_access_cookies, get_jwt_identity, get_jwt
from datetime import timedelta
import requests
import os

auth_blueprint = Blueprint('auth', __name__)

# ===========================
# ✅ ĐĂNG KÝ & ĐĂNG NHẬP BÌNH THƯỜNG
# ===========================

# Trang giao diện đăng ký
@auth_blueprint.route('/register', methods=['GET'])
def register_page():
    return render_template('register.html')

# Trang giao diện đăng nhập
@auth_blueprint.route('/login', methods=['GET'])
def login_page():
    return render_template('login.html')

# Đăng ký người dùng
@auth_blueprint.route('/register', methods=['POST'])
def register():
    data = request.form
    if not data.get('username') or not data.get('password'):
        flash("Thiếu thông tin cần thiết!")
        return redirect(url_for('auth.register_page'))

    if User.query.filter_by(user_username=data['username']).first():
        flash("Tên người dùng đã tồn tại!")
        return redirect(url_for('auth.register_page'))

    new_user = User(
        user_username=data['username'],
        user_email=data['email']
    )
    new_user.set_password(data['password'])
    db.session.add(new_user)
    db.session.commit()

    flash("Đăng ký thành công!")
    return redirect(url_for('auth.login_page'))

# Đăng nhập bằng tài khoản thường
@auth_blueprint.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')

    user = User.query.filter_by(user_username=username).first()

    if user and user.check_password(password):
        access_token = create_access_token(
            identity=user.user_id,
            expires_delta=timedelta(hours=1),
            additional_claims={"role": user.user_role}
        )
        response = make_response(redirect(url_for('main.home')))
        set_access_cookies(response, access_token)
        flash("Đăng nhập thành công!")
        return response
    else:
        flash("Sai thông tin đăng nhập!")
        return redirect(url_for('auth.login_page'))

# Đăng xuất người dùng
@auth_blueprint.route('/logout', methods=['GET'])
@jwt_required()
def logout():
    response = redirect(url_for('auth.login_page'))
    unset_jwt_cookies(response)
    flash("Bạn đã đăng xuất thành công!")
    return response

# =============================
# ĐĂNG NHẬP MICROSOFT OAUTH2
# =============================

MICROSOFT_AUTH_URL = f"https://login.microsoftonline.com/{os.getenv('MICROSOFT_TENANT_ID')}/oauth2/v2.0/authorize"
MICROSOFT_TOKEN_URL = f"https://login.microsoftonline.com/{os.getenv('MICROSOFT_TENANT_ID')}/oauth2/v2.0/token"
CLIENT_ID = os.getenv('MICROSOFT_CLIENT_ID')
CLIENT_SECRET = os.getenv('MICROSOFT_CLIENT_SECRET')
REDIRECT_URI = os.getenv('MICROSOFT_REDIRECT_URI')

# Route chuyển hướng đến trang Microsoft để đăng nhập
@auth_blueprint.route('/microsoft')
def microsoft_login():
    auth_url = (
        f"{MICROSOFT_AUTH_URL}?client_id={CLIENT_ID}&response_type=code"
        f"&redirect_uri={REDIRECT_URI}&response_mode=query&scope=openid profile email"
    )
    return redirect(auth_url)

# Callback xử lý sau khi đăng nhập Microsoft
@auth_blueprint.route('/microsoft/callback')
def microsoft_callback():
    code = request.args.get('code')
    
    if not code:
        flash("Lỗi trong quá trình đăng nhập!")
        return redirect(url_for('auth.login_page'))

    token_data = {
        "client_id": CLIENT_ID,
        "scope": "openid profile email",
        "client_secret": CLIENT_SECRET,
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code"
    }
    
    # Trao đổi mã code để lấy token từ Microsoft
    response = requests.post(MICROSOFT_TOKEN_URL, data=token_data)
    token_json = response.json()

    # Kiểm tra lỗi từ phía Microsoft
    if 'access_token' not in token_json:
        flash("Xác thực Microsoft thất bại!")
        return redirect(url_for('auth.login_page'))

    # Lấy access token và user info
    access_token = token_json['access_token']
    headers = {"Authorization": f"Bearer {access_token}"}
    user_info_response = requests.get("https://graph.microsoft.com/v1.0/me", headers=headers)
    user_info = user_info_response.json()

    # Kiểm tra xem có nhận được email không
    user_email = user_info.get('userPrincipalName')
    if not user_email:
        flash("Không thể lấy thông tin tài khoản Microsoft!")
        return redirect(url_for('auth.login_page'))

    # Tìm kiếm hoặc tạo người dùng mới
    existing_user = User.query.filter_by(user_email=user_email).first()
    if not existing_user:
        new_user = User(
            user_username=user_info.get('displayName'),
            user_email=user_email
        )
        db.session.add(new_user)
        db.session.commit()
        flash("Tài khoản mới đã được tạo!")

    # Tạo JWT Token và lưu vào cookie
    jwt_token = create_access_token(identity=user_email, additional_claims={"role": "user"})
    response = make_response(redirect(url_for('main.home')))
    set_access_cookies(response, jwt_token)
    flash("Đăng nhập thành công với Microsoft!")
    return response
