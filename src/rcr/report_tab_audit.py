"""Tab "Check ID ads" nhung trang audit day du vao report (Next-Gen + TC) -> mot file report duy nhat.

Trang audit co <style>/<script> rieng (bien :root, nut loc) nen nhung bang `<iframe srcdoc>` de CSS/JS
khong dam nhau voi report. sandbox chi cho `allow-scripts` (khong same-origin) -> nut loc cua trang
audit van chay, nhung khong cham duoc vao report. Tab dung mau `currentColor`/rgba nen hop ca hai
khung CSS (sang + toi) cua hai loai report. Khong co audit -> van hien tab, noi ro "chua check".
"""

from __future__ import annotations

import html
import shutil
from pathlib import Path

from . import audit_tom_tat

BAN_SAO = "audit.html"                 # ten ban sao trong thu muc luot (Next-Gen)
MAX_BAO = 9 * 1024 * 1024              # report + audit nhung vuot muc nay -> chi giu khoi tom tat
_E = html.escape

CSS = """<style>
.rt-bar{display:flex;gap:4px;border-bottom:1px solid rgba(128,128,128,.35)}
.rt-tab{font:inherit;font-weight:500;background:none;border:0;border-bottom:3px solid transparent;color:inherit;
opacity:.65;padding:8px 16px;cursor:pointer}
.rt-tab:hover{opacity:.9}.rt-tab:focus-visible{outline:2px solid currentColor;outline-offset:-2px}
.rt-tab[aria-selected="true"]{opacity:1;font-weight:600;border-bottom-color:currentColor}
.rt-panel{display:flex;flex-direction:column;gap:20px}.rt-panel[hidden]{display:none}
.rt-frame{width:100%;height:85vh;min-height:560px;border:1px solid rgba(128,128,128,.35);border-radius:10px;background:#fff}
</style>"""

JS = """<script>(function(){var t=[].slice.call(document.querySelectorAll('.rt-tab'));
function sel(b){t.forEach(function(x){var on=x===b;x.setAttribute('aria-selected',on?'true':'false');x.tabIndex=on?0:-1;
document.getElementById(x.getAttribute('aria-controls')).hidden=!on});b.focus()}
t.forEach(function(b,i){b.addEventListener('click',function(){sel(b)});
b.addEventListener('keydown',function(e){var k=e.key;if(k==='ArrowRight'||k==='ArrowLeft'){e.preventDefault();
sel(t[(i+(k==='ArrowRight'?1:t.length-1))%t.length])}})})})();</script>"""


def luu_ban_sao(tt: dict | None, thu_muc: Path) -> dict | None:
    """Copy trang audit vao thu muc luot de dung lai report van thay dung noi dung; `trang` tro toi ban sao."""
    if not tt or not tt.get("trang"):
        return tt
    try:
        dich = Path(thu_muc) / BAN_SAO
        if Path(tt["trang"]).resolve() != dich.resolve():
            shutil.copyfile(tt["trang"], dich)
        return {**tt, "trang": str(dich)}
    except OSError:
        return tt


def _doc_trang(tt: dict | None) -> str | None:
    """Noi dung trang de nhung; chi nhan file trong thu muc out cua audit hoac ban sao `audit.html`."""
    if not tt or not tt.get("trang"):
        return None
    try:
        f = Path(tt["trang"]).resolve()
        if f.name != BAN_SAO:
            f.relative_to(audit_tom_tat.thu_muc_out().resolve())
        if not f.is_file() or f.stat().st_size > audit_tom_tat.MAX_TRANG:
            return None
        return f.read_text("utf-8", errors="replace")
    except (OSError, ValueError):
        return None


def _noi_dung_tab(tt: dict | None, dung_luong_chinh: int) -> str:
    if not tt:
        return '<p>Chưa check ID ads cho build này.</p>'
    trang = _doc_trang(tt)
    if trang is None:
        return '<p>Không đọc được trang audit đầy đủ; xem khối tóm tắt ở tab đầu.</p>'
    srcdoc = _E(trang, quote=True)
    if dung_luong_chinh + len(srcdoc.encode("utf-8")) > MAX_BAO:
        return '<p>Trang audit quá lớn để nhúng vào report (đã giữ khối tóm tắt ở tab đầu).</p>'
    return (f'<iframe class="rt-frame" title="Check ID ads" sandbox="allow-scripts" '
            f'referrerpolicy="no-referrer" srcdoc="{srcdoc}"></iframe>')


def boc(nhan_tab1: str, phan_chinh: str, tt: dict | None) -> str:
    """Thanh tab + hai panel: tab 1 = `phan_chinh` (kem khoi tom tat), tab 2 = trang audit day du."""
    tab2 = _noi_dung_tab(tt, len(phan_chinh.encode("utf-8")))

    def nut(i: int, ten: str) -> str:
        on = i == 1
        return (f'<button type="button" role="tab" class="rt-tab" id="rt-t{i}" aria-controls="rt-p{i}" '
                f'aria-selected="{str(on).lower()}" tabindex="{0 if on else -1}">{_E(ten)}</button>')

    return (f'{CSS}<div class="rt-bar" role="tablist" aria-label="Nội dung report">{nut(1, nhan_tab1)}{nut(2, "Check ID ads")}</div>'
            f'<div class="rt-panel" role="tabpanel" id="rt-p1" aria-labelledby="rt-t1">{audit_tom_tat.khoi_html(tt)}{phan_chinh}</div>'
            f'<div class="rt-panel" role="tabpanel" id="rt-p2" aria-labelledby="rt-t2" hidden>{tab2}</div>{JS}')
