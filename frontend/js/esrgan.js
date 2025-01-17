function uploadImage() {
    let fileInput = document.getElementById("imageUpload");
    let formData = new FormData();
    formData.append("image", fileInput.files[0]);

    fetch("/esrgan/upload", {
        method: "POST",
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        document.getElementById("originalImage").src = data.image_url;
        localStorage.setItem("image_id", data.image_id);
        loadImages(); // Tải lại danh sách ảnh đã tải lên
    });
}

function enhanceImage() {
    let imageId = localStorage.getItem("image_id");
    let scale = document.getElementById("scale").value;
    let faceEnhance = document.getElementById("faceEnhance").checked;

    fetch("/esrgan/enhance", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
            image_id: imageId, 
            scale: parseInt(scale), 
            face_enhance: faceEnhance 
        })
    })
    .then(response => response.json())
    .then(data => {
        document.getElementById("enhancedImage").src = data.enhanced_url;
        loadImages(); // Cập nhật danh sách ảnh đã nâng cấp
    });
}

function loadImages() {
    fetch("/esrgan/images")
    .then(response => response.json())
    .then(data => {
        let uploadedContainer = document.getElementById("uploadedImages");
        let enhancedContainer = document.getElementById("enhancedImages");

        uploadedContainer.innerHTML = "";
        enhancedContainer.innerHTML = "";

        data.images.forEach(image => {
            let imgElem = document.createElement("img");
            imgElem.src = image.original_url;
            imgElem.width = 150;
            uploadedContainer.appendChild(imgElem);

            if (image.enhanced_url) {
                let enhancedImg = document.createElement("img");
                enhancedImg.src = image.enhanced_url;
                enhancedImg.width = 150;
                enhancedContainer.appendChild(enhancedImg);
            }
        });
    });
}
