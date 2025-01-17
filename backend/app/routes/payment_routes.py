from flask import Blueprint, request, jsonify, render_template, redirect, url_for
import requests
import os
from backend.app.db import db
from backend.app.models import User, Payment, Package, UserPackage
from flask_jwt_extended import jwt_required, get_jwt_identity

payment_blueprint = Blueprint("payment", __name__)

PAYPAL_CLIENT_ID = os.getenv("PAYPAL_CLIENT_ID")
PAYPAL_SECRET = os.getenv("PAYPAL_SECRET")
PAYPAL_MODE = os.getenv("PAYPAL_MODE", "sandbox")  # sandbox hoặc live

PAYPAL_API_URL = "https://api-m.sandbox.paypal.com" if PAYPAL_MODE == "sandbox" else "https://api-m.paypal.com"


# ==============================
# ✅ Route: Trang chọn gói thanh toán
# ==============================
@payment_blueprint.route("/payment", methods=["GET"])
@jwt_required()
def payment_page():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    # Lấy danh sách các gói package từ CSDL
    packages = Package.query.all()

    return render_template("payment.html", user=user, packages=packages, paypal_client_id=PAYPAL_CLIENT_ID)


# ==============================
# ✅ Route: Xử lý thanh toán với PayPal
# ==============================
@payment_blueprint.route("/process", methods=["POST"])  # 🔄 Đổi tên endpoint
@jwt_required()
def process_payment():
    data = request.json
    package_id = data.get("package_id")
    paypal_order_id = data.get("paypal_order_id")

    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    package = Package.query.get(package_id)

    if not user or not package:
        return jsonify({"error": "User hoặc Package không hợp lệ!"}), 400

    # Gọi API PayPal để xác nhận thanh toán
    access_token = get_paypal_access_token()
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {access_token}"}
    verify_url = f"{PAYPAL_API_URL}/v2/checkout/orders/{paypal_order_id}"
    
    response = requests.get(verify_url, headers=headers)
    response_json = response.json()

    if response.status_code != 200 or response_json.get("status") != "COMPLETED":
        return jsonify({"error": "Thanh toán chưa hoàn tất!"}), 400

    # Lưu thông tin thanh toán vào CSDL
    new_payment = Payment(
        user_id=user_id,
        payment_amount=package.package_price,
        payment_currency="USD",
        payment_method="PayPal",
        payment_status="completed"
    )
    db.session.add(new_payment)

    # Cập nhật tín dụng cho người dùng
    user_package = UserPackage.query.filter_by(user_id=user_id, package_id=package_id).first()
    if user_package:
        user_package.user_package_credits += package.package_credits
    else:
        new_user_package = UserPackage(
            user_id=user_id,
            package_id=package_id,
            user_package_credits=package.package_credits
        )
        db.session.add(new_user_package)

    db.session.commit()

    return jsonify({"message": "Thanh toán thành công!", "credits": package.package_credits})



# ==============================
# ✅ Lấy danh sách gói dịch vụ
# ==============================
@payment_blueprint.route("/payment/packages", methods=["GET"])
def get_packages():
    packages = Package.query.all()
    package_list = [
        {
            "id": str(pkg.package_id),
            "name": pkg.package_name,
            "price": float(pkg.package_price),
            "credits": pkg.package_credits,
            "description": pkg.package_description
        }
        for pkg in packages
    ]
    return jsonify(package_list)


# ==============================
# ✅ Hàm hỗ trợ: Lấy Access Token từ PayPal
# ==============================
def get_paypal_access_token():
    auth_url = f"{PAYPAL_API_URL}/v1/oauth2/token"
    auth_data = {"grant_type": "client_credentials"}
    auth_headers = {"Accept": "application/json", "Accept-Language": "en_US"}

    response = requests.post(auth_url, auth_data, headers=auth_headers, auth=(PAYPAL_CLIENT_ID, PAYPAL_SECRET))
    response_json = response.json()

    return response_json.get("access_token")


@payment_blueprint.route("/payment/checkout", methods=["GET"])
@jwt_required()
def payment_checkout():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    # Lấy danh sách các gói package từ CSDL
    packages = Package.query.all()

    return render_template("payment.html", user=user, packages=packages, paypal_client_id=PAYPAL_CLIENT_ID)
