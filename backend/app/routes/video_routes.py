from flask import Blueprint, request, jsonify, render_template
from backend.app.db import db
from backend.app.models import User, Video, UserPackage
from flask_jwt_extended import jwt_required, get_jwt_identity
from azure.storage.blob import BlobServiceClient
import os
import uuid
import requests
import replicate
from sqlalchemy.sql import func
from io import BytesIO

# 🔹 Cấu hình Azure Storage
AZURE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
CONTAINER_NAME_UPLOADS = "user-uploads-video"  # 🔹 Video do người dùng tải lên
CONTAINER_NAME_PROCESSED = "video-sound"  # 🔹 Video đã xử lý có âm thanh
blob_service_client = BlobServiceClient.from_connection_string(AZURE_CONNECTION_STRING)

# 🔹 API Token của Replicate
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")

video_blueprint = Blueprint("video", __name__)

# ✅ **API: Tải video lên Azure Storage**
@video_blueprint.route("/upload", methods=["POST"])
@jwt_required()
def upload_video():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    if not user:
        return jsonify({"error": "User không tồn tại!"}), 400

    file = request.files.get("video")
    if not file:
        return jsonify({"error": "Không có file nào được tải lên!"}), 400

    # Tạo tên file ngẫu nhiên
    blob_name = f"{uuid.uuid4()}.mp4"

    # ✅ Upload video lên Azure Storage (user-uploads-video)
    blob_client = blob_service_client.get_blob_client(container=CONTAINER_NAME_UPLOADS, blob=blob_name)
    blob_client.upload_blob(file.read(), overwrite=True)

    video_url = f"https://{blob_service_client.account_name}.blob.core.windows.net/{CONTAINER_NAME_UPLOADS}/{blob_name}"

    print(f"✅ Video đã tải lên: {video_url}")  # ✅ Debug URL video

    return jsonify({"message": "Video đã tải lên thành công!", "video_url": video_url})


# ✅ **API: Xử lý video và tạo âm thanh**
@video_blueprint.route("/generate-audio", methods=["POST"])
@jwt_required()
def generate_audio():
    data = request.json
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    if not user:
        return jsonify({"error": "User không tồn tại!"}), 400

    video_url = data.get("video_url")  # URL video từ Azure Storage
    prompt = data.get("prompt", "")
    duration = data.get("duration", 8)
    num_steps = data.get("num_steps", 25)
    cfg_strength = data.get("cfg_strength", 4.5)
    negative_prompt = data.get("negative_prompt", "music")

    if not video_url:
        return jsonify({"error": "Vui lòng tải video lên trước!"}), 400

    # ✅ Kiểm tra tín dụng
    total_credits = db.session.query(
        func.coalesce(func.sum(UserPackage.user_package_credits), 0)
    ).filter(UserPackage.user_id == user.user_id).scalar()

    if total_credits < 2:
        return jsonify({"error": "Bạn không đủ tín dụng để tạo âm thanh!"}), 403

    # ✅ Gửi video đến API Replicate
    try:
        output_audio_url = replicate.run(
            "zsxkib/mmaudio:4b9f801a167b1f6cc2db6ba7ffdeb307630bf411841d4e8300e63ca992de0be9",
            input={
                "seed": -1,
                "video": video_url,
                "prompt": prompt,
                "duration": duration,
                "num_steps": num_steps,
                "cfg_strength": cfg_strength,
                "negative_prompt": negative_prompt
            }
        )

        if not output_audio_url:
            return jsonify({"error": "Không thể tạo âm thanh từ Replicate!"}), 500

        # ✅ Tải video đã xử lý từ URL kết quả
        response = requests.get(output_audio_url, timeout=15, stream=True)
        response.raise_for_status()
        processed_video_data = response.content

        # ✅ Lưu video đã xử lý vào Azure Storage (video-sound)
        processed_blob_name = f"processed_{uuid.uuid4()}.mp4"
        processed_blob_client = blob_service_client.get_blob_client(container=CONTAINER_NAME_PROCESSED, blob=processed_blob_name)
        processed_blob_client.upload_blob(processed_video_data, overwrite=True)

        processed_video_url = f"https://{blob_service_client.account_name}.blob.core.windows.net/{CONTAINER_NAME_PROCESSED}/{processed_blob_name}"

        # ✅ Lưu vào database
        new_video = Video(user_id=user_id, video_original_url=video_url, video_processed_url=processed_video_url)
        db.session.add(new_video)

        # ✅ Trừ tín dụng
        user_package = UserPackage.query.filter(UserPackage.user_id == user.user_id).first()
        if user_package:
            user_package.user_package_credits -= 2
            db.session.commit()

        return jsonify({"message": "Tạo âm thanh thành công!", "processed_video_url": processed_video_url})

    except Exception as e:
        return jsonify({"error": f"Lỗi kết nối đến Replicate: {str(e)}"}), 500


# ✅ **API: Lấy danh sách video đã xử lý**
@video_blueprint.route("/videos", methods=["GET"])
@jwt_required()
def get_user_videos():
    user_id = get_jwt_identity()
    videos = Video.query.filter_by(user_id=user_id).order_by(Video.video_created_at.desc()).limit(10).all()

    video_list = [{
        "original_url": video.video_original_url,
        "processed_url": video.video_processed_url
    } for video in videos]

    return jsonify({"videos": video_list})


# ✅ **Trang giao diện xử lý video**
@video_blueprint.route("/", methods=["GET"])
@jwt_required()
def video_page():
    return render_template("video.html")
