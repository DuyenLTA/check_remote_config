"""Cham dong Expected ghi THANG ID ads (`ca-app-pub-<pub>/<so>`) - bo case IAA, TC dan ID tu sheet KT.

Cau loai nay khong co ma vi tri (`302`, `show_*`) nen luat cu roi vao nhanh phu dinh chung chung: cau
"Request dung unit high X truoc; high khong fill thi goi unit thuong Y" bi doc la phu dinh ("khong fill thi
goi") va moi request cua man khac (native OB1) bi tinh -> FAIL "van co request" ma X, Y khong he duoc goi
(do 12/11/2026, AIP893 IAA-01-01). Nguoc lai cau "Native hien thi" PASS nho native OB1 - PASS gia.

Doi chieu theo DUOI ID: log AdEventLogger che ID con 3 so cuoi (`*****865`), FA-SVC thi co du. Moi ID trong
cau xep vao mot vai:
  - bat buoc  : ve khang dinh ("Request ... unit high X", "Chi request unit thuong Y")
  - cam       : ve phu dinh ("khong request unit high X", "Khong request unit nao cua vi tri (X, Y)")
  - tuy       : ve dieu kien sau "thi" ("high khong fill thi goi unit thuong Y") - co hay khong deu dung
"""

from __future__ import annotations

import re

from .verdict_levels import CONFIG_BLOCKED, FAIL, NEEDS_HUMAN, PASS, out

ID_RE = re.compile(r"ca-app-pub-\d+/(\d+)")
# Cat ve theo dau cau; "(X, Y)" giu nguyen trong mot ve (dau phay trong ngoac khong cat).
VE_RE = re.compile(r"[^;.,(]*(?:\([^)]*\)[^;.,(]*)*")
PHU_DINH_RE = re.compile(r"kh[oô]ng\s+(?:\w+\s+){0,2}?(?:request|g[ọo]i|(?:pre)?load)", re.I)
DIEU_KIEN_RE = re.compile(r"\bth[ìi]\b", re.I)
# Dong hoi ad HIEN THI ("Co fill thi Banner van hien thi tai Home") - khong fill thi chua kiem duoc.
HIEN_THI_RE = re.compile(r"hi[ểe]n\s*th[ịi]|\bhi[ểe]n\b|\bshow\b|xu[ấa]t\s*hi[ệe]n", re.I)


def ids_trong(text: str) -> list[str]:
    return ID_RE.findall(text or "")


def _vai(text: str) -> dict[str, str]:
    """so cuoi ID -> 'bat_buoc' | 'cam' | 'tuy'."""
    vai: dict[str, str] = {}
    for ve in VE_RE.findall(text):
        so = ID_RE.findall(ve)
        if not so:
            continue
        if DIEU_KIEN_RE.search(ve):
            # Chi phan SAU "thi" la he qua cua dieu kien; ID dung truoc "thi" (hiem) van tinh khang dinh.
            sau = DIEU_KIEN_RE.split(ve, maxsplit=1)[1]
            for s in so:
                vai.setdefault(s, "tuy" if s in sau else "bat_buoc")
        elif PHU_DINH_RE.search(ve):
            for s in so:
                vai.setdefault(s, "cam")
        else:
            for s in so:
                vai.setdefault(s, "bat_buoc")
    return vai


def _khop(unit: str, so: str) -> bool:
    """`*****865` / ID day du -> co phai ID ket thuc bang `so` khong."""
    duoi = re.sub(r"\D", "", (unit or "").rsplit("/", 1)[-1])
    return bool(duoi) and so.endswith(duoi)


def _da_toi(drive: dict) -> bool:
    """Tool da lai het buoc Action chua. Dung giua chung = chua toi vi tri, vang request chua noi gi."""
    return (drive or {}).get("status", "DONE") == "DONE"


def cham(text: str, units: list[dict], drive: dict) -> dict | None:
    """Dong co ID day du -> verdict; khong co ID -> None (de luat cu cham)."""
    vai = _vai(text)
    if not vai:
        return None
    req = [u for u in units if u.get("requested")]
    actual = {"requested": [u["unit"] for u in req]}
    bi_goi = {s: [u["unit"] for u in req if _khop(u["unit"], s)] for s in vai}
    sai = [s for s, v in vai.items() if v == "cam" and bi_goi[s]]
    if sai:
        return out(FAIL, "vẫn có request unit bị cấm: " + ", ".join(f"…{s} ({', '.join(bi_goi[s])})" for s in sai),
                   actual)
    thieu = [s for s, v in vai.items() if v == "bat_buoc" and not bi_goi[s]]
    if not _da_toi(drive):
        # Chua toi vi tri: ca "co request" lan "khong request" deu chua chung minh duoc gi.
        return out(NEEDS_HUMAN, "tool chưa lái tới vị trí của case (dừng ở bước "
                                f"{(drive or {}).get('stopped_at') or '?'}), chưa có request nào của "
                                + ", ".join(f"…{s}" for s in vai) + " — đo tay", actual)
    if thieu:
        return out(FAIL, "không có request unit " + ", ".join(f"…{s}" for s in thieu), actual)
    co = [f"…{s}" for s, v in vai.items() if v != "cam" and bi_goi[s]]
    cam = [f"…{s}" for s, v in vai.items() if v == "cam"]
    return out(PASS, "; ".join(x for x in (
        f"có request {', '.join(co)}" if co else "",
        f"không request {', '.join(cam)}" if cam else "") if x), actual)


def cham_theo_case(text: str, units: list[dict], drive: dict, so_case: list[str], phu_dinh: bool) -> dict:
    """Dong ads KHONG ghi ID ("Co fill thi Native van hien thi tai Loading") trong case co ID o dong khac.

    Ad cua vi tri = chi cac ID cua case: native OB1 load o luong FO khong phai native Loading (PASS gia
    12/11/2026, AIP893 IAA-01-01).
    """
    cua = [u for u in units if any(_khop(u["unit"], s) for s in so_case)]
    actual = {"vi_tri": [f"…{s}" for s in so_case], "requested": [u["unit"] for u in cua if u.get("requested")]}
    ten = ", ".join(f"…{s}" for s in so_case)
    if phu_dinh:
        goi = [u["unit"] for u in cua if u.get("requested") or u.get("shown")]
        if goi:
            return out(FAIL, f"vẫn có request/show unit của vị trí ({', '.join(goi)})", actual)
        if not _da_toi(drive):
            return out(NEEDS_HUMAN, f"tool chưa lái tới vị trí, vắng request {ten} chưa chứng minh gì — đo tay",
                       actual)
        return out(PASS, f"không request/show unit nào của vị trí ({ten})", actual)
    for loai, nhan in (("shown", "đã show"), ("loaded", "load được"), ("requested", "được request (kho không fill)")):
        co = [u["unit"] for u in cua if u.get(loai)]
        if co and loai == "requested" and HIEN_THI_RE.search(text):
            # "Co fill thi ... van hien thi": khong fill = chua kiem duoc hien thi -> BLOCKED (user chot 13/11/2026).
            return out(CONFIG_BLOCKED, f"unit của vị trí {nhan}: {', '.join(co)} — chưa có ad hiện để kiểm hiển thị, "
                                       "cần fill (lắc máy chọn ad source / test mode network)", actual)
        if co:
            return out(PASS, f"unit của vị trí {nhan}: {', '.join(co)}", actual)
    if not _da_toi(drive):
        return out(NEEDS_HUMAN, f"tool chưa lái tới vị trí, chưa có request {ten} — đo tay", actual)
    return out(FAIL, f"không có request unit nào của vị trí ({ten})", actual)
