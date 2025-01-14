document.getElementById('loginForm').onsubmit = async function(event) {
    event.preventDefault();  

    const formData = new FormData(this);

    const response = await fetch('/auth/login', {
        method: 'POST',
        body: formData,
        credentials: 'include'  // Đảm bảo gửi token qua cookie
    });

    if (response.redirected) {
        alert('Đăng nhập thành công!');
        window.location.href = response.url;
    } else {
        alert('Đăng nhập thất bại!');
    }
};
