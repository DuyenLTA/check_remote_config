"""Cac cau Action ve LUONG First Open ma bo TC 3.6.1 viet va tool tung khong dich duoc (AIP886 31/10/2026).

    "Chon Francais o LFO1."          -> ChonNgonNgu (fo_flow chon dung ngon ngu khi qua LFO)
    "Di tiep qua OB2."               -> GoTo, lai tiep toi man xa nhat ma dong Expected nhac (OB4)
    "Hoan thanh OB4."                -> GoTo ra khoi onboarding (man sau do: Question / paywall / Home)
    "Di het luong."                  -> GoTo Home
    "Chon 1 item."                   -> bam o lua chon dau tien o man Question
    "Mo lai tu Recent."              -> MoLai bang icon
Khong khop -> None, `act_resolver` xet tiep bang luat co ban.
"""

from __future__ import annotations

import re

from . import fo_ngon_ngu, fo_screens, tag_logcat, ui_names
from .act_types import ChonNgonNgu, GoTo, MoLai, NeedsHuman, NoOp, Seq, Tap, TapId, XemTag

# Danh dau GoTo "di tiep qua": case_drive keo dich toi man xa nhat ma Expected nhac.
DI_QUA = "đi tiếp qua "
# Dich "ra khoi onboarding" cho `fo_flow.walk_to`.
RA_KHOI_OB = "!OnboardingActivity"
DI_QUA_RE = re.compile(r"^\s*(?:đi|di)\s+(?:ti[ếe]p\s+)?qua\s+(?:OB|onb)\s*(\d)\b", re.I)
HOAN_THANH_OB_RE = re.compile(r"^\s*ho[àa]n\s*th[àa]nh\s+(?:OB|onb(?:oarding)?)\s*\d\s*\.?\s*$", re.I)
HET_LUONG_RE = re.compile(r"^\s*(?:đi|di)\s+h[ếe]t\s+lu[ồo]ng\b", re.I)
CHON_ITEM_RE = re.compile(r"^\s*(?:ch[ọo]n|b[ấa]m|tap)\s+(?:1|m[ộo]t)\s+(?:item|style|[ôo]|l[ựu]a\s*ch[ọo]n|"
                          r"đ[áa]p\s*[áa]n)\b", re.I)
# "Di qua OB1 → OB4": lai toi OB4, chup moi trang.
DI_QUA_TOI_RE = re.compile(r"^\s*(?:đi|di)\s+qua\s+(?:OB|onb)\s*\d\s*(?:→|->|đến|den|tới|toi)\s*(?:OB|onb)\s*(\d)\b",
                           re.I)
# Buoc chi ghi ten man: "LFO2.", "OB3.", "OB4."
CHI_TEN_MAN_RE = re.compile(r"^\s*((?:LFO|OB|onb)\s*\d)\s*\.?\s*$", re.I)
TICK_RE = re.compile(r"^\s*(?:b[ấa]m|nh[ấa]n|tap)\s+(?:n[úu]t\s+)?tick\b", re.I)
CHUP_RE = re.compile(r"^\s*ch[ụu]p\s+(?:m[àa]n|[ảa]nh)\b", re.I)
NGOAC_RE = re.compile(r"[\"“”'‘’]([^\"“”'‘’]{1,60})[\"“”'‘’]")
MO_LAI_TU_RE = re.compile(r"^\s*(?:m[ởo]|open)\s*(?:l[ạa]i)?\s*(?:app\s*)?(?:t[ừu]|b[ằa]ng|qua)\s+"
                          r"(?:recent|đa\s*nhi[ệe]m|icon|launcher)\b", re.I)


def resolve(text: str, nodes):
    tags = tag_logcat.tags_cua(text)
    if tags:
        return XemTag(tuple(tags), "đọc log của tag " + ", ".join(tags)
                      + (" (bật tester mode trước)" if tag_logcat.TESTER_TAG in tags else ""))
    nn = fo_ngon_ngu.doc_cau(text)
    if nn:
        return ChonNgonNgu(nn[1], f"chọn {nn[1]} khi lái qua LFO")
    m = DI_QUA_TOI_RE.match(text)
    if m:
        return GoTo(f"OnboardingActivity#{m.group(1)}", f"{DI_QUA}tới OB{m.group(1)} (chụp mọi trang đi qua)")
    m = DI_QUA_RE.match(text)
    if m:
        so = int(m.group(1))
        return GoTo(f"OnboardingActivity#{so + 1}", f"{DI_QUA}OB{so} (chụp mọi trang đi qua)")
    m = CHI_TEN_MAN_RE.match(text)
    if m:
        dich = fo_screens.target_for(m.group(1))
        if dich:
            return GoTo(dich, f"bước chỉ ghi tên màn {m.group(1).strip()} — lái tới đó (đã qua thì bỏ)")
    if TICK_RE.match(text):
        return GoTo("OnboardingActivity#1", "bấm tick xác nhận ngôn ngữ ở LFO (đã qua LFO thì bỏ)")
    if CHUP_RE.match(text):
        return NoOp("bước chụp màn để chấm — tool đã chụp ở mỗi bước")
    bam = _bam_sau_khi_chon(text, nodes)
    if bam is not None:
        return bam
    if HOAN_THANH_OB_RE.match(text):
        return GoTo(RA_KHOI_OB, "hoàn thành onboarding → lái tới màn sau onboarding")
    if HET_LUONG_RE.match(text):
        return GoTo("MainActivity", "đi hết luồng First Open tới Home")
    if MO_LAI_TU_RE.match(text):
        return MoLai("mở lại app bằng icon (TC ghi Recent — nhiều máy không coi Recent là ẩn app)")
    if CHON_ITEM_RE.match(text):
        return _chon_item(nodes)
    return None


def _bam_sau_khi_chon(text: str, nodes):
    """"Bam 'FR - Go'" o man Question khi nut cta CHUA hien (chi hien sau khi chon mot o): chon o dau roi bam cta.
    Nut da hien / khong phai man Question -> None (luat bam theo chu lo)."""
    m = NGOAC_RE.search(text)
    if not m or not re.match(r"^\s*(?:b[ấa]m|nh[ấa]n|tap|click)\b", text, re.I) or not nodes:
        return None
    if any(m.group(1).strip().casefold() == (n.text or "").strip().casefold() for n in nodes):
        return None
    chon = _chon_item(nodes)
    cta = ui_names.chon_item_cta_ids()
    if not isinstance(chon, Tap) or not cta:
        return None
    return Seq((chon, TapId(cta, f"bấm {m.group(1)!r} (nút hiện sau khi chọn 1 ô)")),
               f"chọn 1 ô rồi bấm {m.group(1)!r}")


def _chon_item(nodes):
    """O dau tien (tren cung, roi trai nhat) mang id o lua chon cua man Question."""
    ids = set(ui_names.chon_item_ids())
    o = [n for n in nodes if n.resource_id in ids and n.visible and not n.bounds.empty]
    if not o:
        return NeedsHuman("không thấy ô lựa chọn nào (id ở mục chon_item của ui_names.yaml) để chọn 1 item")
    n = min(o, key=lambda n: (n.bounds.top, n.bounds.left))
    x, y = n.bounds.center
    return Tap(n.label, x, y, "ô lựa chọn đầu tiên (TC chỉ đòi chọn 1 item bất kỳ)")
