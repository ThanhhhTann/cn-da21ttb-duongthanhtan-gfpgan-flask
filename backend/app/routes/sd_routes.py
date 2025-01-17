from flask import Blueprint, request, jsonify, render_template
from flask_jwt_extended import jwt_required, get_jwt_identity
from backend.app.db import db
from backend.app.models import User
from azure.storage.blob import BlobServiceClient
import os
import uuid
import requests
import replicate
from flask_cors import CORS

# 🔹 Cấu hình Azure Storage
AZURE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
CONTAINER_NAME = "stable-diffusion-3-5-large"
blob_service_client = BlobServiceClient.from_connection_string(AZURE_CONNECTION_STRING)

# 🔹 API Token của Replicate
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")

sd_blueprint = Blueprint("sd", __name__)
CORS(sd_blueprint)  # Cho phép API gọi từ frontend

# ✅ **API: Gọi Stable Diffusion 3.5 để tạo ảnh**
@sd_blueprint.route("/generate", methods=["POST"])
@jwt_required()
def generate_image():
    data = request.json
    prompt = data.get("prompt", "").strip()
    aspect_ratio = data.get("aspect_ratio", "1:1")
    cfg = data.get("cfg", 4.5)
    steps = data.get("steps", 40)
    output_format = data.get("output_format", "webp")
    output_quality = data.get("output_quality", 90)
    prompt_strength = data.get("prompt_strength", 0.85)

    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User không tồn tại!"}), 400

    if not prompt:
        return jsonify({"error": "Prompt không được để trống!"}), 400

    # ✅ Gửi yêu cầu đến Replicate API
    headers = {"Authorization": f"Bearer {REPLICATE_API_TOKEN}", "Content-Type": "application/json"}
    payload = {
        "cfg": cfg,
        "steps": steps,
        "prompt": prompt,
        "aspect_ratio": aspect_ratio,
        "output_format": output_format,
        "output_quality": output_quality,
        "prompt_strength": prompt_strength,
    }

    try:
        response = replicate.run("stability-ai/stable-diffusion-3.5-large", input=payload)

        if not response:
            return jsonify({"error": "Không thể tạo ảnh từ Replicate!"}), 500

        image_url = response[0]  # ✅ URL ảnh trả về từ Replicate
        print(f"✅ Ảnh tạo thành công: {image_url}")

    except Exception as e:
        return jsonify({"error": f"Lỗi kết nối đến Replicate: {str(e)}"}), 500

    # ✅ Tải ảnh từ URL trả về
    try:
        image_data = requests.get(image_url, timeout=15).content
    except Exception as e:
        return jsonify({"error": "Không thể tải ảnh từ Replicate!"}), 500

    # ✅ Upload ảnh lên Azure Storage
    blob_name = f"generated_{uuid.uuid4()}.webp"
    blob_client = blob_service_client.get_blob_client(container=CONTAINER_NAME, blob=blob_name)
    blob_client.upload_blob(image_data, overwrite=True)

    stored_image_url = f"https://{blob_service_client.account_name}.blob.core.windows.net/{CONTAINER_NAME}/{blob_name}"

    return jsonify({"message": "Ảnh đã tạo thành công!", "image_url": stored_image_url})


# ✅ **Trang nhập prompt và hiển thị ảnh**
@sd_blueprint.route("/", methods=["GET"])
@jwt_required()
def sd_page():
    return render_template("sd.html")
