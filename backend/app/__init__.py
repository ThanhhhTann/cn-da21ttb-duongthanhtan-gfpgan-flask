from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, get_jwt_identity, verify_jwt_in_request
from backend.app.config import Config
from backend.app.db import db
from dotenv import load_dotenv
import os

# Import các models
from backend.app.models import User, UserPackage  # ✅ Gộp chung vào một dòng
from sqlalchemy.sql import func  # ✅ Import func để tính tổng tín dụng

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
from .routes.password_routes import password_blueprint
from backend.app.routes.payment_routes import payment_blueprint
from backend.app.routes.gfpgan_routes import gfpgan_blueprint
from backend.app.routes.esrgan_routes import esrgan_blueprint
from backend.app.routes.lama_routes import lama_blueprint
from backend.app.routes.sd_routes import sd_blueprint
from backend.app.routes.sdxl_routes import sdxl_blueprint
from backend.app.routes.video_routes import video_blueprint
from backend.app.routes.video01_routes import video01_blueprint

app.register_blueprint(auth_blueprint, url_prefix='/auth')
app.register_blueprint(main_blueprint)
app.register_blueprint(frontend_bp)
app.register_blueprint(password_blueprint, url_prefix='/password')
app.register_blueprint(payment_blueprint, url_prefix='/payment')
app.register_blueprint(gfpgan_blueprint, url_prefix='/gfpgan')
app.register_blueprint(esrgan_blueprint, url_prefix='/esrgan')
app.register_blueprint(lama_blueprint, url_prefix='/lama')
app.register_blueprint(sd_blueprint, url_prefix='/sd')
app.register_blueprint(sdxl_blueprint, url_prefix='/sdxl')
app.register_blueprint(video_blueprint, url_prefix="/video")
app.register_blueprint(video01_blueprint, url_prefix="/video01")

# ✅ Fix lỗi: Kiểm tra token hợp lệ trước khi gọi get_jwt_identity()
@app.context_processor
def inject_user():
    user = None
    try:
        verify_jwt_in_request(optional=True)
        user_id = get_jwt_identity()
        if user_id:
            user = User.query.get(user_id)
            if user:
                # Tính tổng tín dụng mới nhất
                user.total_credits = db.session.query(
                    func.coalesce(func.sum(UserPackage.user_package_credits), 0)
                ).filter(UserPackage.user_id == user.user_id).scalar()
                db.session.commit()  # ✅ Lưu cập nhật vào database
    except Exception:
        pass
    return dict(current_user=user)


# Tạo CSDL nếu chưa tồn tại
with app.app_context():
    db.create_all()
    print("✅ Database tables created successfully!")
