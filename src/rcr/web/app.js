// UI: chon device -> chon app -> doc baseline -> nap file testcase.
// App KHONG debuggable van hien trong danh sach (kem nhan) de tester hieu vi sao
// khong chon duoc, thay vi app bien mat khong ro ly do.

const $ = (id) => document.getElementById(id);
let state = { serial: '', package: '' };

function banner(msg, kind = 'info') {
  const el = $('banner');
  el.textContent = msg;
  el.className = `banner ${kind}`;
  el.classList.remove('hidden');
}
function clearBanner() { $('banner').classList.add('hidden'); }

async function api(path, opts) {
  const res = await fetch(path, opts);
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(body.detail || `HTTP ${res.status}`);
  return body;
}

async function loadDevices() {
  try {
    const { devices } = await api('/api/devices');
    const sel = $('device');
    if (!devices.length) {
      sel.innerHTML = '<option value="">-- khong thay may nao --</option>';
      banner('Khong thay device. Cam cap, bat USB debugging, bam Allow tren may.\n' +
             'Kiem tra: adb devices phai hien "device" (khong phai "unauthorized").', 'warn');
      return;
    }
    sel.innerHTML = devices
      .map((d) => `<option value="${d.serial}" ${d.ready ? '' : 'disabled'}>` +
                  `${d.label}${d.ready ? '' : ' — ' + d.state}</option>`)
      .join('');
    const first = devices.find((d) => d.ready);
    if (first) { sel.value = first.serial; await onDevice(); }
  } catch (e) { banner(`Loi doc danh sach may: ${e.message}`, 'error'); }
}

async function onDevice() {
  state.serial = $('device').value;
  state.package = '';
  const sel = $('package');
  sel.disabled = true;
  sel.innerHTML = '<option value="">-- dang tai --</option>';
  $('read').disabled = true;
  $('summary').classList.add('hidden');
  if (!state.serial) return;
  try {
    const { packages } = await api(`/api/packages?serial=${encodeURIComponent(state.serial)}`);
    const dbg = packages.filter((p) => p.debuggable);
    sel.innerHTML =
      '<option value="">-- chon app --</option>' +
      packages
        .map((p) => `<option value="${p.package}" ${p.debuggable ? '' : 'disabled'}>` +
                    `${p.package}${p.debuggable ? '' : '  (khong debuggable)'}</option>`)
        .join('');
    sel.disabled = false;
    banner(`${dbg.length}/${packages.length} app debuggable. ` +
           'App khong debuggable bi mo di: can ban APK bat `debuggable` (xin dev), ' +
           'hoac may da root.', 'info');
  } catch (e) { banner(`Loi doc danh sach app: ${e.message}`, 'error'); }
}

function onPackage() {
  state.package = $('package').value;
  $('read').disabled = !state.package;
  $('summary').classList.add('hidden');
}

function row(k, v) { return `<tr><th>${k}</th><td>${v}</td></tr>`; }

async function readBaseline() {
  clearBanner();
  $('read').disabled = true;
  $('read').textContent = 'Dang doc...';
  const qs = `serial=${encodeURIComponent(state.serial)}&package=${encodeURIComponent(state.package)}`;
  try {
    const s = await api(`/api/baseline?${qs}`, { method: 'POST' });
    const mirrors = Object.entries(s.mirrors);
    $('sumTable').innerHTML =
      row('Package', `<code>${s.package}</code>`) +
      row('Firebase appId', `<code>${s.app_id}</code>`) +
      row('So key remote config', `<b>${s.keys}</b>`) +
      row('Key bi mirror', `<b>${s.mirrored_keys}</b> (${s.keys ? Math.round(s.mirrored_keys * 100 / s.keys) : 0}%)`) +
      row('File mirror (se patch)',
          mirrors.length
            ? mirrors.map(([n, c]) => `<code>${n}</code> <span class="tag">${c} key</span>`).join('<br>')
            : '<i>khong co</i>') +
      row('File vsl_* bo qua (state noi bo app)',
          s.non_mirror_files.length
            ? s.non_mirror_files.map((n) => `<code>${n}</code>`).join('<br>')
            : '<i>khong co</i>') +
      row('Duong ghi', `<code>${s.write_mode}</code>`) +
      row('Template version', s.template_version || '<i>?</i>') +
      row('Moc fetch cuoi', s.fetch_time_ms
            ? new Date(s.fetch_time_ms).toLocaleString('vi-VN')
            : '<i>?</i>');
    $('summary').classList.remove('hidden');
    await loadKeys();
  } catch (e) {
    banner(e.message, 'error');
  } finally {
    $('read').disabled = false;
    $('read').textContent = 'Doc baseline';
  }
}

async function loadKeys() {
  const qs = `serial=${encodeURIComponent(state.serial)}&package=${encodeURIComponent(state.package)}` +
             `&q=${encodeURIComponent($('q').value)}`;
  try {
    const { total, keys } = await api(`/api/baseline/keys?${qs}`);
    $('keyCount').textContent =
      `${total} key khop` + (keys.length < total ? ` — hien ${keys.length} dau` : '');
    $('keyTable').innerHTML =
      '<tr><th>Key</th><th>Gia tri</th><th>Mirror</th></tr>' +
      keys.map((k) =>
        `<tr><td class="key">${k.key}</td><td class="val">${escapeHtml(k.value)}</td>` +
        `<td>${k.mirrored ? '<span class="tag mirror">co</span>' : ''}</td></tr>`).join('');
  } catch (e) { banner(`Loi doc key: ${e.message}`, 'error'); }
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"]/g, (c) =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]);
}

async function loadTestcases() {
  const f = $('tcFile').files[0];
  if (!f) return;
  const form = new FormData();
  form.append('file', f);
  const qs = `serial=${encodeURIComponent(state.serial)}&package=${encodeURIComponent(state.package)}`;
  $('loadTc').disabled = true;
  $('loadTc').textContent = 'Dang nap...';
  try {
    const r = await api(`/api/testcases?${qs}`, { method: 'POST', body: form });
    $('tcCount').textContent =
      `${r.file}: ${r.total} case, ${r.runnable} case chay duoc ` +
      `(loc bang ${r.whitelist_size} key that cua app)`;
    $('tcTable').innerHTML =
      '<tr><th>#</th><th>Case</th><th>Test Data</th><th>Key se dat</th><th>Ghi chu</th></tr>' +
      r.cases.map((c) => {
        const ov = Object.entries(c.overrides)
          .map(([k, v]) => `<code>${escapeHtml(k)}</code>=<b>${escapeHtml(v)}</b>`).join('<br>');
        const note = c.needs_human
          ? `<span class="tag warn">can nguoi</span> ${escapeHtml(c.needs_human)}`
          : (c.ignored.length ? `<span class="tag">bo qua: ${c.ignored.join(', ')}</span>` : '');
        return `<tr class="${c.runnable ? '' : 'dim'}"><td>${c.n}</td>` +
               `<td>${escapeHtml(c.label)}</td>` +
               `<td class="val">${escapeHtml(c.test_data)}</td>` +
               `<td>${ov || '—'}</td><td>${note}</td></tr>`;
      }).join('');
  } catch (e) {
    banner(`Loi nap file testcase: ${e.message}`, 'error');
  } finally {
    $('loadTc').disabled = false;
    $('loadTc').textContent = 'Nap file testcase';
  }
}

let qTimer;
$('tcFile').onchange = () => { $('loadTc').disabled = !$('tcFile').files.length; };
$('loadTc').onclick = loadTestcases;
$('device').onchange = onDevice;
$('package').onchange = onPackage;
$('read').onclick = readBaseline;
$('q').oninput = () => { clearTimeout(qTimer); qTimer = setTimeout(loadKeys, 200); };
loadDevices();
