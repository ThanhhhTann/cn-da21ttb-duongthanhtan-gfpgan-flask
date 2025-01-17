document.addEventListener("DOMContentLoaded", function () {
    // 🖼 **Lấy thẻ canvas**
    const canvas = document.getElementById("imageCanvas");
    const maskCanvas = document.getElementById("maskCanvas");
    
    if (!canvas || !maskCanvas) {
        console.error("❌ Không tìm thấy phần tử canvas!");
        return;
    }

    const ctx = canvas.getContext("2d");
    const maskCtx = maskCanvas.getContext("2d");

    let img = null;
    let drawing = false;
    let currentTool = '';
    let brushSize = 20;

    // 🖼 **Tải ảnh lên**
    document.getElementById("imageUpload").addEventListener("change", uploadImage);
    document.getElementById("brushButton").addEventListener("click", () => currentTool = "brush");
    document.getElementById("clearButton").addEventListener("click", clearCanvas);
    document.getElementById("removeButton").addEventListener("click", removeObject);
    document.getElementById("downloadButton").addEventListener("click", downloadImage);

    // ✅ **Hàm tải ảnh lên server**
    function uploadImage() {
        let fileInput = document.getElementById("imageUpload");
        let formData = new FormData();
        formData.append("image", fileInput.files[0]);

        fetch("/lama/upload", {
            method: "POST",
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.image_id) {
                localStorage.setItem("image_id", data.image_id); // 🔹 Lưu `image_id`
                loadImageFromURL(data.image_url); // 🔹 Hiển thị ảnh lên `canvas`
            } else {
                alert("❌ Lỗi tải ảnh!");
            }
        })
        .catch(error => console.error("❌ Lỗi tải ảnh:", error));
    }

    // ✅ **Hàm hiển thị ảnh lên `canvas`**
    function loadImageFromURL(imageUrl) {
        if (!imageUrl) {
            console.error("❌ Không có URL ảnh để tải.");
            return;
        }

        img = new Image();
        img.crossOrigin = "Anonymous";  // 🔹 Cho phép tải ảnh từ nguồn khác
        img.src = imageUrl;
        
        img.onload = function () {
            loadImageToCanvas(img);
        };

        img.onerror = function () {
            console.error("❌ Lỗi tải ảnh:", imageUrl);
        };
    }

    // ✅ **Hàm vẽ mask**
    canvas.addEventListener("mousedown", () => drawing = true);
    canvas.addEventListener("mouseup", () => { drawing = false; ctx.beginPath(); maskCtx.beginPath(); });
    canvas.addEventListener("mousemove", drawMask);

    function drawMask(event) {
        if (!drawing || currentTool !== "brush") return;

        const { x, y } = getCursorPosition(event);
        ctx.strokeStyle = "rgba(255, 0, 0, 0.5)";
        ctx.lineWidth = brushSize;
        ctx.lineCap = "round";
        ctx.lineTo(x, y);
        ctx.stroke();
        ctx.beginPath();
        ctx.moveTo(x, y);

        maskCtx.fillStyle = "white";
        maskCtx.beginPath();
        maskCtx.arc(x, y, brushSize / 2, 0, Math.PI * 2);
        maskCtx.fill();
    }

    // ✅ **Hàm hiển thị ảnh trên `canvas`**
    function loadImageToCanvas(image) {
        canvas.width = image.width;
        canvas.height = image.height;
        maskCanvas.width = image.width;
        maskCanvas.height = image.height;
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.drawImage(image, 0, 0);
    }

    // ✅ **Hàm xóa nét vẽ**
    function clearCanvas() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        if (img) loadImageToCanvas(img);
        maskCtx.clearRect(0, 0, maskCanvas.width, maskCanvas.height);
    }

    // ✅ **Gửi ảnh đến API để xử lý**
    async function removeObject() {
        let imageId = localStorage.getItem("image_id");  // 🔹 Lấy `image_id` từ localStorage
        if (!imageId) {
            alert("❌ Không tìm thấy ảnh! Hãy tải lên trước.");
            return;
        }

        const maskData = maskCanvas.toDataURL();

        const response = await fetch("/lama/remove-object", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ image_id: imageId, mask_data: maskData }) // 🔹 Đảm bảo `image_id` gửi đi hợp lệ
        });

        const data = await response.json();
        if (data.processed_url) {
            img = new Image();
            img.src = data.processed_url;
            img.onload = () => loadImageToCanvas(img);
            loadUserImages(); // 🔹 Cập nhật danh sách ảnh sau khi xử lý
        } else {
            alert("❌ Lỗi khi xóa vật thể!");
        }
    }

    // ✅ **Hàm tải ảnh xuống**
    function downloadImage() {
        const link = document.createElement("a");
        link.download = "edited_image.png";
        link.href = canvas.toDataURL();
        link.click();
    }

    // ✅ **Lấy danh sách ảnh đã xử lý**
    async function loadUserImages() {
        const response = await fetch("/lama/images", { method: "GET" });
        const data = await response.json();

        const imageList = document.getElementById("imageList");
        imageList.innerHTML = "";

        data.images.forEach(imgData => {
            const container = document.createElement("div");
            container.className = "image-container";

            const originalImg = document.createElement("img");
            originalImg.src = imgData.original_url;
            originalImg.alt = "Ảnh gốc";

            const processedImg = document.createElement("img");
            processedImg.src = imgData.processed_url;
            processedImg.alt = "Ảnh đã xử lý";

            container.appendChild(originalImg);
            container.appendChild(processedImg);
            imageList.appendChild(container);
        });
    }

    // ✅ **Hàm lấy tọa độ con trỏ chuột**
    function getCursorPosition(event) {
        const rect = canvas.getBoundingClientRect();
        return {
            x: (event.clientX - rect.left) * (canvas.width / rect.width),
            y: (event.clientY - rect.top) * (canvas.height / rect.height)
        };
    }

    // ✅ **Gọi `loadUserImages()` khi trang tải xong**
    loadUserImages();
});
