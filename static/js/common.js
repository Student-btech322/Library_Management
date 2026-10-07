async function api(path, opts = {}) {
  const init = { method: opts.method || 'GET', headers: {} };
  if (opts.form) {
    init.body = opts.form;
  } else if (opts.body !== undefined) {
    init.headers['Content-Type'] = 'application/json';
    init.body = JSON.stringify(opts.body);
  }
  const res = await fetch(path, init);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || `Request failed (${res.status})`);
  return data;
}

function esc(v) {
  return String(v ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

function toast(msg, type = '') {
  const el = document.createElement('div');
  el.className = 'toast ' + type;
  el.textContent = msg;
  document.getElementById('toast').appendChild(el);
  setTimeout(() => el.remove(), 4000);
}

function fmtDate(iso) {
  if (!iso) return '-';
  return new Date(iso + 'T00:00:00').toLocaleDateString(undefined, { day: '2-digit', month: 'short', year: 'numeric' });
}

function initials(name) {
  return (name || '?').split(/\s+/).filter(Boolean).slice(0, 2).map(w => w[0].toUpperCase()).join('');
}

function avatarHtml(s, cls = '') {
  return s.photo_url
    ? `<img class="avatar ${cls}" src="${esc(s.photo_url)}" alt="${esc(s.name)}">`
    : `<div class="avatar ${cls}">${esc(initials(s.name))}</div>`;
}

function statusBadge(st) {
  return `<span class="badge ${st}">${st[0].toUpperCase() + st.slice(1)}</span>`;
}

function debounce(fn, ms = 250) {
  let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); };
}

function openModal(id) { document.getElementById(id).classList.add('open'); }
function closeModal(id) { document.getElementById(id).classList.remove('open'); }
document.addEventListener('click', e => {
  if (e.target.classList.contains('modal-backdrop') && e.target.id !== 'scanner-modal') e.target.classList.remove('open');
  if (e.target.dataset.close) closeModal(e.target.dataset.close);
});

/* Camera / image scanner for QR codes and barcodes on ID cards and books */
const Scanner = (() => {
  let reader = null, onResult = null;
  const modal = () => document.getElementById('scanner-modal');
  const errBox = () => document.getElementById('scanner-error');
  const formats = () => {
    const F = window.Html5QrcodeSupportedFormats;
    return F ? [F.QR_CODE, F.CODE_128, F.CODE_39, F.EAN_13, F.EAN_8, F.UPC_A, F.CODABAR, F.ITF] : undefined;
  };

  function showError(msg) { errBox().textContent = msg; errBox().style.display = 'block'; }

  async function stop() {
    if (reader) {
      try { if (reader.isScanning) await reader.stop(); reader.clear(); } catch (_) {}
      reader = null;
    }
    modal().classList.remove('open');
  }

  function deliver(text) {
    const cb = onResult;
    stop().then(() => cb && cb(String(text).trim()));
  }

  async function open(title, cb) {
    onResult = cb;
    document.getElementById('scanner-title').textContent = title;
    errBox().style.display = 'none';
    modal().classList.add('open');
    reader = new Html5Qrcode('scanner-region', { formatsToSupport: formats(), verbose: false });
    try {
      await reader.start({ facingMode: 'environment' }, { fps: 10, qrbox: { width: 260, height: 180 } },
        text => deliver(text), () => {});
    } catch (e) {
      showError('Camera not available (' + (e.message || e) + '). You can upload a photo of the card instead, or type the ID.');
    }
  }

  document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('scanner-close').onclick = stop;
    document.getElementById('scanner-file').onchange = async e => {
      const file = e.target.files[0];
      e.target.value = '';
      if (!file) return;
      try {
        if (reader && reader.isScanning) await reader.stop();
        const r = reader || new Html5Qrcode('scanner-region', { formatsToSupport: formats(), verbose: false });
        reader = r;
        deliver(await r.scanFile(file, false));
      } catch (_) {
        showError('Could not read a QR code / barcode in that image. Try a clearer photo.');
      }
    };
  });

  return { open, stop };
})();
