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
from sqlalchemy.sql import func  # ✅ Import func để tính tổng tín dụng

# 🔹 Cấu hình Azure Storage
AZURE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
CONTAINER_NAME_ORIGINAL = "user-uploads"
CONTAINER_NAME_ENHANCED = "enhanced-images"
blob_service_client = BlobServiceClient.from_connection_string(AZURE_CONNECTION_STRING)

esrgan_blueprint = Blueprint("esrgan", __name__)

# 🔹 Resize ảnh trước khi upload (max 1024x1024)
def resize_image(image_data):
    image = PILImage.open(BytesIO(image_data))
    
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
    image.save(buffer, format="JPEG")  
    return buffer.getvalue()


# ✅ API: Tải ảnh lên Azure Storage
@esrgan_blueprint.route("/upload", methods=["POST"])
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
    blob_client = blob_service_client.get_blob_client(container=CONTAINER_NAME_ORIGINAL, blob=blob_name)
    blob_client.upload_blob(resized_image_data, overwrite=True)

    # Lưu URL vào database
    image_url = f"https://{blob_service_client.account_name}.blob.core.windows.net/{CONTAINER_NAME_ORIGINAL}/{blob_name}"
    new_image = Image(user_id=user_id, image_original_url=image_url)
    db.session.add(new_image)
    db.session.commit()

    return jsonify({"message": "Ảnh đã tải lên thành công!", "image_id": str(new_image.image_id), "image_url": image_url})


# ✅ API: Gửi ảnh đến Replicate để nâng cấp và trừ 2 tín dụng
@esrgan_blueprint.route("/enhance", methods=["POST"])
@jwt_required()
def enhance_image():
    data = request.json
    image_id = data.get("image_id")
    scale = data.get("scale", 2)  # Mặc định scale = 2
    face_enhance = data.get("face_enhance", False)  

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
        return jsonify({"error": "Bạn không đủ tín dụng để nâng cấp ảnh!"}), 403

    # ✅ Gửi ảnh đến API Replicate
    try:
        output_url = replicate.run(
            "nightmareai/real-esrgan:f121d640bd286e1fdc67f9799164c1d5be36ff74576ee11c803ae5b665dd46aa",
            input={
                "image": image.image_original_url,
                "scale": scale,
                "face_enhance": face_enhance
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
        response = requests.get(output_url, timeout=15, stream=True)
        response.raise_for_status()
        image_data = response.content
    except Exception as e:
        print("❌ Lỗi khi tải ảnh từ Replicate:", str(e))
        return jsonify({"error": "Không thể tải ảnh từ Replicate!"}), 500

    # ✅ Upload ảnh lên Azure Storage
    blob_name = f"enhanced_{uuid.uuid4()}.jpg"
    enhanced_blob_client = blob_service_client.get_blob_client(container=CONTAINER_NAME_ENHANCED, blob=blob_name)
    enhanced_blob_client.upload_blob(image_data, overwrite=True)

    enhanced_url = f"https://{blob_service_client.account_name}.blob.core.windows.net/{CONTAINER_NAME_ENHANCED}/{blob_name}"

    # ✅ Lưu vào database
    image.image_restored_url = enhanced_url
    db.session.commit()

    # ✅ Trừ tín dụng sau khi nâng cấp thành công
    user_package = UserPackage.query.filter(
        UserPackage.user_id == user.user_id
    ).first()
    if user_package:
        user_package.user_package_credits -= 2
        db.session.commit()

    return jsonify({"message": "Ảnh đã nâng cấp thành công!", "enhanced_url": enhanced_url})


# ✅ API: Lấy danh sách ảnh đã tải lên và đã nâng cấp
@esrgan_blueprint.route("/list", methods=["GET"])
@jwt_required()
def list_images():
    user_id = get_jwt_identity()
    images = Image.query.filter_by(user_id=user_id).all()

    image_list = [
        {
            "image_id": str(img.image_id),
            "original_url": img.image_original_url,
            "enhanced_url": img.image_restored_url
        }
        for img in images
    ]

    return jsonify({"images": image_list})


# ✅ Trang hiển thị giao diện nâng cấp ảnh
@esrgan_blueprint.route("/", methods=["GET"])
@jwt_required()
def esrgan_page():
    return render_template("esrgan.html")

# ✅ API: Lấy danh sách ảnh đã tải lên & đã nâng cấp
@esrgan_blueprint.route("/images", methods=["GET"])
@jwt_required()
def get_user_images():
    user_id = get_jwt_identity()
    images = Image.query.filter_by(user_id=user_id).all()

    image_list = [{
        "original_url": img.image_original_url,
        "enhanced_url": img.image_restored_url
    } for img in images]

    return jsonify({"images": image_list})
