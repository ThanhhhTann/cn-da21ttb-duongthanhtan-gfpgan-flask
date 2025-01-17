from backend.app.db import db
from flask_bcrypt import Bcrypt
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, DECIMAL, UUID
import uuid
from datetime import datetime

bcrypt = Bcrypt()

# ============================
# ✅ Bảng Users (Người dùng)
# ============================
class User(db.Model):
    __tablename__ = 'users'
    user_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_username = db.Column(String(50), unique=True, nullable=False)
    user_email = db.Column(String(100), unique=True, nullable=False)
    user_password_hash = db.Column(String(255), nullable=True)
    user_role = db.Column(String(20), default='user')
    user_created_at = db.Column(DateTime, default=datetime.utcnow)
    user_updated_at = db.Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user_avatar = db.Column(String(255), default="https://refinaimages-ehh5dse7h5f8g5ga.z02.azurefd.net/images/cn-logo-default-1.webp")
    reset_otp_code = db.Column(String(6), nullable=True)
    reset_otp_expiry = db.Column(DateTime, nullable=True)

    def set_password(self, password):
        self.user_password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.user_password_hash, password)


# ============================
# ✅ Bảng Packages (Gói tín dụng)
# ============================
class Package(db.Model):
    __tablename__ = 'packages'
    package_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    package_name = db.Column(String(50), unique=True, nullable=False)
    package_price = db.Column(DECIMAL(10, 2), nullable=False)
    package_credits = db.Column(Integer, nullable=False)
    package_description = db.Column(String(255))
    package_created_at = db.Column(DateTime, default=datetime.utcnow)
    package_updated_at = db.Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ============================
# ✅ Bảng UserPackages (Gói của người dùng)
# ============================
class UserPackage(db.Model):
    __tablename__ = 'user_packages'
    user_package_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.user_id'), nullable=False)
    package_id = db.Column(UUID(as_uuid=True), db.ForeignKey('packages.package_id'), nullable=False)
    user_package_credits = db.Column(Integer, nullable=False)
    user_package_purchased_at = db.Column(DateTime, default=datetime.utcnow)
    user_package_expired_at = db.Column(DateTime, nullable=True)
    user_package_updated_at = db.Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ============================
# ✅ Bảng Payments (Thanh toán)
# ============================
class Payment(db.Model):
    __tablename__ = 'payments'
    payment_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.user_id'), nullable=False)
    payment_amount = db.Column(DECIMAL(10, 2), nullable=False)
    payment_currency = db.Column(String(10), default='USD')
    payment_method = db.Column(String(50), nullable=False)
    payment_status = db.Column(String(20), default='pending')
    payment_created_at = db.Column(DateTime, default=datetime.utcnow)
    payment_updated_at = db.Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Image(db.Model):
    __tablename__ = 'images'
    image_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.user_id'), nullable=False)
    image_original_url = db.Column(String(255), nullable=False)
    image_restored_url = db.Column(String(255), nullable=True)
    image_status = db.Column(String(20), default='pending')
    image_credits_used = db.Column(Integer, default=2)  # ✅ Mỗi lần xử lý trừ 2 tín dụng
    image_created_at = db.Column(DateTime, default=datetime.utcnow)
    image_updated_at = db.Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)