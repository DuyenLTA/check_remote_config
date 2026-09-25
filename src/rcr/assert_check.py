"""Cham tung dong Expected cua case bang du lieu da thu duoc.

Cham TUNG DONG, khong cham ca case mot cuc: Expected von danh so `1. 2. 3.` va
thuong co dong dung dong sai. Verdict cua case = dong XAU NHAT (`verdict_levels`).

Bon nhom cham duoc, do tren 1421 dong Expected that cua bo TC chung:
    188 dong "khong crash"       -> buffer crash cua Android
    125 dong phu dinh ads        -> tap unit da request (`assert_ads`)
    474 dong khang dinh show     -> nt
     66 dong co chu trong ngoac  -> tim trong dump da chup
Dong ngoai bon nhom do -> NOT_VERIFIABLE kem nguyen van. KHONG doan thanh PASS.
"""

from __future__ import annotations

import re

from . import assert_ads, ui_names
from .verdict_levels import (  # noqa: F401 - tai xuat cho cho goi
    CONFIG_BLOCKED,
    CONFIG_OK,
    FAIL,
    NEEDS_HUMAN,
    NOT_VERIFIABLE,
    PASS,
    SEVERITY,
    out,
    worst,
)

# TC tu danh dau dong nay chua co spec: "[TBD - spec chua neu]", "[Assume ...]",
# "[Inferred ...]". Chua co chuan thi khong ai sai - cham la cham voi mot ky
# vong do chinh nguoi viet TC doan ra.
TBD_RE = re.compile(r"\[\s*(?:tbd|assume|inferred|todo)|spec ch[ưu]a n[êe]u|ch[ưu]a c[óo] spec", re.I)

NO_CRASH_RE = re.compile(r"kh[oô]ng\s+(?:b[ịi]\s+)?crash|not\s+crash|no\s+crash", re.I)
# Dong ta UI: "Popup hien thi", "Title can giua", "Button X o goc phai tren"...
UI_RE = re.compile(r"hi[ểe]n\s*th[ịi]|popup|pop-up|button|n[úu]t|title|subtitle|"
                   r"m[àa]n\s|icon|layout|c[ăa]n\s*gi[ữu]a|g[óo]c\s", re.I)
QUOTED_RE = re.compile(r"[\"“”']([^\"“”']{2,60})[\"“”']")
# "KHONG hien thi icon SWIPE" - phu dinh cua mot phan tu UI.
NOT_SHOW_RE = re.compile(r"kh[oô]ng\s+(?:c[óo]\s+)?(?:hi[ểe]n|th[ấa]y|xu[ấa]t hi[ệe]n)", re.I)


def check(line: str, ads: dict, drive: dict, crash: dict, rc_keys=()) -> dict:
    """Cham mot dong Expected -> {verdict, reason, actual}."""
    text = " ".join((line or "").split())
    if not text:
        return out(NOT_VERIFIABLE, "dòng trống", "")

    if TBD_RE.search(text):
        return out(NOT_VERIFIABLE,
                   "TC tự đánh dấu dòng này là chưa có spec — không có chuẩn để chấm", text)

    if NO_CRASH_RE.search(text):
        if crash.get("crashed"):
            return out(FAIL, "app crash trong lượt chạy", crash.get("lines", [])[:3])
        return out(PASS, "không thấy crash nào của app trong buffer crash", "")

    kind = assert_ads.ad_type_in(text) or assert_ads.type_from_position(text, rc_keys)
    if kind or assert_ads.routes(text):
        return assert_ads.ad_line(text, kind, ads, drive)

    quoted = QUOTED_RE.search(text)
    if quoted:
        return _text_on_screen(quoted.group(1), drive)

    # Ten goi cua nguoi ("icon SWIPE") -> node tren cay UI (data/ui_names.yaml).
    element = ui_names.find_in(text)
    if element:
        return _element_on_screen(element, text, drive)

    if UI_RE.search(text) and not assert_ads.tapped(drive):
        # Dong ta UI cua man phai lai toi, ma tool chua tap gi -> van o man mo dau.
        # Goi la "khong do duoc" la sai: do duoc, chi la chua toi noi.
        where = assert_ads.where(drive) or "màn mở đầu"
        return out(NEEDS_HUMAN,
                   f"dòng này tả UI của màn cần lái tới, tool mới dừng ở {where}", text)
    return out(NOT_VERIFIABLE, "dòng này phải nhìn mắt mới kết luận được (design/màu/animation)", text)


def _text_on_screen(wanted: str, drive: dict) -> dict:
    """Chu co xuat hien tren man hinh nao da chup khong."""
    steps = drive.get("steps") or []
    if not steps:
        return out(NEEDS_HUMAN, f"chưa lái tới màn nào để tìm {wanted!r}", "")
    want = wanted.casefold()
    for step in steps:
        if want in (step.get("dump") or "").casefold():
            return out(PASS, f"thấy {wanted!r} ở bước {step['n']}", step.get("activity", ""))
    if drive.get("blocked_steps"):
        # Dump la UI quang cao, khong phai app -> nguoi dong ad roi chay lai.
        return out(
            NEEDS_HUMAN,
            f"không thấy {wanted!r} vì màn hình bị quảng cáo che ở bước {drive['blocked_steps']} "
            "— đóng quảng cáo rồi chạy lại",
            "",
        )
    if not assert_ads.tapped(drive):
        # Chua tap gi thi van dang o man mo dau: khong thay chu cua MAN KHAC la
        # duong nhien, khong phai app thieu.
        return out(
            NEEDS_HUMAN,
            f"không thấy {wanted!r}, nhưng tool chưa lái tới màn nào khác "
            f"(đang ở {assert_ads.where(drive) or 'màn mở đầu'})",
            "",
        )
    return out(FAIL, f"không thấy {wanted!r} trên màn hình nào đã chụp", "")


def _element_on_screen(element: dict, text: str, drive: dict) -> dict:
    """Phan tu UI co tren man da chup khong. Cau phu dinh thi dao ky vong."""
    if not (drive.get("steps") or []):
        return out(NEEDS_HUMAN, f"chưa lái tới màn nào để tìm {element['name']}", "")
    if not assert_ads.tapped(drive):
        return out(NEEDS_HUMAN,
                   f"chưa lái tới màn cần xem {element['name']} "
                   f"(đang ở {assert_ads.where(drive) or 'màn mở đầu'})", "")
    hit = ui_names.seen_in(element, [s.get("dump", "") for s in drive["steps"]])
    want_absent = bool(assert_ads.NEGATIVE_RE.search(text) or NOT_SHOW_RE.search(text))
    if want_absent:
        if hit:
            return out(FAIL, f"vẫn thấy {element['name']} trên màn ({hit})", hit)
        return out(PASS, f"không thấy {element['name']} trên màn — đúng kỳ vọng", "")
    if hit:
        return out(PASS, f"thấy {element['name']} trên màn ({hit})", hit)
    return out(FAIL, f"không thấy {element['name']} trên màn đã chụp", "")


def check_all(expects, ads: dict, drive: dict, crash: dict, rc_keys=()) -> dict:
    """Cham ca case -> {verdict, lines: [...]}"""
    lines = []
    for index, line in enumerate(expects, 1):
        row = check(line, ads or {}, drive or {}, crash or {}, rc_keys)
        lines.append({"n": index, "expected": " ".join(line.split()), **row})
    if not lines:
        return {"verdict": NOT_VERIFIABLE, "lines": [], "note": "case không có dòng Expected nào"}

    # Verdict case = muc xau nhat trong cac dong DO DUOC. Dong chua do duoc
    # (can nguoi / phai nhin mat) khong keo ca case xuong: chung khong noi gi ve
    # app, chi noi ve gioi han cua tool. So dong do di kem de khong ai tuong case
    # da duoc cham tron ven.
    measured = [r["verdict"] for r in lines if r["verdict"] in (PASS, FAIL)]
    pending = len(lines) - len(measured)
    verdict = worst(measured) if measured else worst(r["verdict"] for r in lines)
    return {"verdict": verdict, "lines": lines, "measured": len(measured), "pending": pending}
