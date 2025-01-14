from backend.app.db import db
from flask_bcrypt import Bcrypt
from sqlalchemy import Column, String, DateTime, UUID
import uuid
from datetime import datetime

bcrypt = Bcrypt()

class User(db.Model):
    __tablename__ = 'users'
    user_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_username = db.Column(String(50), unique=True, nullable=False)
    user_email = db.Column(String(100), unique=True, nullable=False)
    user_password_hash = db.Column(String(255), nullable=True)
    user_role = db.Column(String(20), default='user')
    user_created_at = db.Column(DateTime, default=datetime.utcnow)
    user_updated_at = db.Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def set_password(self, password):
        self.user_password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.user_password_hash, password)
