from flask import Blueprint, request, render_template, redirect, url_for, flash, session
from backend.app.db import db
from backend.app.models import User
import random
from azure.communication.email import EmailClient
from datetime import datetime, timedelta
import os

password_blueprint = Blueprint('password', __name__)

# ✅ Hàm gửi OTP qua email
def send_reset_otp(email, otp_code):
    connection_string = os.getenv("AZURE_EMAIL_CONNECTION_STRING")
    client = EmailClient.from_connection_string(connection_string)

    message = {
        "senderAddress": "DoNotReply@e6b01f03-d4eb-408b-89eb-f6ea8cdae076.azurecomm.net",
        "recipients": {"to": [{"address": email}]},
        "content": {
            "subject": "Mã OTP đặt lại mật khẩu",
            "plainText": f"Mã OTP của bạn là: {otp_code}. Vui lòng nhập mã này để đặt lại mật khẩu.",
        },
    }
    client.begin_send(message)

# ✅ Route xử lý khi nhập email để nhận OTP
@password_blueprint.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(user_email=email).first()

        if not user:
            flash("Email không tồn tại!")
            return redirect(url_for('password.forgot_password'))

        # ✅ Tạo OTP
        otp_code = str(random.randint(100000, 999999))
        otp_expiry = datetime.utcnow() + timedelta(minutes=5)

        # ✅ Lưu OTP vào user
        user.reset_otp_code = otp_code
        user.reset_otp_expiry = otp_expiry
        db.session.commit()

        # ✅ Gửi OTP
        send_reset_otp(email, otp_code)

        # ✅ Lưu email vào session để chuyển hướng
        session['reset_email'] = email

        flash("OTP đã được gửi đến email của bạn. Vui lòng kiểm tra!")
        return redirect(url_for('password.reset_password'))  # Chuyển hướng sau khi gửi OTP

    return render_template('forgot_password.html')

# ✅ Route nhập OTP và cập nhật mật khẩu
@password_blueprint.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    email = session.get('reset_email')  # ✅ Lấy email từ session

    if request.method == 'POST':
        otp_code = request.form.get('otp_code')
        new_password = request.form.get('new_password')

        user = User.query.filter_by(user_email=email).first()
        if user and user.reset_otp_code == otp_code and user.reset_otp_expiry > datetime.utcnow():
            user.set_password(new_password)
            user.reset_otp_code = None
            user.reset_otp_expiry = None
            db.session.commit()

            # Xóa email khỏi session sau khi đặt lại mật khẩu
            session.pop('reset_email', None)

            flash("Mật khẩu đã được cập nhật thành công!")
            return redirect(url_for('auth.login_page'))

        flash("OTP không hợp lệ hoặc đã hết hạn!")
        return redirect(url_for('password.reset_password'))

    if not email:
        flash("Yêu cầu không hợp lệ!")
        return redirect(url_for('password.forgot_password'))

    user = User.query.filter_by(user_email=email).first()
    if not user:
        flash("Email không hợp lệ!")
        return redirect(url_for('password.forgot_password'))

    return render_template('reset_password.html', username=user.user_username, email=user.user_email)
