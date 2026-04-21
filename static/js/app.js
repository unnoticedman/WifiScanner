/* ─── UTILS ─────────────────────────────────── */
function $(id) { return document.getElementById(id); }
function $q(sel, root = document) { return root.querySelector(sel); }
function $qa(sel, root = document) { return Array.from(root.querySelectorAll(sel)); }

let toastTimer;
function toast(msg, type = '') {
  const el = $('toast');
  el.textContent = msg;
  el.className = `show ${type}`;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { el.className = ''; }, 3500);
}

async function apiFetch(path, opts = {}) {
  const res = await fetch(path, opts);
  return res.json();
}

function signalClass(pct) {
  if (pct >= 80) return 's4';
  if (pct >= 55) return 's3';
  if (pct >= 30) return 's2';
  return 's1';
}

function signalBar(pct) {
  return `<div class="signal-bar ${signalClass(pct)}">
    <span></span><span></span><span></span><span></span>
  </div>`;
}

function secBadge(sec) {
  const map = {
    safe: ['✓', 'safe', 'Segura'],
    warning: ['⚠', 'warning', 'WEP (débil)'],
    danger: ['✕', 'danger', 'Abierta'],
    moderate: ['~', 'moderate', 'WPA'],
    unknown: ['?', 'unknown', 'Desconocida'],
  };
  const [icon, cls, label] = map[sec] || map.unknown;
  return `<span class="badge ${cls}">${icon} ${label}</span>`;
}

function bandPill(band) {
  return band === '5 GHz'
    ? `<span class="band-5">5 GHz</span>`
    : `<span class="band-24">2.4 GHz</span>`;
}

function copyToClipboard(text) {
  navigator.clipboard.writeText(text)
    .then(() => toast('Copiado al portapapeles', 'success'))
    .catch(() => toast('No se pudo copiar', 'error'));
}

/* ─── TABS ──────────────────────────────────── */
const tabEls = $qa('.tab');
const paneEls = $qa('.tab-pane');

tabEls.forEach(btn => {
  btn.addEventListener('click', () => {
    tabEls.forEach(t => t.classList.remove('active'));
    paneEls.forEach(p => p.classList.remove('active'));
    btn.classList.add('active');
    $(`pane-${btn.dataset.tab}`).classList.add('active');

    if (btn.dataset.tab === 'overview') loadOverview();
  });
});

/* ─── OVERVIEW ──────────────────────────────── */
async function loadOverview() {
  const conn = $('conn-card');
  conn.innerHTML = '<div class="loading-state"><div class="spinner"></div> Detectando conexión...</div>';

  const r = await apiFetch('/api/connection');
  if (!r.ok || !r.data.ssid) {
    conn.innerHTML = '<div class="empty"><div class="empty-icon">📡</div><div class="empty-title">Sin conexión WiFi activa</div><div class="empty-sub">Conéctate a una red para ver la información</div></div>';
    return;
  }

  const d = r.data;
  const sig = parseInt(d.signal) || 0;

  conn.innerHTML = `
    <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:16px;flex-wrap:wrap;">
      <div>
        <div style="font-size:11px;text-transform:uppercase;letter-spacing:.8px;color:var(--text-faint);margin-bottom:4px">Red conectada</div>
        <div class="connection-ssid">${escHtml(d.ssid || '')}</div>
        <div style="margin-top:6px;display:flex;align-items:center;gap:8px;">
          ${secBadge(d.auth?.toLowerCase().includes('wpa2') || d.auth?.toLowerCase().includes('wpa3') ? 'safe' : 'unknown')}
          ${d.state ? `<span style="font-size:12px;color:var(--success)">● ${escHtml(d.state)}</span>` : ''}
        </div>
      </div>
      <div style="display:flex;align-items:center;gap:8px;">
        ${signalBar(sig)}
        <span style="font-family:var(--mono);font-size:18px;font-weight:700;color:var(--primary)">${sig}%</span>
      </div>
    </div>
    <div class="connection-meta">
      ${metaItem('BSSID', d.bssid || '—')}
      ${metaItem('Canal', d.channel || '—')}
      ${metaItem('Radio', d.radio_type || '—')}
      ${metaItem('Auth', d.auth || '—')}
      ${metaItem('Rx', d.rx_rate || '—')}
      ${metaItem('Tx', d.tx_rate || '—')}
    </div>
  `;

  // Quick stats
  const [nr, dr] = await Promise.all([
    apiFetch('/api/networks'),
    apiFetch('/api/devices'),
  ]);

  const nets = nr.ok ? nr.data.length : 0;
  const devs = dr.ok ? dr.data.length : 0;

  $('stat-nets').textContent = nets;
  $('stat-devs').textContent = devs;
  $('stat-sig').textContent = sig + '%';
  $('stat-ch').textContent = d.channel || '—';
}

function metaItem(k, v) {
  return `<div class="meta-item"><div class="meta-key">${k}</div><div class="meta-val mono">${escHtml(String(v))}</div></div>`;
}

function escHtml(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

/* ─── NETWORKS ──────────────────────────────── */
let networksData = [];
let sortCol = 'signal', sortDir = -1;

async function loadNetworks() {
  const wrap = $('networks-body');
  wrap.innerHTML = '<tr><td colspan="7"><div class="loading-state"><div class="spinner"></div> Escaneando redes...</div></td></tr>';
  $('networks-error').style.display = 'none';

  const r = await apiFetch('/api/networks');
  if (!r.ok) {
    $('networks-error').textContent = r.error;
    $('networks-error').style.display = 'block';
    wrap.innerHTML = '';
    return;
  }

  networksData = r.data;
  $('net-count').textContent = `${networksData.length} redes`;
  renderNetworks();
}

function renderNetworks() {
  const data = [...networksData].sort((a, b) => {
    let va = a[sortCol], vb = b[sortCol];
    if (typeof va === 'string') va = va.toLowerCase();
    if (typeof vb === 'string') vb = vb.toLowerCase();
    return va < vb ? sortDir : va > vb ? -sortDir : 0;
  });

  const wrap = $('networks-body');
  if (!data.length) {
    wrap.innerHTML = '<tr><td colspan="7"><div class="empty"><div class="empty-icon">📡</div><div class="empty-title">Sin redes detectadas</div></td></tr>';
    return;
  }

  wrap.innerHTML = data.map(n => `
    <tr>
      <td><strong>${escHtml(n.ssid)}</strong></td>
      <td class="mono" style="font-size:11px;color:var(--text-dim)">${escHtml(n.bssid)}</td>
      <td>
        <div style="display:flex;align-items:center;gap:8px;">
          ${signalBar(n.signal)}
          <span style="font-family:var(--mono);font-size:12px">${n.signal}%</span>
        </div>
      </td>
      <td>${n.channel > 0 ? n.channel : '—'} ${n.channel > 0 ? bandPill(n.band) : ''}</td>
      <td>${secBadge(n.security)}</td>
      <td style="color:var(--text-dim);font-size:12px">${escHtml(n.auth || '—')}</td>
      <td style="color:var(--text-dim);font-size:12px">${escHtml(n.radio_type || '—')}</td>
    </tr>
  `).join('');
}

$qa('thead th[data-sort]').forEach(th => {
  th.addEventListener('click', () => {
    const col = th.dataset.sort;
    if (sortCol === col) sortDir *= -1;
    else { sortCol = col; sortDir = -1; }
    renderNetworks();
  });
});

$('btn-scan-networks').addEventListener('click', loadNetworks);

/* ─── MINI BAR CHART (no deps) ──────────────── */
function drawBarChart(canvas, labels, values, colors) {
  const dpr = window.devicePixelRatio || 1;
  const cssW = canvas.parentElement.offsetWidth || 680;
  const cssH = 260;
  canvas.width = cssW * dpr;
  canvas.height = cssH * dpr;
  canvas.style.width = cssW + 'px';
  canvas.style.height = cssH + 'px';

  const ctx = canvas.getContext('2d');
  ctx.scale(dpr, dpr);

  const pad = { top: 28, right: 16, bottom: 38, left: 38 };
  const W = cssW - pad.left - pad.right;
  const H = cssH - pad.top - pad.bottom;
  const maxVal = Math.max(...values, 1);
  const n = labels.length;
  const slotW = W / n;
  const barW = Math.max(slotW * 0.6, 8);
  const barOff = (slotW - barW) / 2;

  // Horizontal grid lines
  for (let i = 0; i <= maxVal; i++) {
    const y = pad.top + H - (i / maxVal) * H;
    ctx.strokeStyle = '#1a3356';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(pad.left, y);
    ctx.lineTo(pad.left + W, y);
    ctx.stroke();
    ctx.fillStyle = '#475569';
    ctx.font = `10px Inter, sans-serif`;
    ctx.textAlign = 'right';
    ctx.textBaseline = 'middle';
    ctx.fillText(i, pad.left - 5, y);
  }

  // Bars
  values.forEach((val, i) => {
    const bh = val > 0 ? Math.max((val / maxVal) * H, 4) : 0;
    const x = pad.left + i * slotW + barOff;
    const y = pad.top + H - bh;
    const r = Math.min(5, barW / 2);

    if (bh > 0) {
      ctx.fillStyle = colors[i];
      ctx.beginPath();
      ctx.moveTo(x + r, y);
      ctx.lineTo(x + barW - r, y);
      ctx.arcTo(x + barW, y, x + barW, y + r, r);
      ctx.lineTo(x + barW, y + bh);
      ctx.lineTo(x, y + bh);
      ctx.lineTo(x, y + r);
      ctx.arcTo(x, y, x + r, y, r);
      ctx.closePath();
      ctx.fill();

      // Value above bar
      ctx.fillStyle = '#e2e8f0';
      ctx.font = `bold 12px Inter, sans-serif`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'bottom';
      ctx.fillText(val, x + barW / 2, y - 3);
    }

    // X label
    ctx.fillStyle = '#94a3b8';
    ctx.font = `10px "JetBrains Mono", monospace`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'top';
    ctx.fillText(labels[i], x + barW / 2, pad.top + H + 6);
  });
}

/* ─── CHANNELS ──────────────────────────────── */
async function loadChannels() {
  $('channels-content').innerHTML = '<div class="loading-state"><div class="spinner"></div> Analizando canales...</div>';

  const r = await apiFetch('/api/channels');
  if (!r.ok) {
    $('channels-content').innerHTML = `<div class="error-banner" style="display:block">${escHtml(r.error)}</div>`;
    return;
  }

  const d = r.data;
  const dist = d.distribution || {};
  const channels = Object.keys(dist).map(Number).sort((a, b) => a - b);
  const counts = channels.map(c => dist[c]);
  const maxCount = Math.max(...counts, 1);

  const colors = counts.map(v => {
    if (v === maxCount) return 'rgba(239,68,68,0.85)';
    if (v > maxCount / 2) return 'rgba(245,158,11,0.85)';
    return 'rgba(34,197,94,0.85)';
  });

  $('channels-content').innerHTML = `
    <div class="stack">
      <div style="display:flex;gap:16px;flex-wrap:wrap;">
        <div class="recommendation" style="flex:1;min-width:200px">
          <div class="rec-icon">📡</div>
          <div>
            <div class="rec-title">Mejor canal 2.4 GHz</div>
            <div class="rec-sub">Canal <strong style="color:var(--primary);font-size:18px">${d.best_24ghz}</strong> — menos congestionado</div>
          </div>
        </div>
        <div class="recommendation" style="flex:1;min-width:200px">
          <div class="rec-icon">🚀</div>
          <div>
            <div class="rec-title">Mejor canal 5 GHz</div>
            <div class="rec-sub">Canal <strong style="color:var(--primary);font-size:18px">${d.best_5ghz}</strong> — menos congestionado</div>
          </div>
        </div>
        <div class="recommendation" style="flex:1;min-width:200px">
          <div class="rec-icon">🔥</div>
          <div>
            <div class="rec-title">Canal más saturado</div>
            <div class="rec-sub">Canal <strong style="color:var(--danger);font-size:18px">${d.most_congested || '—'}</strong>${d.most_congested ? ' — ' + dist[d.most_congested] + ' redes' : ''}</div>
          </div>
        </div>
      </div>
      <div class="card">
        <div class="card-title">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
          Distribución de redes por canal
        </div>
        <div class="chart-wrap"><canvas id="channel-chart"></canvas></div>
      </div>
    </div>
  `;

  const canvas = $('channel-chart');
  if (canvas && channels.length) {
    drawBarChart(canvas, channels.map(c => `Ch ${c}`), counts, colors);
  } else if (canvas) {
    canvas.parentElement.innerHTML = '<div class="empty"><div class="empty-icon">📊</div><div class="empty-title">Sin datos de canal disponibles</div></div>';
  }
}

$('btn-scan-channels').addEventListener('click', loadChannels);

/* ─── DEVICES ───────────────────────────────── */
async function loadDevices() {
  const wrap = $('devices-body');
  wrap.innerHTML = '<tr><td colspan="5"><div class="loading-state"><div class="spinner"></div> Descubriendo dispositivos...</div></td></tr>';
  $('devices-error').style.display = 'none';

  const r = await apiFetch('/api/devices');
  if (!r.ok) {
    $('devices-error').textContent = r.error;
    $('devices-error').style.display = 'block';
    wrap.innerHTML = '';
    return;
  }

  const devices = r.data;
  $('dev-count').textContent = `${devices.length} dispositivos`;

  if (!devices.length) {
    wrap.innerHTML = '<tr><td colspan="5"><div class="empty"><div class="empty-icon">🔍</div><div class="empty-title">No se detectaron dispositivos</div><div class="empty-sub">Intenta desde una red conectada</div></div></td></tr>';
    return;
  }

  wrap.innerHTML = devices.map((d, i) => `
    <tr>
      <td style="color:var(--text-faint);font-family:var(--mono);font-size:11px">${i + 1}</td>
      <td><strong class="mono">${escHtml(d.ip)}</strong></td>
      <td class="mono" style="font-size:12px;color:var(--text-dim)">${escHtml(d.mac)}</td>
      <td style="color:var(--text-dim);font-size:12px">${escHtml(d.hostname || '—')}</td>
      <td>
        ${d.gateway ? '<span class="badge gateway">🌐 Gateway</span>' : ''}
        ${d.type === 'dynamic' ? '<span style="font-size:11px;color:var(--text-faint)">dinámica</span>' : '<span style="font-size:11px;color:var(--text-faint)">estática</span>'}
      </td>
    </tr>
  `).join('');
}

$('btn-scan-devices').addEventListener('click', loadDevices);

/* ─── MAC TOOLS ─────────────────────────────── */
let macInfo = null;

async function loadMac() {
  $('mac-content').innerHTML = '<div class="loading-state"><div class="spinner"></div> Cargando información de MAC...</div>';

  const r = await apiFetch('/api/mac');
  if (!r.ok) {
    $('mac-content').innerHTML = `<div class="error-banner" style="display:block">${escHtml(r.error)}</div>`;
    return;
  }

  macInfo = r.data;
  renderMac();
}

function renderMac() {
  const d = macInfo;
  const spoofedTag = d.is_spoofed ? '<span class="spoofed-tag">🎭 Spoofed</span>' : '<span class="badge safe">✓ Original</span>';

  $('mac-content').innerHTML = `
    <div class="stack">
      <div class="card">
        <div class="card-title">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>
          Adaptador: ${escHtml(d.adapter_name)}
          <span style="margin-left:8px">${spoofedTag}</span>
        </div>

        <div class="stack">
          <div>
            <div style="font-size:11px;text-transform:uppercase;letter-spacing:.8px;color:var(--text-faint);margin-bottom:8px">MAC Actual</div>
            <div class="mac-display">
              <div class="mac-block">
                <div class="mac-label">MAC Actual</div>
                <div id="display-current">${escHtml(d.current_mac || '—')}</div>
              </div>
              <button class="mac-copy" onclick="copyToClipboard('${escHtml(d.current_mac || '')}')">
                <svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
                Copiar
              </button>
            </div>
          </div>

          <div>
            <div style="font-size:11px;text-transform:uppercase;letter-spacing:.8px;color:var(--text-faint);margin-bottom:8px">MAC Original (hardware)</div>
            <div class="mac-display" style="color:var(--success);text-shadow:0 0 20px rgba(34,197,94,.2)">
              <div class="mac-block">
                <div class="mac-label">MAC Original</div>
                <div>${escHtml(d.original_mac || '—')}</div>
              </div>
              <button class="mac-copy" onclick="copyToClipboard('${escHtml(d.original_mac || '')}')">
                <svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
                Copiar
              </button>
            </div>
          </div>

          <div id="mac-error" class="error-banner"></div>

          <div class="btn-row">
            <button class="btn btn-primary" id="btn-randomize">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="16 3 21 3 21 8"/><line x1="4" y1="20" x2="21" y2="3"/><polyline points="21 16 21 21 16 21"/><line x1="15" y1="15" x2="21" y2="21"/></svg>
              Aleatorizar MAC
            </button>
            <button class="btn btn-success" id="btn-restore" ${!d.is_spoofed ? 'disabled' : ''}>
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/></svg>
              Restaurar Original
            </button>
            <button class="btn btn-outline" id="btn-preview-mac">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
              Previsualizar
            </button>
          </div>

          <div id="preview-mac" style="display:none;padding:12px;background:var(--surface);border:1px dashed var(--border-bright);border-radius:8px;font-family:var(--mono);color:var(--text-dim);font-size:14px">
            Siguiente MAC aleatoria: <strong id="preview-val" style="color:var(--primary)"></strong>
          </div>
        </div>
      </div>

      <div class="card" id="mac-history-card" style="${d.history?.length ? '' : 'display:none'}">
        <div class="card-title">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
          Historial de cambios (${d.change_count} cambios)
        </div>
        <div class="history-list" id="mac-history">
          ${(d.history || []).slice().reverse().map(h => `
            <div class="history-item">
              <span class="history-mac">${escHtml(h.mac)}</span>
              <span class="history-time">${escHtml(h.timestamp)}</span>
            </div>
          `).join('')}
        </div>
      </div>

      <div class="card" style="border-color:rgba(245,158,11,.3)">
        <div class="card-title" style="color:var(--warning)">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
          Aviso Legal
        </div>
        <p style="font-size:12px;color:var(--text-dim);line-height:1.7">
          El cambio de dirección MAC es una herramienta legítima de privacidad y ciberseguridad.
          Úsala únicamente en redes y dispositivos de tu propiedad o con autorización explícita.
          Esta función requiere <strong>privilegios de Administrador</strong> y puede no ser compatible con todos los adaptadores.
          La MAC original queda guardada y puedes restaurarla en cualquier momento.
        </p>
      </div>
    </div>
  `;

  $('btn-randomize').addEventListener('click', doRandomizeMac);
  $('btn-restore').addEventListener('click', doRestoreMac);
  $('btn-preview-mac').addEventListener('click', previewMac);
}

async function doRandomizeMac() {
  const btn = $('btn-randomize');
  btn.disabled = true;
  btn.innerHTML = '<div class="spinner"></div> Cambiando...';
  $('mac-error').style.display = 'none';

  const r = await apiFetch('/api/mac/randomize', { method: 'POST' });
  btn.disabled = false;
  btn.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="16 3 21 3 21 8"/><line x1="4" y1="20" x2="21" y2="3"/><polyline points="21 16 21 21 16 21"/><line x1="15" y1="15" x2="21" y2="21"/></svg> Aleatorizar MAC`;

  if (!r.ok) {
    $('mac-error').textContent = r.error;
    $('mac-error').style.display = 'block';
    toast(r.error, 'error');
    return;
  }

  toast(`MAC cambiada a ${r.data.new_mac}`, 'success');
  await loadMac();
}

async function doRestoreMac() {
  const btn = $('btn-restore');
  btn.disabled = true;
  btn.innerHTML = '<div class="spinner"></div> Restaurando...';
  $('mac-error').style.display = 'none';

  const r = await apiFetch('/api/mac/restore', { method: 'POST' });
  btn.disabled = false;
  btn.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/></svg> Restaurar Original`;

  if (!r.ok) {
    $('mac-error').textContent = r.error;
    $('mac-error').style.display = 'block';
    toast(r.error, 'error');
    return;
  }

  toast(`MAC restaurada: ${r.data.restored_mac}`, 'success');
  await loadMac();
}

async function previewMac() {
  const r = await apiFetch('/api/mac/preview');
  if (!r.ok) return;
  const box = $('preview-mac');
  $('preview-val').textContent = r.data.mac;
  box.style.display = 'block';
}

/* ─── INIT ──────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  loadOverview();

  // Set active tab handlers for lazy loading
  tabEls.forEach(btn => {
    btn.addEventListener('click', () => {
      const tab = btn.dataset.tab;
      if (tab === 'mac') loadMac();
    });
  });
});
