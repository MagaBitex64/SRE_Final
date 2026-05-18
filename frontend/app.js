let currentUser = JSON.parse(localStorage.getItem('sre_user') || 'null');
let currentToken = localStorage.getItem('sre_token') || null;

function goTo(page) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
  document.getElementById('page-' + page).classList.add('active');
  document.querySelectorAll('.nav-link').forEach(l => {
    if (l.textContent.toLowerCase().includes(page)) l.classList.add('active');
  });
  if (page === 'home')     checkHealth();
  if (page === 'products') loadProducts();
  if (page === 'orders')   loadOrders();
  if (page === 'profile')  loadProfile();
  if (page === 'reviews')  loadReviews();
  if (page === 'audit')    loadAudit();
}

function updateNavUser() {
  if (currentUser) {
    document.getElementById('nav-user').textContent = '👤 ' + currentUser.username;
    document.getElementById('nav-auth-btn').textContent = 'Account';
  } else {
    document.getElementById('nav-user').textContent = 'Not logged in';
    document.getElementById('nav-auth-btn').textContent = 'Login';
  }
}
updateNavUser();

function showRes(id, data) {}

const SERVICES = [
  { name: 'auth-service',         path: '/api/auth/health' },
  { name: 'product-service',      path: '/api/products/health' },
  { name: 'order-service',        path: '/api/orders/health' },
  { name: 'user-profile-service', path: '/api/users/health' },
  { name: 'review-service',       path: '/api/reviews/health' },
  { name: 'audit-service',        path: '/api/audit/health' },
];

async function checkHealth() {
  const tbody = document.getElementById('health-table');
  tbody.innerHTML = '';
  for (const s of SERVICES) {
    let ok = false;
    try { const r = await fetch(s.path); ok = r.ok; } catch {}
    tbody.innerHTML += `<tr>
      <td>${s.name}</td>
      <td style="color:#8b949e">${s.path}</td>
      <td><span class="dot ${ok ? 'ok' : 'err'}"></span>${ok ? 'Healthy' : 'Unhealthy'}</td>
    </tr>`;
  }
}

async function doRegister() {
  const r = await fetch('/api/auth/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      username: document.getElementById('reg-user').value,
      password: document.getElementById('reg-pass').value
    })
  });
  showRes('register', await r.json());
}

async function doLogin() {
  const r = await fetch('/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      username: document.getElementById('log-user').value,
      password: document.getElementById('log-pass').value
    })
  });
  const data = await r.json();
  if (data.token) {
    currentToken = data.token;
    const payload = JSON.parse(atob(data.token.split('.')[1]));
    currentUser = { id: payload.sub, username: payload.username };
    localStorage.setItem('sre_token', currentToken);
    localStorage.setItem('sre_user', JSON.stringify(currentUser));
    updateNavUser();
    fetch('/api/audit/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: parseInt(currentUser.id),
        action: 'LOGIN',
        service: 'auth-service',
        details: currentUser.username + ' logged in'
      })
    });
  }
  showRes('login', data);
}

function doLogout() {
  currentToken = null;
  currentUser = null;
  localStorage.removeItem('sre_token');
  localStorage.removeItem('sre_user');
  updateNavUser();
  showRes('login', { message: 'Logged out' });
}

async function loadProducts() {
  const r = await fetch('/api/products/');
  const data = await r.json();
  document.getElementById('products-table').innerHTML = data.map(p => `<tr>
    <td>${p.id}</td><td>${p.name}</td><td>$${p.price}</td><td>${p.stock}</td>
  </tr>`).join('');
}

async function createProduct() {
  const r = await fetch('/api/products/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      name: document.getElementById('p-name').value,
      description: document.getElementById('p-desc').value,
      price: parseFloat(document.getElementById('p-price').value),
      stock: parseInt(document.getElementById('p-stock').value)
    })
  });
  showRes('product', await r.json());
  loadProducts();
}

async function loadOrders() {
  const r = await fetch('/api/orders/');
  const data = await r.json();
  document.getElementById('orders-table').innerHTML = data.map(o => `<tr>
    <td>${o.id}</td><td>${o.user_id}</td><td>${o.product_id}</td>
    <td>${o.quantity}</td><td>$${o.total_price}</td>
    <td><span class="tag">${o.status}</span></td>
  </tr>`).join('');
}

async function createOrder() {
  const r = await fetch('/api/orders/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      user_id: parseInt(document.getElementById('o-uid').value),
      product_id: parseInt(document.getElementById('o-pid').value),
      quantity: parseInt(document.getElementById('o-qty').value),
      total_price: parseFloat(document.getElementById('o-price').value)
    })
  });
  showRes('order', await r.json());
  loadOrders();
}

async function loadProfile() {
  const locked = document.getElementById('profile-locked');
  const content = document.getElementById('profile-content');
  if (!currentUser) {
    locked.style.display = 'block';
    content.style.display = 'none';
    return;
  }
  locked.style.display = 'none';
  content.style.display = 'block';
  const r = await fetch('/api/users/' + currentUser.id);
  if (r.ok) {
    const data = await r.json();
    document.getElementById('profile-data').innerHTML = `
      <table>
        <tr><th>Field</th><th>Value</th></tr>
        <tr><td>User ID</td><td>${data.user_id}</td></tr>
        <tr><td>Full Name</td><td>${data.full_name || '—'}</td></tr>
        <tr><td>Email</td><td>${data.email || '—'}</td></tr>
        <tr><td>Phone</td><td>${data.phone || '—'}</td></tr>
      </table>`;
    document.getElementById('pr-fullname').value = data.full_name || '';
    document.getElementById('pr-email').value = data.email || '';
    document.getElementById('pr-phone').value = data.phone || '';
  } else {
    document.getElementById('profile-data').innerHTML = '<p style="color:#8b949e">No profile yet. Create one below.</p>';
  }
}

async function saveProfile() {
  if (!currentUser) return;
  const body = {
    user_id: parseInt(currentUser.id),
    full_name: document.getElementById('pr-fullname').value,
    email: document.getElementById('pr-email').value,
    phone: document.getElementById('pr-phone').value
  };
  let r = await fetch('/api/users/' + currentUser.id, {
    method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body)
  });
  if (!r.ok) r = await fetch('/api/users/', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body)
  });
  showRes('profile', await r.json());
  loadProfile();
}

async function loadReviews() {
  const r = await fetch('/api/reviews/');
  const data = await r.json();
  document.getElementById('reviews-table').innerHTML = data.map(rv => `<tr>
    <td>${rv.id}</td><td>${rv.user_id}</td><td>${rv.product_id}</td>
    <td>${'⭐'.repeat(rv.rating)}</td><td>${rv.comment || '—'}</td>
  </tr>`).join('');
}

async function createReview() {
  const r = await fetch('/api/reviews/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      user_id: parseInt(document.getElementById('rv-uid').value),
      product_id: parseInt(document.getElementById('rv-pid').value),
      rating: parseInt(document.getElementById('rv-rating').value),
      comment: document.getElementById('rv-comment').value
    })
  });
  showRes('review', await r.json());
  loadReviews();
}

async function loadAudit() {
  const r = await fetch('/api/audit/');
  const data = await r.json();
  document.getElementById('audit-table').innerHTML = data.map(a => `<tr>
    <td>${a.id}</td><td>${a.user_id || '—'}</td>
    <td><span class="tag">${a.action}</span></td>
    <td>${a.service}</td><td>${a.details || '—'}</td>
    <td style="color:#8b949e;font-size:0.75rem">${new Date(a.created_at).toLocaleString()}</td>
  </tr>`).join('');
}

async function createAudit() {
  const r = await fetch('/api/audit/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      user_id: parseInt(document.getElementById('au-uid').value) || null,
      action: document.getElementById('au-action').value,
      service: document.getElementById('au-service').value,
      details: document.getElementById('au-details').value
    })
  });
  showRes('audit', await r.json());
  loadAudit();
}

checkHealth();