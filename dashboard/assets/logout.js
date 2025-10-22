// assets/logout.js
(function(){
  document.addEventListener('click', function(e){
    try {
      // cari tombol logout (bisa klik ikon atau button)
      const btn = e.target.closest ? e.target.closest('#logout-btn') : (e.target.id === 'logout-btn' ? e.target : null);
      if (!btn) return;
      e.preventDefault();
      btn.disabled = true;

      fetch('/auth/logout', {
        method: 'POST',
        credentials: 'same-origin',   // gunakan 'include' jika frontend & backend beda origin
        headers: { 'Content-Type': 'application/json' }
      })
      .then(async (resp) => {
        // coba baca JSON (tidak kritikal)
        try { await resp.json().catch(()=>{}); } catch(e){}
        // redirect ke login apapun hasilnya
        window.location.href = '/login';
      })
      .catch((err) => {
        console.error('logout error', err);
        // tetap redirect supaya UX konsisten
        window.location.href = '/login';
      })
      .finally(() => {
        try { btn.disabled = false; } catch(e){}
      });
    } catch(err) {
      console.error('logout handler error', err);
    }
  }, true);
})();
