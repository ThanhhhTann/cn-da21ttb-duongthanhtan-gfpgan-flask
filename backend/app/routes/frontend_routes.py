# app/routes_frontend.py
from flask import Blueprint, send_from_directory
from pathlib import Path

# [1] Khởi tạo fronend_bp theo cấu trúc Blueprint
frontend_bp = Blueprint('frontend_bp', __name__)

# [1] Khởi tạo routes để lấy đường dẫn fronend, vì muốn hoạt động được thì các file ngoài backend phải đky thông qua routes
@frontend_bp.route('/frontend/<path:filename>')
def frontend_static(filename):
    # Tính toán đường dẫn tuyệt đối đến thư mục frontend
    frontend_path = Path(__file__).resolve().parents[3] / 'frontend'
    file_path = frontend_path / filename
    print(f"Serving {filename} from {frontend_path}")
    if not file_path.exists():
        print(f"File {filename} not found in {frontend_path}")
        return "File not found", 404
    return send_from_directory(frontend_path, filename)
