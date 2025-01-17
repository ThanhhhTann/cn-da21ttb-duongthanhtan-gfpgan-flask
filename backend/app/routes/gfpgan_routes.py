from flask import Blueprint, request, jsonify, render_template
from backend.app.db import db
from backend.app.models import User, Image, UserPackage
from flask_jwt_extended import jwt_required, get_jwt_identity
from azure.storage.blob import BlobServiceClient
import os
import uuid
import requests
import replicate
from PIL import Image as PILImage
from io import BytesIO
import time
from sqlalchemy.sql import func  # ✅ Import func để tính tổng tín dụng

# 🔹 Cấu hình Azure Storage
AZURE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
CONTAINER_NAME_ORIGINAL = "user-uploads"
CONTAINER_NAME_RESTORED = "restored-images"
blob_service_client = BlobServiceClient.from_connection_string(AZURE_CONNECTION_STRING)

gfpgan_blueprint = Blueprint("gfpgan", __name__)

# 🔹 Resize ảnh trước khi upload (max 1024x1024)
def resize_image(image_data):
    image = PILImage.open(BytesIO(image_data))
    
    # Chuyển đổi ảnh có kênh Alpha (RGBA) sang RGB
    if image.mode == "RGBA":
        image = image.convert("RGB")

    max_size = 1024
    width, height = image.size

    if width > max_size or height > max_size:
        if width > height:
            new_width = max_size
            new_height = int((max_size / width) * height)
        else:
            new_height = max_size
            new_width = int((max_size / height) * width)

        image = image.resize((new_width, new_height), PILImage.LANCZOS)

    buffer = BytesIO()
    image.save(buffer, format="JPEG")  # ✅ Lưu lại đúng định dạng JPEG
    return buffer.getvalue()


@gfpgan_blueprint.route("/upload", methods=["POST"])
@jwt_required()
def upload_image():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    if not user:
        return jsonify({"error": "User không tồn tại!"}), 400

    file = request.files.get("image")
    if not file:
        return jsonify({"error": "Không có file nào được tải lên!"}), 400

    # Resize ảnh
    image_data = file.read()
    resized_image_data = resize_image(image_data)

    # Tạo tên file ngẫu nhiên
    blob_name = f"{uuid.uuid4()}.jpg"

    # Upload lên Azure Storage
    blob_client = blob_service_client.get_blob_client(
        container=CONTAINER_NAME_ORIGINAL,
        blob=blob_name
    )
    blob_client.upload_blob(resized_image_data, overwrite=True)

    # Lưu URL vào database
    image_url = f"https://{blob_service_client.account_name}.blob.core.windows.net/{CONTAINER_NAME_ORIGINAL}/{blob_name}"
    new_image = Image(user_id=user_id, image_original_url=image_url)
    db.session.add(new_image)
    db.session.commit()

    return jsonify({
        "message": "Ảnh đã tải lên thành công!",
        "image_id": str(new_image.image_id),
        "image_url": image_url
    })


# --- BỎ HÀM CHỜ POLL VÌ KHÔNG CẦN DÙNG NỮA ---
# def wait_for_replicate_output(prediction_url, timeout=60):
#     ...
#     # KHÔNG CẦN CODE NÀY NỮA


@gfpgan_blueprint.route("/restore", methods=["POST"])
@jwt_required()
def restore_image():
    data = request.json
    image_id = data.get("image_id")

    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    image = Image.query.get(image_id)

    if not user or not image:
        return jsonify({"error": "User hoặc ảnh không hợp lệ!"}), 400

    # ✅ Kiểm tra tín dụng
    total_credits = db.session.query(
        func.coalesce(func.sum(UserPackage.user_package_credits), 0)
    ).filter(UserPackage.user_id == user.user_id).scalar()

    if total_credits < 2:
        return jsonify({"error": "Bạn không đủ tín dụng để khôi phục ảnh!"}), 403

    # ✅ Gửi ảnh đến API Replicate
    try:
        # replicate.run(...) tự block đến khi có URL đầu ra
        output_url = replicate.run(
            "tencentarc/gfpgan:0fbacf7afc6c144e5be9767cff80f25aff23e52b0708f17e20f9879b2f21516c",
            input={
                "img": image.image_original_url,
                "scale": 2,
                "version": "v1.4"
            }
        )

        print(f"✅ Replicate Output URL: {output_url}")

        if not output_url:
            return jsonify({"error": "Không thể lấy ảnh kết quả từ Replicate!"}), 500

    except Exception as e:
        print("❌ Lỗi khi gọi Replicate:", str(e))
        return jsonify({"error": "Lỗi khi kết nối đến Replicate!"}), 500

    # ✅ Tải ảnh từ URL trả về (output_url)
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        }
        response = requests.get(output_url, headers=headers, timeout=15, stream=True)
        response.raise_for_status()
        image_data = response.content
    except Exception as e:
        print("❌ Lỗi khi tải ảnh từ Replicate:", str(e))
        return jsonify({"error": "Không thể tải ảnh từ Replicate!"}), 500

    # ✅ Upload ảnh lên Azure
    blob_name = f"restored_{uuid.uuid4()}.jpg"
    restored_blob_client = blob_service_client.get_blob_client(
        container=CONTAINER_NAME_RESTORED,
        blob=blob_name
    )
    restored_blob_client.upload_blob(image_data, overwrite=True)

    restored_url = (
        f"https://{blob_service_client.account_name}.blob.core.windows.net/"
        f"{CONTAINER_NAME_RESTORED}/{blob_name}"
    )

    # Lưu vào database
    image.image_restored_url = restored_url
    db.session.commit()

    # ✅ Trừ tín dụng
    user_package = UserPackage.query.filter(
        UserPackage.user_id == user.user_id
    ).first()
    if user_package:
        user_package.user_package_credits -= 2
        db.session.commit()

    return jsonify({
        "message": "Ảnh đã phục hồi thành công!",
        "restored_url": restored_url
    })


@gfpgan_blueprint.route("/", methods=["GET"])
@jwt_required()
def gfpgan_page():
    return render_template("gfpgan.html")

@gfpgan_blueprint.route("/list", methods=["GET"])
@jwt_required()
def list_images():
    """ API lấy danh sách ảnh của user """
    user_id = get_jwt_identity()
    images = Image.query.filter_by(user_id=user_id).all()

    image_list = [
        {
            "image_id": str(img.image_id),
            "original_url": img.image_original_url,
            "restored_url": img.image_restored_url
        }
        for img in images
    ]

    return jsonify({"images": image_list})
