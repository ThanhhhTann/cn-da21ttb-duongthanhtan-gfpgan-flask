function uploadImage() {
    let fileInput = document.getElementById("imageUpload");
    let formData = new FormData();
    formData.append("image", fileInput.files[0]);

    fetch("/gfpgan/upload", {
        method: "POST",
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.image_url) {
            document.getElementById("originalImage").src = data.image_url;
            localStorage.setItem("image_id", data.image_id);
        } else {
            alert("Lỗi tải ảnh!");
        }
    });
}

function restoreImage() {
    let imageId = localStorage.getItem("image_id");

    fetch("/gfpgan/restore", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ image_id: imageId })
    })
    .then(response => response.json())
    .then(data => {
        if (data.restored_url) {
            document.getElementById("restoredImage").src = data.restored_url;
        } else {
            alert("Lỗi khi khôi phục ảnh!");
        }
    });
}

function loadImages() {
    fetch("/gfpgan/list")
    .then(response => response.json())
    .then(data => {
        let imageListDiv = document.getElementById("imageList");
        imageListDiv.innerHTML = ""; // Xóa nội dung cũ

        data.images.forEach(img => {
            let imgContainer = document.createElement("div");
            imgContainer.style.marginBottom = "20px";

            let originalImg = document.createElement("img");
            originalImg.src = img.original_url;
            originalImg.width = 150;

            let restoredImg = document.createElement("img");
            restoredImg.src = img.restored_url ? img.restored_url : "";
            restoredImg.width = 150;
            restoredImg.style.marginLeft = "20px";

            let label = document.createElement("p");
            label.textContent = img.restored_url ? "✅ Đã khôi phục" : "⏳ Đang chờ khôi phục";

            imgContainer.appendChild(originalImg);
            imgContainer.appendChild(restoredImg);
            imgContainer.appendChild(label);
            imageListDiv.appendChild(imgContainer);
        });
    });
}
