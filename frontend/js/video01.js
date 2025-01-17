let uploadedImageUrl = "";

function uploadImage() {
    let fileInput = document.getElementById("imageUpload");
    let formData = new FormData();
    formData.append("image", fileInput.files[0]);

    fetch("/video01/upload", {
        method: "POST",
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.image_url) {
            uploadedImageUrl = data.image_url; // ✅ Lưu URL ảnh vào biến toàn cục
            let imgElement = document.getElementById("uploadedImage");
            imgElement.src = uploadedImageUrl;
            imgElement.style.display = "block";
        } else {
            alert("❌ Lỗi tải ảnh!");
        }
    })
    .catch(error => console.error("❌ Lỗi tải ảnh:", error));
}

// ✅ **Hàm tạo video từ prompt**
function generateVideo() {
    const prompt = document.getElementById("prompt").value;

    fetch("/video01/generate-video", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            prompt: prompt,
            image_url: uploadedImageUrl // ✅ Truyền ảnh đã tải lên nếu có
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.processed_video_url) {
            let processedVideo = document.getElementById("processedVideo");
            processedVideo.src = data.processed_video_url;
            processedVideo.style.display = "block";
        } else {
            alert("❌ Lỗi khi tạo video!");
        }
    })
    .catch(error => console.error("❌ Lỗi tạo video:", error));
}

document.addEventListener("DOMContentLoaded", function () {
    loadUserVideos(); // ✅ Gọi API ngay khi trang load
});

function loadUserVideos() {
    fetch("/video01/videos", { method: "GET" })
        .then(response => response.json())
        .then(data => {
            const videoList = document.getElementById("videoList");
            videoList.innerHTML = ""; // Xóa danh sách cũ trước khi hiển thị mới

            if (!data.videos || data.videos.length === 0) {
                videoList.innerHTML = "<p>Chưa có video nào được tạo.</p>";
                return;
            }

            data.videos.forEach(vid => {
                const container = document.createElement("div");
                container.className = "video-container";

                if (vid.original_url) {
                    const originalVideo = document.createElement("video");
                    originalVideo.src = vid.original_url;
                    originalVideo.controls = true;
                    originalVideo.width = 300;
                    container.appendChild(originalVideo);
                }

                if (vid.processed_url) {
                    const processedVideo = document.createElement("video");
                    processedVideo.src = vid.processed_url;
                    processedVideo.controls = true;
                    processedVideo.width = 300;
                    container.appendChild(processedVideo);
                }

                videoList.appendChild(container);
            });
        })
        .catch(error => console.error("❌ Lỗi khi tải danh sách video:", error));
}
