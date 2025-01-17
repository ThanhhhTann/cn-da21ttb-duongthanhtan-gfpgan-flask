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
import time
from flask_cors import CORS

# 🔹 Cấu hình Azure Storage
AZURE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
CONTAINER_NAME_ORIGINAL = "user-uploads"  # 📌 Ảnh gốc để tạo video
CONTAINER_NAME_PROCESSED = "video-no-sound"  # 📌 Video sau khi tạo
blob_service_client = BlobServiceClient.from_connection_string(AZURE_CONNECTION_STRING)

# 🔹 API Token của Replicate
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")

video01_blueprint = Blueprint("video01", __name__)
CORS(video01_blueprint)  # ✅ Cho phép tất cả origin truy cập API

# ✅ **API: Tải ảnh lên Azure Storage**
@video01_blueprint.route("/upload", methods=["POST"])
@jwt_required()
def upload_image():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    if not user:
        return jsonify({"error": "User không tồn tại!"}), 400

    file = request.files.get("image")
    if not file:
        return jsonify({"error": "Không có ảnh nào được tải lên!"}), 400

    # ✅ Tạo tên file ngẫu nhiên
    blob_name = f"{uuid.uuid4()}.jpg"

    # ✅ Upload ảnh lên Azure Storage
    blob_client = blob_service_client.get_blob_client(container=CONTAINER_NAME_ORIGINAL, blob=blob_name)
    blob_client.upload_blob(file.read(), overwrite=True)

    image_url = f"https://{blob_service_client.account_name}.blob.core.windows.net/{CONTAINER_NAME_ORIGINAL}/{blob_name}"

    return jsonify({"message": "Ảnh đã tải lên thành công!", "image_url": image_url})

# ✅ **API: Gửi prompt đến Replicate để tạo video**
@video01_blueprint.route("/generate-video", methods=["POST"])
@jwt_required()
def generate_video():
    data = request.json
    prompt = data.get("prompt")
    image_url = data.get("image_url", None)  # ✅ Nhận ảnh nếu có
    prompt_optimizer = data.get("prompt_optimizer", True)
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    if not user or not prompt:
        return jsonify({"error": "Thiếu thông tin user hoặc prompt!"}), 400

    # ✅ Kiểm tra tín dụng người dùng
    total_credits = db.session.query(
        func.coalesce(func.sum(UserPackage.user_package_credits), 0)
    ).filter(UserPackage.user_id == user.user_id).scalar()

    if total_credits < 2:
        return jsonify({"error": "Bạn không đủ tín dụng để tạo video!"}), 403

    # ✅ Gửi yêu cầu đến Replicate (truyền thêm `first_frame_image` nếu có)
    try:
        input_data = {
            "prompt": prompt,
            "prompt_optimizer": prompt_optimizer
        }

        if image_url:
            input_data["first_frame_image"] = image_url  # ✅ Truyền ảnh vào request nếu có

        output_url = replicate.run("minimax/video-01", input=input_data)

        if not output_url:
            return jsonify({"error": "Không thể tạo video từ Replicate!"}), 500

    except Exception as e:
        return jsonify({"error": f"Lỗi khi kết nối đến Replicate: {str(e)}"}), 500

    # ✅ Chờ tối đa 8 phút (480 giây) để lấy kết quả video
    start_time = time.time()
    while True:
        if time.time() - start_time > 480:
            return jsonify({"error": "Quá thời gian chờ, vui lòng thử lại sau!"}), 500

        try:
            response = requests.get(output_url, timeout=30, stream=True)
            if response.status_code == 200:
                video_data = response.content
                break
        except:
            time.sleep(10)

    # ✅ Upload video đã tạo lên Azure Storage
    blob_name = f"generated_{uuid.uuid4()}.mp4"
    processed_blob_client = blob_service_client.get_blob_client(container=CONTAINER_NAME_PROCESSED, blob=blob_name)
    processed_blob_client.upload_blob(video_data, overwrite=True)

    processed_url = f"https://{blob_service_client.account_name}.blob.core.windows.net/{CONTAINER_NAME_PROCESSED}/{blob_name}"

    # ✅ Lưu video vào database
    new_video = Video(
        user_id=user_id,
        video_original_url=image_url if image_url else None,
        video_processed_url=processed_url
    )
    db.session.add(new_video)
    db.session.commit()

    # ✅ Trừ tín dụng người dùng
    user_package = UserPackage.query.filter(UserPackage.user_id == user.user_id).first()
    if user_package:
        user_package.user_package_credits -= 2
        db.session.commit()

    return jsonify({"message": "Video đã tạo thành công!", "processed_video_url": processed_url})

# ✅ **API: Lấy danh sách video đã tạo**
@video01_blueprint.route("/videos", methods=["GET"])
@jwt_required()
def get_user_videos():
    user_id = get_jwt_identity()
    videos = Video.query.filter_by(user_id=user_id).all()

    if not videos:
        print("❌ Không tìm thấy video nào trong CSDL!")  # Debug xem API có chạy không
        return jsonify({"videos": []})

    video_list = [{
        "original_url": vid.video_original_url if vid.video_original_url else "",
        "processed_url": vid.video_processed_url if vid.video_processed_url else ""
    } for vid in videos]

    print(f"✅ Video tải lên: {video_list}")  # Debug danh sách video trả về
    return jsonify({"videos": video_list})


# ✅ **Trang hiển thị giao diện tạo video**
@video01_blueprint.route("/", methods=["GET"])
@jwt_required()
def video01_page():
    return render_template("video01.html")


