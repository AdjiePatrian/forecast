// assets/login.js — hanya aktif di /login
(function(){
  if (!window.location || !window.location.pathname) return;
  // sesuaikan jika route login berbeda, misal '/login' atau '/login/'
  if (!window.location.pathname.startsWith('/login')) {
    return; // tidak jalankan script di halaman lain
  }

  // --- sisanya: listener normal seperti sebelumnya ---
  async function doLogin(username, password, alertDiv){
    try {
      const res = await fetch('/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'same-origin',
        body: JSON.stringify({ username, password })
      });
      const data = await res.json().catch(()=>({}));
      if (res.ok && data.success) {
        window.location.href = '/forecasting';
      } else {
        const err = data.error || data.msg || ('HTTP ' + res.status);
        if (alertDiv) alertDiv.innerText = 'Login gagal: ' + err;
      }
    } catch (err) {
      if (alertDiv) alertDiv.innerText = 'Gagal menghubungi server: ' + err;
      console.error('fetch error', err);
    }
  }

  document.addEventListener('click', function(e){
    const tgt = e.target;
    const btn = tgt && tgt.closest ? tgt.closest('#login-submit') : (tgt && tgt.id === 'login-submit' ? tgt : null);
    if (!btn) return;
    e.preventDefault();

    const usernameEl = document.getElementById('login-username');
    const passwordEl = document.getElementById('login-password');
    const alertDiv = document.getElementById('login-alert');

    const username = usernameEl ? usernameEl.value : null;
    const password = passwordEl ? passwordEl.value : null;

    if (!username || !password) {
      if (alertDiv) alertDiv.innerText = "Username dan password diperlukan.";
      return;
    }

    btn.disabled = true;
    doLogin(username, password, alertDiv).finally(()=> { try { btn.disabled = false; } catch(e){} });
  }, true);

  document.addEventListener('keydown', function(e){
    if (e.key === 'Enter') {
      const active = document.activeElement;
      if (active && (active.id === 'login-username' || active.id === 'login-password')) {
        e.preventDefault();
        const submitBtn = document.getElementById('login-submit');
        if (submitBtn) submitBtn.click();
      }
    }
  });
})();
