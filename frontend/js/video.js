let uploadedVideoUrl = ""; // Lưu trữ URL video sau khi tải lên

// ✅ **Hàm tải video lên**
function uploadVideo() {
    let fileInput = document.getElementById("videoUpload");
    let formData = new FormData();
    formData.append("video", fileInput.files[0]);

    fetch("/video/upload", {
        method: "POST",
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.video_url) {
            uploadedVideoUrl = data.video_url;  // Lưu URL video
            let videoElement = document.getElementById("uploadedVideo");
            videoElement.src = uploadedVideoUrl;
            videoElement.style.display = "block";  // Hiển thị video
            alert("✅ Video đã tải lên thành công!");
        } else {
            alert("❌ Lỗi tải video!");
        }
    })
    .catch(error => console.error("❌ Lỗi tải video:", error));
}

// ✅ **Hàm tạo âm thanh từ video**
function generateAudio() {
    if (!uploadedVideoUrl) {
        alert("❌ Vui lòng tải video lên trước!");
        return;
    }

    const prompt = document.getElementById("prompt").value;

    fetch("/video/generate-audio", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ video_url: uploadedVideoUrl, prompt: prompt })
    })
    .then(response => response.json())
    .then(data => {
        if (data.processed_video_url) {
            let processedVideo = document.getElementById("processedVideo");
            processedVideo.src = data.processed_video_url;
            processedVideo.style.display = "block";  // Hiển thị video kết quả
            loadUserVideos(); // Cập nhật danh sách video
        } else {
            alert("❌ Lỗi khi tạo âm thanh!");
        }
    })
    .catch(error => console.error("❌ Lỗi tạo âm thanh:", error));
}

// ✅ **Hàm lấy danh sách video đã xử lý**
function loadUserVideos() {
    fetch("/video/videos", { method: "GET" })
    .then(response => response.json())
    .then(data => {
        const videoList = document.getElementById("videoList");
        videoList.innerHTML = "";

        data.videos.forEach(video => {
            const container = document.createElement("div");
            container.className = "video-container";

            const originalVideo = document.createElement("video");
            originalVideo.src = video.original_url;
            originalVideo.controls = true;

            const processedVideo = document.createElement("video");
            processedVideo.src = video.processed_url;
            processedVideo.controls = true;

            container.appendChild(originalVideo);
            container.appendChild(processedVideo);
            videoList.appendChild(container);
        });
    })
    .catch(error => console.error("❌ Lỗi tải danh sách video:", error));
}

// ✅ **Tự động tải danh sách video khi trang tải xong**
document.addEventListener("DOMContentLoaded", loadUserVideos);
