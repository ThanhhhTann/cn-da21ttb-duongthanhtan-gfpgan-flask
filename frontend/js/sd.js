function generateImage() {
    let prompt = document.getElementById("promptInput").value.trim();
    let aspectRatio = document.getElementById("aspectRatio").value;

    if (!prompt) {
        alert("Vui lòng nhập prompt để tạo ảnh!");
        return;
    }

    let requestData = {
        prompt: prompt,
        aspect_ratio: aspectRatio,
        cfg: 4.5,
        steps: 40,
        output_format: "webp",
        output_quality: 90,
        prompt_strength: 0.85
    };

    fetch("/sd/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(requestData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.image_url) {
            document.getElementById("generatedImage").src = data.image_url;
        } else {
            alert("Lỗi tạo ảnh: " + data.error);
        }
    })
    .catch(error => console.error("Lỗi tạo ảnh:", error));
}
