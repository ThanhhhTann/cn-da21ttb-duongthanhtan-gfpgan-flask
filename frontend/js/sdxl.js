function generateImage() {
    const prompt = document.getElementById("prompt").value;
    const aspectRatio = document.getElementById("aspectRatio").value;
    let width = 1280, height = 1280;

    switch (aspectRatio) {
        case "16:9": width = 1280; height = 720; break;
        case "3:2": width = 1280; height = 853; break;
        case "4:5": width = 1024; height = 1280; break;
    }

    if (!prompt) {
        alert("Vui lòng nhập mô tả ảnh!");
        return;
    }

    fetch("/sdxl/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            prompt: prompt,
            width: width,
            height: height,
            num_outputs: 1,
            scheduler: "K_EULER",
            num_inference_steps: 4,
            guidance_scale: 0
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.images) {
            loadUserImages(); // Cập nhật danh sách ảnh sau khi tạo thành công
        } else {
            alert("Lỗi khi tạo ảnh!");
        }
    })
    .catch(error => console.error("Lỗi tạo ảnh:", error));
}

// ✅ **Lấy danh sách ảnh đã tạo**
function loadUserImages() {
    fetch("/sdxl/images", { method: "GET" })
    .then(response => response.json())
    .then(data => {
        const imageList = document.getElementById("imageList");
        imageList.innerHTML = "";

        data.images.forEach(imgData => {
            const img = document.createElement("img");
            img.src = imgData.original_url;
            img.width = 300;
            imageList.appendChild(img);
        });
    })
    .catch(error => console.error("Lỗi tải danh sách ảnh:", error));
}

// ✅ **Gọi danh sách ảnh khi trang tải xong**
document.addEventListener("DOMContentLoaded", loadUserImages);
