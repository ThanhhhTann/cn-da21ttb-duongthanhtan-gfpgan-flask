from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from backend.app.config import Config
from backend.app.db import db
from dotenv import load_dotenv
import os

# Load file .env
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '../.env'))

# Khởi tạo Flask App
app = Flask(__name__)
app.config.from_object(Config)

# Khởi tạo CSDL và JWT
db.init_app(app)
jwt = JWTManager(app)

# Đăng ký các routes
from backend.app.routes.auth_routes import auth_blueprint
from .routes.main_routes import main_blueprint
from .routes.frontend_routes import frontend_bp

app.register_blueprint(auth_blueprint, url_prefix='/auth')
app.register_blueprint(main_blueprint)
app.register_blueprint(frontend_bp)

# Tạo CSDL nếu chưa tồn tại
with app.app_context():
    db.create_all()
    print("✅ Database tables created successfully!")
