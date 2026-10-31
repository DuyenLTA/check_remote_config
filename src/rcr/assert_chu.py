"""Cham dong Expected co chu trong ngoac: MOI chuoi, co phu dinh, co ban dich.

Truoc day chi lay chuoi DAU TIEN va chi hoi "co thay khong" (AIP886 31/10/2026):
  - "KHONG dung khoi 'en' ('EN ROOT - ...')" -> tim 'en', thay o dau do -> PASS gia;
  - "Nen GIF chay 1 lan roi dung o frame cuoi, sub_title 'Gif once'" -> thay chu -> PASS,
    ve GIF khong ai do;
  - chon Francais thi 'Swipe to next' hien ban dich 'Balayez pour continuer' -> FAIL gia.
"""

from __future__ import annotations

import re

from . import assert_ads
from .verdict_levels import FAIL, NEEDS_HUMAN, NOT_VERIFIABLE, PASS, out, worst

NGOAC_RE = re.compile(r"[\"“”'‘’]([^\"“”'‘’]{2,80})[\"“”'‘’]")
# Ve phu dinh dung TRUOC chuoi trong cung ve: "khong co 'KEY CU ...'", "KHONG dung khoi 'en' (...)".
PHU_DINH_RE = re.compile(r"\bkh[ôo]ng\b|\bch[ẳa]ng\b|\bno\b|\bnot\b|\bwithout\b", re.I)
# Duoi "..." la cho TC luoc phan con lai, khong phai chu tren man.
DUOI_RE = re.compile(r"\s*(?:\.{3}|…)\s*$")
# Ve hinh anh dong / GIF ma chu khong chung minh duoc.
HINH_DONG_RE = re.compile(r"\bgif\b|video_loop|frame\s+cu[ốo]i|ch[ạa]y\s+\d+\s+l[ầa]n|l[ặa]p\s+li[êe]n\s+t[ụu]c", re.I)
NGAN_NHAT = 3
# "dung mau primary cua app" - mau goi bang TEN, khong co ma: thay chu khong chung minh dung mau.
MAU_RE = re.compile(r"\bm[àa]u\b|\bcolou?r\b", re.I)
HEX_RE = re.compile(r"#[0-9a-f]{6}\b", re.I)
PRIMARY_RE = re.compile(r"primary|ch[ủu]\s*[đd][ạa]o", re.I)


def _mau_ten(text: str, drive: dict) -> dict:
    """Dong "chu dung mau primary": so voi mau `color/primary` cua APK da do tren anh (case_run do san)."""
    do = (drive or {}).get("mau_primary") or {}
    if not PRIMARY_RE.search(text) or not do.get("hex"):
        return out(NOT_VERIFIABLE, "câu nêu màu bằng tên, không có mã màu để đo", text, tinh=True)
    if do.get("khop"):
        return out(PASS, f"chữ có màu {do['hex']} = color/primary của APK ({do.get('pixel', 0)} pixel)", do["hex"])
    if do.get("pixel") is None:
        return out(NEEDS_HUMAN, f"chưa có ảnh của chữ để so với color/primary {do['hex']}", text)
    return out(FAIL, f"chữ không mang màu color/primary {do['hex']} của APK (màu đo được {do.get('thay', '?')})",
               do.get("thay", ""))


def _chuoi(text: str) -> list[tuple[str, bool]]:
    """[(chu can tim, phai VANG MAT)] theo thu tu trong cau."""
    ra = []
    for m in NGOAC_RE.finditer(text):
        chu = DUOI_RE.sub("", m.group(1)).strip(" -–")
        if len(chu) < NGAN_NHAT:
            continue
        # Ve chua chuoi: tu dau phay/cham phay gan nhat truoc no toi chuoi.
        truoc = re.split(r"[,;]", text[:m.start()])[-1]
        ra.append((chu, bool(PHU_DINH_RE.search(truoc))))
    return ra


def _thay(chu: str, dumps: list[str], ban_dich: dict) -> str:
    """Chuoi da thay tren man ("" neu khong): nguyen van, hoac ban dich cua chinh chuoi do trong APK."""
    if any(chu.casefold() in d for d in dumps):
        return chu
    for dich in ban_dich.get(chu) or ():
        if any(dich.casefold() in d for d in dumps):
            return dich
    return ""


def cham(text: str, drive: dict, bo_hinh_dong: bool = False) -> dict | None:
    """None khi dong khong co chuoi nao du dai de tim. `bo_hinh_dong`: ve GIF da do o noi khac (splash_media)."""
    can = _chuoi(text)
    if not can:
        return None
    steps = (drive or {}).get("steps") or []
    if not steps:
        return out(NEEDS_HUMAN, "chưa lái tới màn nào để tìm chữ", "")
    dumps = [(s.get("dump") or "").casefold() for s in steps]
    toi_noi = assert_ads.tapped(drive) or bool(drive.get("walked"))
    ban_dich = drive.get("ban_dich") or {}
    ket = []
    for chu, vang in can:
        thay = _thay(chu, dumps, ban_dich)
        if vang:
            if thay:
                ket.append(out(FAIL, f"vẫn thấy {thay!r} trên màn", thay))
            elif not toi_noi:
                ket.append(out(NEEDS_HUMAN, f"chưa lái tới màn cần xem nên chưa kết luận được không có {chu!r}", ""))
            else:
                ket.append(out(PASS, f"không thấy {chu!r} trên màn nào đã chụp — đúng kỳ vọng", ""))
        elif thay:
            ghi = f"thấy {chu!r}" if thay == chu else f"thấy {thay!r} (bản dịch của {chu!r} trong APK)"
            ket.append(out(PASS, ghi, thay))
        elif drive.get("blocked_steps"):
            ket.append(out(NEEDS_HUMAN, f"không thấy {chu!r} vì màn hình bị quảng cáo che ở bước "
                                        f"{drive['blocked_steps']} — đóng quảng cáo rồi chạy lại", ""))
        elif not toi_noi:
            ket.append(out(NEEDS_HUMAN, f"không thấy {chu!r}, nhưng tool chưa lái tới màn nào khác "
                                        f"(đang ở {assert_ads.where(drive) or 'màn mở đầu'})", ""))
        else:
            ket.append(out(FAIL, f"không thấy {chu!r} trên màn nào đã chụp", ""))
    if MAU_RE.search(text) and not HEX_RE.search(text):
        ket.append(_mau_ten(text, drive))
    # Bo chu trong ngoac truoc: "sub_title 'Gif loop'" la chu tren man, khong phai cau hoi GIF (AIP886 R02-01).
    if HINH_DONG_RE.search(NGOAC_RE.sub("", text)) and not bo_hinh_dong:
        ket.append(out(NOT_VERIFIABLE, "phần GIF / hình động phải đo theo khung hình, chữ trên màn không chứng minh được",
                       text, tinh=True))
    if len(ket) == 1:
        return ket[0]
    return out(worst(k["verdict"] for k in ket), "; ".join(k["reason"] for k in ket),
               "; ".join(str(k.get("actual") or "") for k in ket if k.get("actual")))
