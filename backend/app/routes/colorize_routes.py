from flask import Blueprint, request, jsonify, render_template
from backend.app.db import db
from backend.app.models import User, Image, UserPackage
from flask_jwt_extended import jwt_required, get_jwt_identity
from azure.storage.blob import BlobServiceClient
import os
import uuid
import requests
import replicate
from sqlalchemy.sql import func
import time
from flask_cors import CORS

# 🔹 Cấu hình Azure Storage
AZURE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
CONTAINER_NAME_ORIGINAL = "user-uploads"  # 📌 Ảnh gốc tải lên
CONTAINER_NAME_PROCESSED = "color-image"  # 📌 Ảnh sau khi tô màu
blob_service_client = BlobServiceClient.from_connection_string(AZURE_CONNECTION_STRING)

# 🔹 API Token của Replicate
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")

colorize_blueprint = Blueprint("colorize", __name__)
CORS(colorize_blueprint)  # ✅ Cho phép tất cả origin truy cập API

# ✅ **API: Tải ảnh lên Azure Storage**
@colorize_blueprint.route("/upload", methods=["POST"])
@jwt_required()
def upload_image():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    if not user:
        return jsonify({"error": "User không tồn tại!"}), 400

    file = request.files.get("image")
    if not file:
        return jsonify({"error": "Không có file nào được tải lên!"}), 400

    # ✅ Tạo tên file ngẫu nhiên
    blob_name = f"{uuid.uuid4()}.jpg"

    # ✅ Upload ảnh lên Azure Storage
    blob_client = blob_service_client.get_blob_client(container=CONTAINER_NAME_ORIGINAL, blob=blob_name)
    blob_client.upload_blob(file.read(), overwrite=True)

    image_url = f"https://{blob_service_client.account_name}.blob.core.windows.net/{CONTAINER_NAME_ORIGINAL}/{blob_name}"

    # ✅ Lưu vào database
    new_image = Image(user_id=user_id, image_original_url=image_url)
    db.session.add(new_image)
    db.session.commit()

    return jsonify({"message": "Ảnh đã tải lên thành công!", "image_id": str(new_image.image_id), "image_url": image_url})


# ✅ **API: Gửi ảnh đến Replicate để tô màu**
@colorize_blueprint.route("/colorize", methods=["POST"])
@jwt_required()
def colorize_image():
    data = request.json
    image_url = data.get("image_url")
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    if not user or not image_url:
        return jsonify({"error": "Thiếu thông tin người dùng hoặc URL ảnh!"}), 400

    # ✅ Kiểm tra tín dụng người dùng
    total_credits = db.session.query(
        func.coalesce(func.sum(UserPackage.user_package_credits), 0)
    ).filter(UserPackage.user_id == user.user_id).scalar()

    if total_credits < 2:
        return jsonify({"error": "Bạn không đủ tín dụng để tô màu ảnh!"}), 403

    # ✅ Gửi ảnh đến API Replicate
    try:
        output_image_url = replicate.run(
            "arielreplicate/deoldify_image:0da600fab0c45a66211339f1c16b71345d22f26ef5fea3dca1bb90bb5711e950",
            input={
                "model_name": "Artistic",
                "input_image": image_url,
                "render_factor": 35
            }
        )

        if not output_image_url:
            return jsonify({"error": "Không thể tô màu ảnh!"}), 500

    except Exception as e:
        return jsonify({"error": f"Lỗi khi kết nối đến Replicate: {str(e)}"}), 500

    # ✅ Tăng thời gian chờ tối đa lên 10 phút (600 giây)
    start_time = time.time()
    while True:
        if time.time() - start_time > 600:  # 10 phút
            return jsonify({"error": "Quá thời gian chờ, vui lòng thử lại sau!"}), 500

        try:
            response = requests.get(output_image_url, timeout=30, stream=True)
            if response.status_code == 200:
                image_data = response.content
                break
        except:
            time.sleep(10)

    # ✅ Upload ảnh đã tô màu lên Azure
    blob_name = f"colorized_{uuid.uuid4()}.jpg"
    processed_blob_client = blob_service_client.get_blob_client(container=CONTAINER_NAME_PROCESSED, blob=blob_name)
    processed_blob_client.upload_blob(image_data, overwrite=True)

    processed_url = f"https://{blob_service_client.account_name}.blob.core.windows.net/{CONTAINER_NAME_PROCESSED}/{blob_name}"

    # ✅ Lưu vào database
    image = Image.query.filter_by(image_original_url=image_url).first()
    if image:
        image.image_restored_url = processed_url
        db.session.commit()

    # ✅ Trừ 2 tín dụng của người dùng
    user_package = UserPackage.query.filter(UserPackage.user_id == user.user_id).first()
    if user_package:
        user_package.user_package_credits -= 2
        db.session.commit()

    return jsonify({"message": "Ảnh đã tô màu thành công!", "processed_image_url": processed_url})


# ✅ **API: Lấy danh sách ảnh đã tô màu**
@colorize_blueprint.route("/images", methods=["GET"])
@jwt_required()
def get_user_images():
    user_id = get_jwt_identity()
    images = Image.query.filter_by(user_id=user_id).all()

    image_list = [{
        "original_url": img.image_original_url,
        "processed_url": img.image_restored_url or ""
    } for img in images]

    return jsonify({"images": image_list})


# ✅ **Trang hiển thị giao diện tô màu ảnh**
@colorize_blueprint.route("/", methods=["GET"])
@jwt_required()
def colorize_page():
    return render_template("colorize.html")
