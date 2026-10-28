"""Tom tat ket qua check ID ads (audit-fanout) doc tu trang HTML audit sinh san.

Audit ghi `<repo audit>/tools/ad-checklist-diff/out/<package>-artifact.html`. Headless Claude khong
publish duoc artifact nen bot / report tu doc trang nay bang code (khong tin chu Claude tra ve).
Module thuan: khong goi mang, khong goi may.
"""

from __future__ import annotations

import html
import os
import re
from datetime import date, datetime
from pathlib import Path

OUT_REL = Path("tools") / "ad-checklist-diff" / "out"
PACKAGE_RE = re.compile(r"^[A-Za-z0-9_]+(\.[A-Za-z0-9_]+)*$")
MAX_TRANG = 10 * 1024 * 1024
_BIGFRAC = re.compile(r'<div class="bigfrac"><span class="n">(\d+)</span><span class="d">/(\d+)</span>')
_LUC = re.compile(r"<span>audit <b>([^<]+)</b>")
_CALLOUT = re.compile(r'<div class="callout">.*?<p>(.*?)</p>', re.S)
CHUA_CHECK = "🔎 ID ads: chưa check ID ads cho build này"


def _the(html_text: str, loai: str) -> int | None:
    m = re.search(rf'<button class="card[^"]*" data-f="{loai}"[^>]*><span class="n">(\d+)</span>', html_text)
    return int(m.group(1)) if m else None


def doc(html_text: str) -> dict | None:
    """-> {khop, tong, lech, ngoai_sheet, luc, canh_bao} hoac None khi trang hong / thieu so."""
    big, lech, ngoai = _BIGFRAC.search(html_text), _the(html_text, "fail"), _the(html_text, "leftover")
    if not big or lech is None or ngoai is None:
        return None
    luc = _LUC.search(html_text)
    canh = [html.unescape(re.sub(r"<[^>]+>", "", p)).strip() for p in _CALLOUT.findall(html_text)]
    return {"khop": int(big.group(1)), "tong": int(big.group(2)), "lech": lech, "ngoai_sheet": ngoai,
            "luc": luc.group(1).strip() if luc else "", "canh_bao": " ".join(c for c in canh if c)}


def thu_muc_out() -> Path:
    repo = os.environ.get("AD_AUDIT_REPO") or str(Path.home() / "android-ad-audit")
    return Path(repo) / OUT_REL


def trang_audit(package: str, out: Path | None = None) -> Path | None:
    """Duong dan trang audit cua package, chi khi nam trong thu muc out va la file vua kich thuoc."""
    if not PACKAGE_RE.match(package or ""):
        return None
    out = Path(out) if out else thu_muc_out()
    try:
        f = (out / f"{package}-artifact.html").resolve()
        f.relative_to(out.resolve())
        return f if f.is_file() and f.stat().st_size <= MAX_TRANG else None
    except (OSError, ValueError):
        return None


def _ngay_audit(tt: dict, f: Path) -> date:
    try:
        return datetime.fromisoformat(tt["luc"]).astimezone().date()
    except (ValueError, KeyError):
        return datetime.fromtimestamp(f.stat().st_mtime).date()


def tim(package: str, tu_luc: float | None = None, ngay: date | None = None, out: Path | None = None) -> dict | None:
    """Tom tat + `trang` (duong dan) cua audit package; None neu khong co / cu / hong.

    `tu_luc`: chi nhan khi mtime >= moc (audit chay TRONG luot bot). `ngay`: chi nhan khi audit
    cung ngay (gio may) voi luot checklist - ngay lay tu gio audit ghi trong trang, khong thi mtime.
    """
    f = trang_audit(package, out)
    if not f:
        return None
    try:
        if tu_luc is not None and f.stat().st_mtime < tu_luc:
            return None
        tt = doc(f.read_text("utf-8", errors="replace"))
        if tt is None or (ngay is not None and _ngay_audit(tt, f) != ngay):
            return None
    except OSError:
        return None
    return {**tt, "trang": str(f)}


def dong_tin(tt: dict | None) -> str:
    """Dong tom tat cho tin Discord."""
    if not tt:
        return CHUA_CHECK
    d = f"🔎 ID ads: {tt['khop']}/{tt['tong']} khớp · {tt['lech']} lệch · {tt['ngoai_sheet']} ID ngoài sheet"
    if tt["lech"] > 0:
        d += f"\n⚠️ {tt['lech']} ID lệch sheet — xem trang audit đính kèm"
    if tt.get("canh_bao"):
        d += f"\n⚠️ {tt['canh_bao'][:200]}"
    return d


def dinh_kem(report: Path | None, tt: dict | None) -> list[Path]:
    """File dinh kem Discord: report (neu co) + trang audit (khong trung, tong <= gioi han mot tin)."""
    files = [report] if report else []
    if tt and tt.get("trang") and Path(tt["trang"]) not in files:
        try:
            tong = sum(Path(x).stat().st_size for x in files) + Path(tt["trang"]).stat().st_size
        except OSError:
            return files
        if tong <= MAX_TRANG:
            files.append(Path(tt["trang"]))
    return files


def khoi_html(tt: dict | None) -> str:
    """Khoi "Check ID ads" cho report (style inline, co fallback bien mau -> dung duoc o ca hai khung report)."""
    e = html.escape
    box = ('<section class="audit-ids" style="border:1px solid rgba(128,128,128,.35);border-radius:10px;'
           'padding:12px 16px;display:grid;gap:6px;font-size:14px">')
    if not tt:
        return f'{box}<h2 style="font-size:14px;margin:0">Check ID ads</h2><span>chưa check ID ads cho build này</span></section>'
    mau = "#b3261e" if tt["lech"] else "#1b7a3a"
    out = [f'<h2 style="font-size:14px;margin:0">Check ID ads</h2>',
           f'<span><b style="color:{mau}">{tt["khop"]}/{tt["tong"]}</b> khớp · <b>{tt["lech"]}</b> lệch · '
           f'<b>{tt["ngoai_sheet"]}</b> ID ngoài sheet</span>']
    if tt.get("luc"):
        out.append(f'<span style="opacity:.7">audit lúc {e(tt["luc"])}</span>')
    if tt.get("canh_bao"):
        out.append(f'<span style="color:#b3261e">⚠ {e(tt["canh_bao"])}</span>')
    if tt.get("trang"):
        out.append(f'<span style="opacity:.7">Trang audit: <code>{e(tt["trang"])}</code></span>')
    return box + "".join(out) + "</section>"
