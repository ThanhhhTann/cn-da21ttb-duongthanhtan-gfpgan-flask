// 🖼 Lưu URL ảnh đã tải lên
let uploadedImageUrl = "";

// ✅ **Hàm tải ảnh lên**
function uploadImage() {
    let fileInput = document.getElementById("imageUpload");
    let formData = new FormData();
    formData.append("image", fileInput.files[0]);

    fetch("/colorize/upload", {
        method: "POST",
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.image_url) {
            uploadedImageUrl = data.image_url;
            let imgElement = document.getElementById("uploadedImage");
            imgElement.src = uploadedImageUrl;
            imgElement.style.display = "block";
        } else {
            alert("❌ Lỗi tải ảnh!");
        }
    })
    .catch(error => console.error("❌ Lỗi tải ảnh:", error));
}

// ✅ **Hàm tô màu ảnh**
function colorizeImage() {
    fetch("/colorize/colorize", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ image_url: uploadedImageUrl })
    })
    .then(response => response.json())
    .then(data => {
        if (data.processed_image_url) {
            let processedImg = document.getElementById("processedImage");
            processedImg.src = data.processed_image_url;
            processedImg.style.display = "block";
        } else {
            alert("❌ Lỗi khi tô màu ảnh!");
        }
    })
    .catch(error => console.error("❌ Lỗi tô màu ảnh:", error));
}

// ✅ **Hàm lấy danh sách ảnh đã tô màu**
async function loadUserImages() {
    const response = await fetch("/colorize/images", { method: "GET" });
    const data = await response.json();

    const imageList = document.getElementById("imageList");
    imageList.innerHTML = "";

    data.images.forEach(imgData => {
        const container = document.createElement("div");
        container.className = "image-container";

        const originalImg = document.createElement("img");
        originalImg.src = imgData.original_url;
        originalImg.alt = "Ảnh gốc";
        originalImg.style.maxWidth = "100%";

        const processedImg = document.createElement("img");
        processedImg.src = imgData.processed_url;
        processedImg.alt = "Ảnh đã tô màu";
        processedImg.style.maxWidth = "100%";

        container.appendChild(originalImg);
        container.appendChild(processedImg);
        imageList.appendChild(container);
    });
}
