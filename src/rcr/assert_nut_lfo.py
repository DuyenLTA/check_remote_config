"""Dong ve NUT NEXT / TICK cua man chon ngon ngu (LFO): "Button Next disable + co icon huong dan cho den khi chon
ngon ngu", "nut tick bat san".

Truoc day dong nay khop ten "nut next onboarding" (btnNextOnboarding...) nen tool di tim nut Next cua man OB tren
man LFO va bao FAIL "khong thay nut next" (AIP936 RG01-04 03/11/2026). Nut cua man LFO la `buttonLanguageNext`,
ban tay huong dan la `lottieHandPoint`; ca hai co san trong dump moi man tool da chup, kem trang thai enabled.
"""

from __future__ import annotations

import re

from . import ui_dump
from .verdict_levels import FAIL, PASS, out

NUT_RE = re.compile(r"(?:button|nút|nut)\s*(?:next|tick)", re.I)
TAT_RE = re.compile(r"disable|tắt|không\s+bấm\s+được|mờ", re.I)
BAT_RE = re.compile(r"enable|bật\s+sẵn|bat\s+san|bấm\s+được", re.I)
TAY_RE = re.compile(r"icon\s+hướng\s+dẫn|bàn\s+tay|hand|hint", re.I)
DEN_KHI_CHON_RE = re.compile(r"cho\s+đến\s+khi\s+chọn|until", re.I)
NUT_ID, TAY_ID = "buttonLanguageNext", "lottieHandPoint"


def _man(drive: dict, ten: str) -> list:
    """Cac node cua dump DAU TIEN o man co `ten` trong activity (Language1x = LFO1, Language2x = LFO2)."""
    for st in drive.get("steps") or []:
        if ten in (st.get("activity") or "") and st.get("dump"):
            return ui_dump.parse_dump(st["dump"])
    return []


def _nut(nodes) -> object | None:
    return next((n for n in nodes if n.resource_id == NUT_ID), None)


def cham(text: str, drive: dict) -> dict | None:
    """Dong ve nut Next/tick man ngon ngu -> ket qua; dong khac hoac chua chup duoc man LFO -> None."""
    if not NUT_RE.search(text or "") or "focus" in text.lower():
        return None
    lfo1 = _man(drive or {}, "Language1")
    nut = _nut(lfo1)
    if nut is None:
        return None
    ve = []
    if TAT_RE.search(text):
        ve.append((not nut.enabled, f"LFO1 {NUT_ID} enabled={str(nut.enabled).lower()} (kỳ vọng tắt)"))
    elif BAT_RE.search(text):
        ve.append((nut.enabled, f"LFO1 {NUT_ID} enabled={str(nut.enabled).lower()} (kỳ vọng bật sẵn)"))
    if TAY_RE.search(text):
        co_tay = any(n.resource_id == TAY_ID and n.visible for n in lfo1)
        ve.append((co_tay, f"bàn tay hướng dẫn {TAY_ID} {'có' if co_tay else 'không có'} trên LFO1"))
    if DEN_KHI_CHON_RE.search(text):
        nut2 = _nut(_man(drive or {}, "Language2"))
        if nut2 is not None:
            ve.append((nut2.enabled, f"chọn ngôn ngữ xong (LFO2) {NUT_ID} enabled={str(nut2.enabled).lower()}"))
    if not ve:
        return None
    return out(PASS if all(ok for ok, _ in ve) else FAIL, "; ".join(ly for _, ly in ve), text)
