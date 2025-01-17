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

# 🔹 Cấu hình Azure Storage
AZURE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
CONTAINER_NAME = "sdxl-lightning-4step"
blob_service_client = BlobServiceClient.from_connection_string(AZURE_CONNECTION_STRING)

# 🔹 API Token của Replicate
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")

sdxl_blueprint = Blueprint("sdxl", __name__)

# ✅ **API: Tạo ảnh bằng SDXL Lightning 4-step**
@sdxl_blueprint.route("/generate", methods=["POST"])
@jwt_required()
def generate_image():
    data = request.json
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    if not user:
        return jsonify({"error": "User không tồn tại!"}), 400

    prompt = data.get("prompt")
    negative_prompt = data.get("negative_prompt", "worst quality, low quality")
    width = data.get("width", 1280)
    height = data.get("height", 1280)
    num_outputs = data.get("num_outputs", 1)
    scheduler = data.get("scheduler", "K_EULER")
    num_inference_steps = data.get("num_inference_steps", 4)
    guidance_scale = data.get("guidance_scale", 0)

    if not prompt:
        return jsonify({"error": "Vui lòng nhập prompt để tạo ảnh!"}), 400

    # ✅ Kiểm tra tín dụng
    total_credits = db.session.query(
        func.coalesce(func.sum(UserPackage.user_package_credits), 0)
    ).filter(UserPackage.user_id == user.user_id).scalar()

    if total_credits < 2:
        return jsonify({"error": "Bạn không đủ tín dụng để tạo ảnh!"}), 403

    # ✅ Gửi prompt đến API Replicate
    try:
        output_urls = replicate.run(
            "bytedance/sdxl-lightning-4step:5599ed30703defd1d160a25a63321b4dec97101d98b4674bcc56e41f62f35637",
            input={
                "width": width,
                "height": height,
                "prompt": prompt,
                "scheduler": scheduler,
                "num_outputs": num_outputs,
                "guidance_scale": guidance_scale,
                "negative_prompt": negative_prompt,
                "num_inference_steps": num_inference_steps
            }
        )

        if not output_urls:
            return jsonify({"error": "Không thể tạo ảnh từ Replicate!"}), 500

        generated_images = []

        for img_url in output_urls:
            response = requests.get(img_url, timeout=15, stream=True)
            response.raise_for_status()
            image_data = response.content

            # ✅ Upload ảnh lên Azure Storage
            blob_name = f"sdxl_{uuid.uuid4()}.jpg"
            blob_client = blob_service_client.get_blob_client(container=CONTAINER_NAME, blob=blob_name)
            blob_client.upload_blob(image_data, overwrite=True)

            # ✅ URL ảnh trên Azure
            azure_image_url = f"https://{blob_service_client.account_name}.blob.core.windows.net/{CONTAINER_NAME}/{blob_name}"
            generated_images.append(azure_image_url)

            # ✅ Lưu ảnh vào database
            new_image = Image(user_id=user_id, image_original_url=azure_image_url)
            db.session.add(new_image)

        # ✅ Trừ tín dụng
        user_package = UserPackage.query.filter(UserPackage.user_id == user.user_id).first()
        if user_package:
            user_package.user_package_credits -= 2
            db.session.commit()

        return jsonify({"message": "Tạo ảnh thành công!", "images": generated_images})

    except Exception as e:
        return jsonify({"error": f"Lỗi kết nối đến Replicate: {str(e)}"}), 500


# ✅ **API: Lấy danh sách ảnh đã tạo**
@sdxl_blueprint.route("/images", methods=["GET"])
@jwt_required()
def get_user_images():
    user_id = get_jwt_identity()
    images = Image.query.filter_by(user_id=user_id).order_by(Image.image_created_at.desc()).limit(10).all()

    image_list = [{
        "original_url": img.image_original_url
    } for img in images]

    return jsonify({"images": image_list})


# ✅ **Trang giao diện tạo ảnh SDXL**
@sdxl_blueprint.route("/", methods=["GET"])
@jwt_required()
def sdxl_page():
    return render_template("sdxl.html")
