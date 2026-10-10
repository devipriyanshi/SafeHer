const API = (() => {
  const BASE = '';

  function getToken() { return localStorage.getItem('sh_token'); }
  function setToken(t) { localStorage.setItem('sh_token', t); }
  function clearToken() { localStorage.removeItem('sh_token'); }

  function headers(extra = {}) {
    const h = { 'Content-Type': 'application/json', ...extra };
    const t = getToken();
    if (t) h['Authorization'] = `Bearer ${t}`;
    return h;
  }

  async function request(method, path, body = null) {
    const opts = { method, headers: headers() };
    if (body) opts.body = JSON.stringify(body);
    const res = await fetch(BASE + path, opts);
    if (res.status === 204) return null;
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw { status: res.status, detail: data.detail || 'Request failed' };
    return data;
  }

  return {
    getToken, setToken, clearToken,
    get:    (p)    => request('GET',    p),
    post:   (p, b) => request('POST',   p, b),
    put:    (p, b) => request('PUT',    p, b),
    delete: (p)    => request('DELETE', p),
  };
})();

function requireAuth() {
  if (!API.getToken()) { window.location.href = '/static/login.html'; }
}

function logout() {
  API.clearToken();
  window.location.href = '/static/login.html';
}

function showAlert(id, msg, type = 'error') {
  const el = document.getElementById(id);
  if (!el) return;
  el.className = `sh-alert sh-alert-${type} show`;
  el.textContent = msg;
  setTimeout(() => el.classList.remove('show'), 4000);
}

function fmtDate(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' });
}
