// frontend/js/register.js
document.getElementById('registerForm').onsubmit = async function(event) {
    event.preventDefault();  

    const formData = new FormData(this);

    const response = await fetch('/auth/register', {
        method: 'POST',
        body: formData
    });

    if (response.redirected) {
        alert('Đăng ký thành công! Chuyển hướng đến trang đăng nhập.');
        window.location.href = response.url;
    } else {
        alert('Đăng ký thất bại. Vui lòng thử lại!');
    }
};
