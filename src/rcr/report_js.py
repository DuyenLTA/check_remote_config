"""JS cua report: loc theo verdict, tim theo chu, an dong tieu de nhom rong.

Tach khoi report_html de moi file duoi 200 dong. Khong dung thu vien nao -
trang phai mo duoc khi khong co mang.

Dong tieu de nhom (`tr.ghead`) phai an theo: loc con 3 case FAIL ma van con
nguyen 4 tieu de nhom thi doc nhu moi nhom deu co case, dem nham ngay.
"""

JS = """
const rows = [...document.querySelectorAll('tr.row')];
const heads = [...document.querySelectorAll('tr.ghead')];
const btns = [...document.querySelectorAll('[data-f]')];
const sel = document.getElementById('st');
const q = document.getElementById('q');
const count = document.getElementById('count');
let filter = 'ALL';
function apply() {
  const text = q.value.trim().toLowerCase();
  let shown = 0;
  rows.forEach(r => {
    const ok = (filter === 'ALL' || r.dataset.v === filter)
      && (!text || r.dataset.q.includes(text));
    r.hidden = !ok; shown += ok ? 1 : 0;
  });
  heads.forEach(h => {
    let any = false;
    for (let n = h.nextElementSibling; n && !n.classList.contains('ghead'); n = n.nextElementSibling)
      if (!n.hidden) { any = true; break; }
    h.hidden = !any;
  });
  count.textContent = shown + '/' + rows.length + ' case';
  btns.forEach(b => b.setAttribute('aria-pressed', String(b.dataset.f === filter)));
  if (sel.value !== filter) sel.value = filter;
}
btns.forEach(b => b.addEventListener('click', () => {
  filter = (filter === b.dataset.f && b.dataset.f !== 'ALL') ? 'ALL' : b.dataset.f;
  apply();
}));
sel.addEventListener('change', () => { filter = sel.value; apply(); });
q.addEventListener('input', apply);
apply();
"""
