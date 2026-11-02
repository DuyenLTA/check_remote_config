"""Dong "Khong hien thi man X ..., vao thang Home": X khong duoc xuat hien o man nao da qua, va (neu doi) phai toi Home.

Truoc day dong nay roi vao `_man_da_toi` voi dich doc tu cau: "Khong hien thi man Question du
onboard_config_content_new ..." khop chu "onb" -> dich Onboarding -> man cuoi dang o Onboarding -> PASS gia
(AIP886 R04-03, 31/10/2026); user cu dung o inter splash luc cham -> FAIL gia (O02-01).
"""

from __future__ import annotations

import re

from . import fo_screens
from .case_cham_them import CHUA_TOI_HOME, HOME_RE
from .verdict_levels import FAIL, NEEDS_HUMAN, PASS, out

MAN_KHONG_RE = re.compile(
    r"kh[ôo]ng\s+(?:hi[ểe]n\s*th[ịi]|v[àa]o|c[óo]|xu[ấa]t\s*hi[ệe]n)\s+(?:m[àa]n\s+)?"
    r"(?P<man>question|onboarding|language|lfo\s*\d?|ob\s*\d|paywall|billing)\b", re.I)


def _da_qua(drive: dict) -> list[str]:
    ten = [s.get("activity") or "" for s in (drive or {}).get("steps") or []]
    ten += [t.get("activity") or "" for trail in (drive or {}).get("trails") or [] for t in trail]
    ten.append(((drive or {}).get("final") or {}).get("activity") or "")
    return [t for t in ten if t]


# "Khong hien thi OB1, OB3, OB5, Question": ca danh sach sau dong tu phu dinh.
DANH_SACH_RE = re.compile(r"(?:,|\bv[àa]\b|&)\s*(question|ob\s*\d|lfo\s*\d)\b", re.I)
OB_RE = re.compile(r"^(ob|lfo)\s*(\d)$", re.I)


def _trang_ob(text: str, m) -> list[str]:
    """Moi trang OB/LFO trong danh sach phu dinh (ob1, ob3...) - mot Activity chua MOI trang OB."""
    ten = [m.group("man")] + DANH_SACH_RE.findall(text[m.end():].split(".")[0])
    return [f"{x.group(1).lower()}{x.group(2)}" for t in ten if (x := OB_RE.match(t.strip()))]


def _cham_trang(trang: list[str], events) -> dict | None:
    """Trang OB cham bang event `<trang>_view` cua app: VslTemplate4OnboardingActivity chua ca OB1..OB5,
    thay Activity do khong noi duoc OB1 co hien hay khong (AIP936 RG04-01: OB2/OB4 hien -> FAIL oan)."""
    views = {e.get("name", "") for e in events or ()}
    if not any(v.endswith("_view") for v in views):
        return None
    co = [t.upper() for t in trang if f"{t}_view" in views]
    if co:
        return out(FAIL, f"có event {', '.join(c.lower() + '_view' for c in co)} — {', '.join(co)} vẫn hiện", co)
    return out(PASS, f"không có event {', '.join(t + '_view' for t in trang)} — {', '.join(t.upper() for t in trang)} "
                     "không hiện", "")


def cham(text: str, drive: dict, events=()) -> dict | None:
    m = MAN_KHONG_RE.search(text)
    if not m:
        return None
    trang = _trang_ob(text, m)
    if trang:
        ket = _cham_trang(trang, events)
        con = [t for t in DANH_SACH_RE.findall(text[m.end():].split(".")[0]) if not OB_RE.match(t.strip())]
        if ket and not con:
            return ket
        if ket:
            # Con man khac trong danh sach (Question): cham them bang Activity nhu cu.
            phu = cham(f"Không hiển thị {con[0]}", drive)
            return ket if not phu else out(FAIL if FAIL in (ket["verdict"], phu["verdict"]) else
                                           (phu["verdict"] if ket["verdict"] == PASS else ket["verdict"]),
                                           f"{ket['reason']}; {phu['reason']}", "")
        if not ket:
            return out(NEEDS_HUMAN, "app không bắn event màn (*_view) nên không phân biệt được trang OB "
                                    "trong cùng một OnboardingActivity", "")
    dich = fo_screens.target_for(m.group("man"))
    if not dich:
        return None
    ten_man = dich.partition("#")[0]
    qua = _da_qua(drive)
    hien = [a for a in qua if ten_man in a]
    if hien:
        return out(FAIL, f"màn {ten_man} vẫn hiện ({hien[0].split('.')[-1]})", hien[0].split(".")[-1])
    cuoi = ((drive or {}).get("final") or {}).get("activity") or ""
    gon = cuoi.split(".")[-1] or "?"
    if HOME_RE.search(text):
        if "MainActivity" in cuoi:
            return out(PASS, f"không có màn {ten_man} trong các màn đã qua, tới Home ({gon})", gon)
        if not cuoi or any(x in cuoi for x in CHUA_TOI_HOME):
            return out(NEEDS_HUMAN, f"chưa lái tới Home (màn cuối {gon}) nên chưa kết luận được", gon)
        return out(FAIL, f"sau bước cuối đang ở {gon}, không phải Home", gon)
    if fo_screens.thu_tu(_man_cua(cuoi)) <= fo_screens.thu_tu(dich):
        return out(NEEDS_HUMAN, f"tool chưa đi qua chỗ màn {ten_man} sẽ hiện (màn cuối {gon})", gon)
    return out(PASS, f"không có màn {ten_man} trong các màn đã qua (màn cuối {gon})", gon)


def _man_cua(activity: str) -> str:
    """Activity -> ten trong THU_TU cua fo_screens ("...VslBillingActivity" -> "BillingActivity")."""
    return next((t for t in reversed(fo_screens.THU_TU) if t and t.partition("#")[0] in activity), "")
