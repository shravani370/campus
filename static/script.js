// Cart management
let cart = JSON.parse(localStorage.getItem('cart')) || [];

// Update cart display
function updateCart() {
  const cartIcon = document.getElementById('cart-icon');
  if (cartIcon) cartIcon.textContent = `Cart (${cart.length})`;

  const cartItems = document.getElementById('cart-items');
  if (cartItems) {
    cartItems.innerHTML = cart.map(item => `<p>${item.name} - $${(item.price / 100).toFixed(2)}</p>`).join('');
  }

  const total = document.getElementById('total');
  if (total) {
    const sum = cart.reduce((acc, item) => acc + item.price, 0);
    total.textContent = (sum / 100).toFixed(2);
  }

  const cartSummary = document.getElementById('cart-summary');
  if (cartSummary) {
    cartSummary.innerHTML = cart.map(item => `<p>${item.name} - $${(item.price / 100).toFixed(2)}</p>`).join('');
  }
}

// Add to cart with animation
document.querySelectorAll('.add-to-cart-btn').forEach(btn => {
  btn.addEventListener('click', (e) => {
    const item = {
      id: e.target.dataset.id,
      name: e.target.dataset.name,
      price: parseInt(e.target.dataset.price)
    };
    cart.push(item);
    localStorage.setItem('cart', JSON.stringify(cart));
    updateCart();

    // Animate cart icon
    const cartIcon = document.getElementById('cart-icon');
    if (cartIcon) {
      cartIcon.classList.add('bounce');
      setTimeout(() => cartIcon.classList.remove('bounce'), 500);
    }
  });
});

// Payment handling (Stripe)
if (document.getElementById('card-element')) {
  const stripe = Stripe('your-publishable-key'); // Replace with your publishable key
  const elements = stripe.elements();
  const cardElement = elements.create('card');
  cardElement.mount('#card-element');

  document.getElementById('checkout-btn').addEventListener('click', async () => {
    const amount = cart.reduce((acc, item) => acc + item.price, 0);
    if (amount === 0) return alert('Cart is empty!');

    showSpinner();
    try {
      const response = await fetch('/create-payment-intent', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ amount }),
      });
      const { clientSecret, error } = await response.json();

      if (error) throw new Error(error);

      const { error: confirmError } = await stripe.confirmCardPayment(clientSecret, {
        payment_method: { card: cardElement },
      });

      if (confirmError) {
        alert(`Payment failed: ${confirmError.message}`);
      } else {
        alert('Payment successful!');
        cart = [];
        localStorage.setItem('cart', JSON.stringify(cart));
        window.location.href = '/';
      }
    } catch (err) {
      alert(`Error: ${err.message}`);
    } finally {
      hideSpinner();
    }
  });
}

function showSpinner() {
  const spinner = document.getElementById('loading-spinner');
  if (spinner) spinner.style.display = 'block';
}

function hideSpinner() {
  const spinner = document.getElementById('loading-spinner');
  if (spinner) spinner.style.display = 'none';
}

// Initialize
document.addEventListener('DOMContentLoaded', updateCart);