"""Renderer cua trang report: dung danh sach case tu `const DATA` da nhung san.

Dung JS thay vi sinh san HTML tung hang vi trang co bo loc + o tim: loc bang JS
thi khong phai sinh lai trang, va file nho hon han khi co vai chuc case.

Trang van doc duoc khi khong co JS? KHONG - va do la danh doi co y: bo TC that
la 60+ case, ban HTML tinh keo theo anh chup se nang toi muc khong mo noi.
"""

JS = """
const LABEL = {PASS: "PASS", FAIL: "FAIL", BLOCKED: "BLOCKED", NA: "N/A"};
// Tu vung noi bo cua tool -> chu tester doc duoc. "noop" tren report khong noi
// duoc gi, ma no la nhan HAY GAP NHAT: phan lon buoc Action cua bo TC la buoc
// quan sat hoac buoc tool da lam xong o cho khac.
const THAOTAC = {
  tap: "bấm", swipe: "vuốt", wait: "chờ", goto: "lái qua luồng FO",
  net: "đổi trạng thái mạng", noop: "không cần thao tác",
  needs_human: "tool không tự làm được",
};
const TILE = {
  FAIL: "sai so với Expected", BLOCKED: "chưa test được",
  PASS: "đúng như Expected", NA: "ngoài phạm vi tester",
};
let filter = "ALL", q = "";
const esc = s => String(s == null ? "" : s).replace(/[&<>"]/g,
  c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[c]));
const pill = s => `<span class="pill ${s}">${LABEL[s] || s}</span>`;

function tally() {
  const el = document.getElementById("tally");
  el.innerHTML = Object.keys(TILE).map(s => {
    const n = DATA.filter(d => d.status === s).length;
    return `<button class="tile ${s}" data-f="${s}" aria-pressed="false">` +
      `<span class="num">${n}</span><span class="lab">${TILE[s]}</span></button>`;
  }).join("");
  el.querySelectorAll(".tile").forEach(b =>
    b.onclick = () => setFilter(filter === b.dataset.f ? "ALL" : b.dataset.f));
}
function todo() {
  const li = (d, txt) => `<li><button class="jump" data-n="${d.n}">#${d.n}</button>` +
    `<span>${esc(txt)}</span></li>`;
  const put = (id, rows) => document.getElementById(id).innerHTML =
    rows.length ? rows.join("") : '<li class="none">— không có —</li>';
  put("todoFail", DATA.filter(d => d.status === "FAIL").map(d => li(d, d.title)));
  put("todoBlock", DATA.filter(d => d.status === "BLOCKED").map(d => li(d, d.actual)));
  put("todoPo", DATA.filter(d => d.po).map(d => li(d, d.title)));
  document.querySelectorAll(".jump").forEach(b => b.onclick = () => openCase(+b.dataset.n));
}
function match(d) {
  if (filter !== "ALL" && d.status !== filter) return false;
  if (!q) return true;
  const hay = [d.n, d.title, d.group, d.cfg, d.actual, d.pre, ...d.expects].join(" ").toLowerCase();
  return /^\\d+$/.test(q) ? String(d.n) === q : hay.includes(q);
}
function render() {
  const list = document.getElementById("list");
  const groups = [...new Set(DATA.map(d => d.group))];
  let shown = 0;
  list.innerHTML = groups.map(g => {
    const all = DATA.filter(d => d.group === g), rows = all.filter(match);
    shown += rows.length;
    if (!rows.length) return "";
    const counts = Object.keys(TILE).map(s => [s, all.filter(d => d.status === s).length])
      .filter(([, n]) => n)
      .map(([s, n]) => `<span class="pill ${s}">${LABEL[s]} ${n}</span>`).join("");
    return `<section class="group"><div class="ghead"><h2>${esc(g)}</h2>` +
      `<div class="gcount">${counts}</div></div>` + rows.map(row).join("") + `</section>`;
  }).join("") || `<div class="card empty">Không có case nào khớp bộ lọc.</div>`;
  document.getElementById("count").textContent = `${shown} / ${DATA.length} case`;
  list.querySelectorAll(".rowbtn").forEach(b => b.onclick = () => toggle(b.closest(".row")));
}
// Ky vong va ket qua cua DUNG dong do di lien nhau: doc mot dong la biet dong
// ay dat hay khong, khong phai doi chieu hai cot danh so song song.
function expects(d) {
  return d.expects.map((e, i) => {
    const l = d.lines[i];
    return `<li><div class="exp">${l ? pill(l.s) : ""}<span>${esc(e)}</span>` +
      (l ? `<span class="why">${esc(l.r)}</span>` : "") + `</div></li>`;
  }).join("");
}
function adsTable(d) {
  if (!d.ads.length) return "";
  const rows = d.ads.map(u => `<tr><td>${esc(u.t)}</td><td class="mono">${esc(u.u)}</td>` +
    `<td class="num">${u.req}</td><td class="num">${u.load}</td><td class="num">${u.show}</td>` +
    `<td class="mono">${esc((u.keys || []).join(", "))}</td></tr>`).join("");
  return `<div class="full"><h4>Ad unit trong log</h4><table class="ads">` +
    `<thead><tr><th>Loại</th><th>Unit</th><th>Req</th><th>Load</th><th>Show</th>` +
    `<th>Vị trí</th></tr></thead><tbody>${rows}</tbody></table></div>`;
}
function shots(d) {
  const has = d.steps.filter(s => s.shot);
  if (!has.length) return "";
  return `<div class="full"><h4>Ảnh từng bước</h4><div class="shots">` + has.map(s =>
    `<figure><img loading="lazy" src="${s.shot}" alt="${esc(s.s)}">` +
    `<figcaption>#${s.n} ${esc(THAOTAC[s.k] || s.k)}</figcaption></figure>`).join("") + `</div></div>`;
}
function steps(d) {
  if (!d.steps.length) return "";
  return `<div class="full"><h4>Các bước đã lái</h4><ol>` + d.steps.map(s =>
    `<li>${esc(s.s)}<span class="why">${esc(THAOTAC[s.k] || s.k)}` +
    (s.r ? ` — ${esc(s.r)}` : "") + (s.blocked ? " · màn bị quảng cáo che" : "") +
    `</span></li>`).join("") + `</ol></div>`;
}
function row(d) {
  return `<div class="row" id="c${d.n}">
    <button class="rowbtn" aria-expanded="false" aria-controls="d${d.n}">
      <span class="n">#${d.n}</span>${pill(d.status)}
      <span class="t"><b>${esc(d.title)}` +
        (d.thieu && d.thieu.length ? ' <span class="pill FIX">thiếu điều kiện</span>' : "") +
        `</b><span>${esc(d.actual)}</span></span>
      <span class="chev" aria-hidden="true">›</span>
    </button>
    <div class="detail" id="d${d.n}">
      <div><h4>Kỳ vọng (TC) &amp; kết quả</h4><ol>${expects(d)}</ol></div>
      <div style="display:flex;flex-direction:column;gap:12px">
        <div><h4>Config đã đặt</h4><div class="box">${esc(d.cfg)}` +
          (d.ep ? `<span class="why">Ép điều kiện: ${esc(d.ep)}</span>` : "") + `</div></div>
        <div><h4>Thực tế</h4><div class="box">${esc(d.actual)}</div></div>
      </div>
      ${d.thieu && d.thieu.length ? `<div class="full fixnote"><b>Precondition chưa tạo được:</b> ` +
        esc(d.thieu.join("; ")) + ` — case chưa chạy đúng nhánh TC mô tả.</div>` : ""}
      <div class="full"><h4>Precondition (TC)</h4><div class="pre">${esc(d.pre)}</div></div>
      ${steps(d)}${adsTable(d)}${shots(d)}
    </div>
  </div>`;
}
function toggle(r, force) {
  const open = force ?? !r.classList.contains("open");
  r.classList.toggle("open", open);
  r.querySelector(".rowbtn").setAttribute("aria-expanded", open);
}
function openCase(n) {
  filter = "ALL"; q = ""; document.getElementById("q").value = ""; syncChips(); render();
  const r = document.getElementById("c" + n); if (!r) return;
  toggle(r, true); r.scrollIntoView({behavior: "smooth", block: "start"});
}
function syncChips() {
  document.querySelectorAll(".chip,.tile").forEach(
    c => c.setAttribute("aria-pressed", c.dataset.f === filter));
}
function setFilter(f) { filter = f; syncChips(); render(); }
document.querySelectorAll(".chip").forEach(c => c.onclick = () => setFilter(c.dataset.f));
document.getElementById("q").oninput = e => {
  q = e.target.value.trim().toLowerCase().replace(/^#/, ""); render();
};
document.getElementById("expandAll").onclick = e => {
  const rows = [...document.querySelectorAll(".row")];
  const open = !rows.every(r => r.classList.contains("open"));
  rows.forEach(r => toggle(r, open));
  e.target.textContent = open ? "Thu gọn tất cả" : "Mở tất cả";
};
tally(); todo(); render();
const h = location.hash.match(/^#c(\\d+)$/); if (h) openCase(+h[1]);
"""
