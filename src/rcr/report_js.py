"""JS cua report: loc theo verdict, tim, bung/thu tung case.

Tach khoi report_html de moi file duoi 200 dong. Khong dung thu vien nao -
trang phai mo duoc khi khong co mang.
"""

JS = """
const rows = [...document.querySelectorAll('.row')];
const chips = [...document.querySelectorAll('[data-f]')];
const q = document.getElementById('q'), count = document.getElementById('count');
let filter = 'ALL';
function apply() {
  const text = q.value.trim().toLowerCase();
  let shown = 0;
  rows.forEach(r => {
    const ok = (filter === 'ALL' || r.dataset.v === filter) && (!text || r.dataset.q.includes(text));
    r.hidden = !ok; shown += ok ? 1 : 0;
  });
  document.querySelectorAll('.group').forEach(g => {
    g.hidden = ![...g.querySelectorAll('.row')].some(r => !r.hidden);
  });
  count.textContent = shown + '/' + rows.length + ' case';
  chips.forEach(c => c.setAttribute('aria-pressed', String(c.dataset.f === filter)));
}
chips.forEach(c => c.addEventListener('click', () => {
  filter = (filter === c.dataset.f && c.dataset.f !== 'ALL') ? 'ALL' : c.dataset.f;
  apply();
}));
q.addEventListener('input', apply);
rows.forEach(r => r.querySelector('.rowbtn').addEventListener('click', () => r.classList.toggle('open')));
document.getElementById('expandAll').addEventListener('click', e => {
  const open = e.target.textContent === 'Mở tất cả';
  rows.forEach(r => r.classList.toggle('open', open));
  e.target.textContent = open ? 'Thu tất cả' : 'Mở tất cả';
});
apply();
"""
