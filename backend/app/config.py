import os
from dotenv import load_dotenv

# Tải file .env
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '../.env'))

class Config:
    # Cấu hình cơ sở dữ liệu
    SQLALCHEMY_DATABASE_URI = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # JWT Config
    SECRET_KEY = os.getenv('SECRET_KEY')
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY')
    JWT_TOKEN_LOCATION = ["cookies"]
    JWT_COOKIE_SECURE = False
    JWT_COOKIE_CSRF_PROTECT = False
    JWT_ACCESS_COOKIE_NAME = "access_token_cookie"

    # Cấu hình dịch vụ Azure Email 
    AZURE_EMAIL_CONNECTION_STRING = os.getenv("AZURE_EMAIL_CONNECTION_STRING")

    # Cấu hình PayPal
    # Cấu hình PayPal API
    PAYPAL_CLIENT_ID = os.getenv("PAYPAL_CLIENT_ID")
    PAYPAL_SECRET = os.getenv("PAYPAL_SECRET")
    PAYPAL_MODE = os.getenv("PAYPAL_MODE", "sandbox")  # sandbox hoặc live 
