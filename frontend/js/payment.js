function payWithPaypal(packageId, packagePrice) {
    paypal.Buttons({
        createOrder: function(data, actions) {
            return actions.order.create({
                purchase_units: [{
                    amount: { value: packagePrice }
                }]
            });
        },
        onApprove: function(data, actions) {
            return actions.order.capture().then(function(details) {
                fetch("/payment/process", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        package_id: packageId,
                        paypal_order_id: data.orderID
                    })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.message) {
                        alert(data.message);
                        window.location.href = "/";
                    } else {
                        alert("Lỗi khi thanh toán!");
                    }
                });
            });
        }
    }).render(`#paypal-button-${packageId}`);
}
