"""Dong "Indicator trang hien thi day du, active o trang N": dem cham chi trang tren dump OB da chup.

Truoc day ra NOT_VERIFIABLE ("phai nhin mat") du dump co du cham (AIP886 R01-03 31/10/2026).
"""

from __future__ import annotations

import re

from . import fo_steps, ui_dump
from .verdict_levels import FAIL, NEEDS_HUMAN, PASS, out

INDICATOR_RE = re.compile(r"indicator|ch[ấa]m\s*(?:ch[ỉi]\s*)?trang", re.I)
TRANG_RE = re.compile(r"active\s*(?:ở|o|tại|tai)?\s*trang\s*(\d)|trang\s*(\d)", re.I)


def cham(text: str, drive: dict) -> dict | None:
    if not INDICATOR_RE.search(text):
        return None
    m = TRANG_RE.search(text)
    can = int(m.group(1) or m.group(2)) if m else 0
    thay = []
    for st in (drive or {}).get("steps") or []:
        if "OnboardingActivity" not in (st.get("activity") or "") or not st.get("dump"):
            continue
        nodes = ui_dump.app_nodes(ui_dump.parse_dump(st["dump"]))
        trang = fo_steps.onboarding_page(nodes)
        if not trang:
            continue
        so = len([n for n in nodes if n.resource_id == fo_steps.DOT_ID and n.visible] or fo_steps._cham_khong_id(nodes))
        thay.append((st.get("n"), trang, so))
    if not thay:
        return out(NEEDS_HUMAN, "chưa có dump trang onboarding nào đọc được chấm chỉ trang", "")
    if can:
        dung = [t for t in thay if t[1] == can]
        if not dung:
            return out(NEEDS_HUMAN, f"chưa chụp được trang {can} (đã thấy trang {sorted({t[1] for t in thay})})", "")
        n, trang, so = dung[0]
        if so < 2:
            return out(FAIL, f"bước {n}: chỉ thấy {so} chấm chỉ trang", f"{so} chấm")
        return out(PASS, f"bước {n}: {so} chấm chỉ trang, chấm active ở trang {trang}", f"{so} chấm, active {trang}")
    n, trang, so = thay[0]
    v = PASS if so >= 2 else FAIL
    return out(v, f"bước {n}: {so} chấm chỉ trang, active ở trang {trang}", f"{so} chấm")
