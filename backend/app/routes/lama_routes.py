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
from sqlalchemy.sql import func
import time
from flask_cors import CORS

# 🔹 Cấu hình Azure Storage
AZURE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
CONTAINER_NAME_ORIGINAL = "user-uploads"  # Ảnh gốc
CONTAINER_NAME_PROCESSED = "object-removed-images"  # Ảnh sau khi xóa vật thể
blob_service_client = BlobServiceClient.from_connection_string(AZURE_CONNECTION_STRING)

# 🔹 API Token của Replicate
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")

lama_blueprint = Blueprint("lama", __name__)
CORS(lama_blueprint)  # 🔹 Cho phép tất cả origin truy cập API

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


# ✅ **API: Tải ảnh lên Azure Storage**
@lama_blueprint.route("/upload", methods=["POST"])
@jwt_required()
def upload_image():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    if not user:
        return jsonify({"error": "User không tồn tại!"}), 400

    file = request.files.get("image")
    if not file:
        return jsonify({"error": "Không có file nào được tải lên!"}), 400

    image_data = file.read()
    resized_image_data = resize_image(image_data)

    blob_name = f"{uuid.uuid4()}.jpg"
    blob_client = blob_service_client.get_blob_client(container=CONTAINER_NAME_ORIGINAL, blob=blob_name)
    blob_client.upload_blob(resized_image_data, overwrite=True)

    image_url = f"https://{blob_service_client.account_name}.blob.core.windows.net/{CONTAINER_NAME_ORIGINAL}/{blob_name}"
    print(f"✅ Ảnh đã tải lên: {image_url}")  # ✅ **Debug in ra URL ảnh**

    new_image = Image(user_id=user_id, image_original_url=image_url)
    db.session.add(new_image)
    db.session.commit()

    return jsonify({"message": "Ảnh đã tải lên thành công!", "image_id": str(new_image.image_id), "image_url": image_url})


# ✅ **API: Gửi ảnh đến Replicate để xóa vật thể**
@lama_blueprint.route("/remove-object", methods=["POST"])
@jwt_required()
def remove_object():
    data = request.json
    image_id = data.get("image_id")
    mask_data = data.get("mask_data")

    if not image_id:
        return jsonify({"error": "Thiếu `image_id`!"}), 400

    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    image = Image.query.get(image_id)

    if not user or not image or not mask_data:
        return jsonify({"error": "User, ảnh hoặc mask không hợp lệ!"}), 400

    # ✅ Kiểm tra tín dụng
    total_credits = db.session.query(
        func.coalesce(func.sum(UserPackage.user_package_credits), 0)
    ).filter(UserPackage.user_id == user.user_id).scalar()

    if total_credits < 2:
        return jsonify({"error": "Bạn không đủ tín dụng để xóa vật thể!"}), 403

    # ✅ Sử dụng ảnh đã xử lý trước đó nếu có
    input_image_url = image.image_restored_url if image.image_restored_url else image.image_original_url

    headers = {"Authorization": f"Bearer {REPLICATE_API_TOKEN}", "Content-Type": "application/json"}
    payload = {
        "version": "cdac78a1bec5b23c07fd29692fb70baa513ea403a39e643c48ec5edadb15fe72",
        "input": {"image": input_image_url, "mask": mask_data},
    }

    try:
        response = requests.post("https://api.replicate.com/v1/predictions", headers=headers, json=payload)
        response_data = response.json()

        if response.status_code != 201:
            return jsonify({"error": "Lỗi khi gửi ảnh đến Replicate!"}), 500

        prediction_url = response_data["urls"]["get"]

        output_image_url = check_prediction_until_complete(prediction_url)

        if not output_image_url:
            return jsonify({"error": "Không thể lấy kết quả từ Replicate!"}), 500

    except Exception as e:
        return jsonify({"error": f"Lỗi kết nối đến Replicate: {str(e)}"}), 500

    # ✅ Tải ảnh từ Replicate
    try:
        response = requests.get(output_image_url, timeout=15, stream=True)
        response.raise_for_status()
        image_data = response.content
    except Exception as e:
        return jsonify({"error": "Không thể tải ảnh từ Replicate!"}), 500

    # ✅ Upload ảnh đã xử lý lên Azure
    blob_name = f"removed_{uuid.uuid4()}.jpg"
    processed_blob_client = blob_service_client.get_blob_client(container=CONTAINER_NAME_PROCESSED, blob=blob_name)
    processed_blob_client.upload_blob(image_data, overwrite=True)

    processed_url = f"https://{blob_service_client.account_name}.blob.core.windows.net/{CONTAINER_NAME_PROCESSED}/{blob_name}"

    # ✅ Lưu vào database
    image.image_restored_url = processed_url
    db.session.commit()

    # ✅ Trừ tín dụng
    user_package = UserPackage.query.filter(UserPackage.user_id == user.user_id).first()
    if user_package:
        user_package.user_package_credits -= 2
        db.session.commit()

    return jsonify({"message": "Xóa vật thể thành công!", "processed_url": processed_url})


# ✅ **Hàm chờ kết quả từ Replicate**
def check_prediction_until_complete(prediction_url):
    headers = {"Authorization": f"Bearer {REPLICATE_API_TOKEN}"}

    while True:
        try:
            response = requests.get(prediction_url, headers=headers)
            response_data = response.json()

            if response.status_code == 200:
                status = response_data["status"]
                if status == "succeeded":
                    return response_data["output"]
                elif status == "failed":
                    return None
                else:
                    time.sleep(3)
            else:
                return None

        except requests.RequestException as e:
            return None


# ✅ **API: Lấy danh sách ảnh**
@lama_blueprint.route("/images", methods=["GET"])
@jwt_required()
def get_user_images():
    user_id = get_jwt_identity()
    images = Image.query.filter_by(user_id=user_id).all()

    image_list = [{
        "original_url": img.image_original_url,
        "processed_url": img.image_restored_url or ""  # ✅ Trả về chuỗi rỗng thay vì `null`
    } for img in images]

    return jsonify({"images": image_list})


# ✅ **Trang hiển thị xóa vật thể**
@lama_blueprint.route("/", methods=["GET"])
@jwt_required()
def lama_page():
    return render_template("lama.html")
