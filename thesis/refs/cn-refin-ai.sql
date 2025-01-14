-- Tạo bảng users
CREATE TABLE users (
    user_id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_username VARCHAR(50) NOT NULL UNIQUE,
    user_email VARCHAR(100) NOT NULL UNIQUE,
    user_password_hash VARCHAR(255),
    user_role VARCHAR(20) CHECK (user_role IN ('admin', 'user')) DEFAULT 'user',
    user_created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tạo bảng packages
CREATE TABLE packages (
    package_id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    package_name VARCHAR(50) NOT NULL UNIQUE,
    package_price DECIMAL(10, 2) NOT NULL,
    package_credits INTEGER NOT NULL,
    package_description TEXT,
    package_created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    package_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tạo bảng user_packages
CREATE TABLE user_packages (
    user_package_id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES users(user_id),
    package_id UUID REFERENCES packages(package_id),
    user_package_credits INTEGER NOT NULL,
    user_package_purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_package_expired_at TIMESTAMP,
    user_package_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tạo bảng images (lưu trữ ảnh)
CREATE TABLE images (
    image_id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES users(user_id),
    image_original_url VARCHAR(255) NOT NULL,
    image_restored_url VARCHAR(255),
    image_status VARCHAR(20) CHECK (image_status IN ('pending', 'completed', 'failed')) DEFAULT 'pending',
    image_credits_used INTEGER DEFAULT 0,
    image_created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    image_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tạo bảng videos (lưu trữ video)
CREATE TABLE videos (
    video_id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES users(user_id),
    video_original_url VARCHAR(255) NOT NULL,
    video_processed_url VARCHAR(255),
    video_status VARCHAR(20) CHECK (video_status IN ('pending', 'processing', 'completed', 'failed')) DEFAULT 'pending',
    video_credits_used INTEGER DEFAULT 0,
    video_created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    video_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tạo bảng sessions (quản lý phiên hoạt động)
CREATE TABLE sessions (
    session_id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES users(user_id),
    session_token VARCHAR(255) NOT NULL,
    ip_address VARCHAR(50),
    device_info VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expired_at TIMESTAMP,
    session_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tạo bảng logs (ghi log hoạt động)
CREATE TABLE logs (
    log_id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES users(user_id),
    action_type VARCHAR(100),
    action_details TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    log_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tạo bảng payments (thanh toán)
CREATE TABLE payments (
    payment_id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES users(user_id),
    payment_amount DECIMAL(10, 2) NOT NULL,
    payment_currency VARCHAR(10) DEFAULT 'USD',
    payment_method VARCHAR(50) NOT NULL,
    payment_status VARCHAR(20) CHECK (payment_status IN ('pending', 'completed', 'failed')) DEFAULT 'pending',
    payment_created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    payment_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ========================================
-- ✅ Tạo trigger function cập nhật tự động
-- ========================================
CREATE OR REPLACE FUNCTION update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.user_updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ========================================
-- ✅ Gán trigger cho tất cả các bảng cần cập nhật
-- ========================================
-- Cập nhật cho bảng users
CREATE TRIGGER trigger_update_users
BEFORE UPDATE ON users
FOR EACH ROW
EXECUTE FUNCTION update_timestamp();

-- Cập nhật cho bảng packages
CREATE TRIGGER trigger_update_packages
BEFORE UPDATE ON packages
FOR EACH ROW
EXECUTE FUNCTION update_timestamp();

-- Cập nhật cho bảng user_packages
CREATE TRIGGER trigger_update_user_packages
BEFORE UPDATE ON user_packages
FOR EACH ROW
EXECUTE FUNCTION update_timestamp();

-- Cập nhật cho bảng images
CREATE TRIGGER trigger_update_images
BEFORE UPDATE ON images
FOR EACH ROW
EXECUTE FUNCTION update_timestamp();

-- Cập nhật cho bảng videos
CREATE TRIGGER trigger_update_videos
BEFORE UPDATE ON videos
FOR EACH ROW
EXECUTE FUNCTION update_timestamp();

-- Cập nhật cho bảng sessions
CREATE TRIGGER trigger_update_sessions
BEFORE UPDATE ON sessions
FOR EACH ROW
EXECUTE FUNCTION update_timestamp();

-- Cập nhật cho bảng logs
CREATE TRIGGER trigger_update_logs
BEFORE UPDATE ON logs
FOR EACH ROW
EXECUTE FUNCTION update_timestamp();

-- Cập nhật cho bảng payments
CREATE TRIGGER trigger_update_payments
BEFORE UPDATE ON payments
FOR EACH ROW
EXECUTE FUNCTION update_timestamp();
