"""Dong "Khong co native ad, hien thi icon SWIPE + text 'Swipe to next'": ve dau phu dinh ad o cac vi tri case TAT.

Truoc day ca cau roi vao luat ads khang dinh ("hien thi") tren MOI vi tri case dong toi (ca 301 dang bat) ->
301 show -> PASS, ve "khong co native" khong ai cham (AIP886 R04-01 31/10/2026).
"""

from __future__ import annotations

import re

from .ad_positions import _khop_vi_tri
from .verdict_levels import FAIL, PASS, out

KHONG_CO_RE = re.compile(r"^\s*kh[ôo]ng\s+c[óo]\s+(?P<loai>native|banner|inter\w*|qu[ảa]ng\s*c[áa]o|ads?)\b", re.I)
SHOW_KEY_RE = re.compile(r"^show_(\d{3}_[a-z0-9_]+)$")
FULL_RE = re.compile(r"\bfull\b|to[àa]n\s*m[àa]n", re.I)


def _vi_tri_tat(cfg: dict, loai: str) -> list[str]:
    """Vi tri case dat show_<vi tri> = false, loc theo loai ad trong cau."""
    goc = {"native": "native", "banner": "banner"}.get(loai.lower()[:6], "inter" if loai.lower().startswith("inter")
                                                       else "")
    ra = []
    for k, v in (cfg or {}).items():
        m = SHOW_KEY_RE.match(k)
        if m and str(v).strip().lower() == "false" and (not goc or goc in m.group(1)):
            ra.append(m.group(1))
    return ra


def cham(text: str, units: list[dict], cfg: dict | None) -> dict | None:
    m = KHONG_CO_RE.match(text or "")
    if not m:
        return None
    tat = _vi_tri_tat(cfg or {}, m.group("loai"))
    if not tat and FULL_RE.search(text) and m.group("loai").lower().startswith("native"):
        # "Khong co native full" khi 303 van bat (case ep no-fill, S02-01): native full = native OB3 (303) - request
        # duoc phep (no-fill), chi khong duoc SHOW.
        full = [u for u in units if _khop_vi_tri(u, "303")]
        show = [u for u in full if u.get("shown")]
        if show:
            return out(FAIL, f"native full (303) vẫn show: {', '.join(u['unit'] for u in show)}", [u["unit"] for u in show])
        return out(PASS, f"native full (303) không show lần nào ({sum(int(u.get('requested') or 0) for u in full)} "
                         "request)", "303")
    if not tat:
        return None
    co = [u for u in units if any(_khop_vi_tri(u, t) for t in tat) and (u.get("requested") or u.get("shown"))]
    if co:
        return out(FAIL, f"vị trí case tắt vẫn có ad: {', '.join(u['unit'] for u in co)}", [u["unit"] for u in co])
    so = sorted({t.split("_")[0] for t in tat})
    return out(PASS, f"các vị trí case tắt ({', '.join(so)}) không có request / show nào", so)
