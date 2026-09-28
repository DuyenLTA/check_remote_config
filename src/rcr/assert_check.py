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

from . import assert_ads, assert_ui, ui_names
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

# "Icon la animation lap", "hieu ung chay lien tuc" - do bang cach chup vai
# khung roi so vung cua node, KHONG phai dong "phai nhin mat".
# "User co the vuot sang man ke tiep" - chung minh bang mot cu vuot that.
DOI_VUOT_RE = re.compile(
    r"(?:c[óo]\s*th[ểe]|\bcan\b|\bable\b).{0,20}(?:vu[ốo]t|swipe)|"
    r"(?:vu[ốo]t|swipe).{0,24}(?:sang|qua|t[ớo]i|to)\s*(?:m[àa]n|trang|next)", re.I)
ANIM_RE = re.compile(r"animation|animated|hi[ệe]u\s*[ứu]ng|l[ặa]p\s*l[ạa]i|\bl[ặa]p\b|loop|"
                     r"nh[áa]y|chuy[ểe]n\s*[đd][ộo]ng", re.I)
# "Luong FO thong suot", "flow tiep tuc binh thuong", "khong bi ket o man nao".
LUONG_RE = re.compile(r"(?:lu[ồo]ng|flow)\b.{0,30}(?:th[ôo]ng\s*su[ốo]t|m[ưu][ợo]t|"
                      r"ti[ếe]p\s*t[ụu]c|b[ìi]nh\s*th[ưu][ờo]ng|kh[ôo]ng\s*k[ẹe]t)|"
                      r"(?:th[ôo]ng\s*su[ốo]t|kh[ôo]ng\s*b[ịi]\s*k[ẹe]t)\b", re.I)
NO_CRASH_RE = re.compile(r"kh[oô]ng\s+(?:b[ịi]\s+)?crash|not\s+crash|no\s+crash", re.I)
# Dong ta UI: "Popup hien thi", "Title can giua", "Button X o goc phai tren"...
UI_RE = re.compile(r"hi[ểe]n\s*th[ịi]|popup|pop-up|button|n[úu]t|title|subtitle|"
                   r"m[àa]n\s|icon|layout|c[ăa]n\s*gi[ữu]a|g[óo]c\s", re.I)
QUOTED_RE = re.compile(r"[\"“”']([^\"“”']{2,60})[\"“”']")
# "Chuyen sang man Onboarding 3", "Vao man Home" - dong ta man hinh DEN duoc
# sau buoc cuoi. Do duoc bang activity dang focus, khong phai "phai nhin mat".
TOI_MAN_RE = re.compile(
    r"chuy[ểe]n\s*(?:sang|qua|t[ớo]i)|v[àa]o\s*m[àa]n|[đd]i\s*(?:[đd]ến|den|t[ớo]i)|"
    r"quay\s*(?:l[ạa]i|v[ềe])|hi[ểe]n\s*th[ịi]\s*m[àa]n|m[àa]n\s+\S+\s+hi[ểe]n\s*th[ịi]",
    re.I)


def check(line: str, ads: dict, drive: dict, crash: dict, rc_keys=(), scope: str = "",
          vi_tri=(), events=()) -> dict:
    """Cham mot dong Expected -> {verdict, reason, actual}.

    `scope` la vi tri unit ma ca case noi toi, cho dong khong tu nhac ten unit.
    """
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
        return assert_ads.ad_line(text, kind, ads, drive, scope, vi_tri)

    if LUONG_RE.search(text):
        ket = assert_ui.luong_thong(drive)
        if ket:
            return ket

    if DOI_VUOT_RE.search(text):
        ket = assert_ui.vuot_duoc(drive)
        if ket:
            return ket

    if assert_ui.EVENT_RE.search(text):
        ket = assert_ui.event_da_ban(text, events)
        if ket:
            return ket

    quoted = QUOTED_RE.search(text)
    if quoted:
        return assert_ui._text_on_screen(quoted.group(1), drive)

    # Ten goi cua nguoi ("icon SWIPE") -> node tren cay UI (data/ui_names.yaml).
    element = ui_names.find_in(text)
    # Cau doi animation cham truoc: no do duoc, con nhanh phan tu chi noi CO/KHONG.
    if ANIM_RE.search(text):
        ket = assert_ui._animation_cua(element, text, drive)
        if ket:
            return ket
    if element:
        return assert_ui._element_on_screen(element, text, drive)

    if TOI_MAN_RE.search(text):
        ket = assert_ui._man_da_toi(text, drive)
        if ket:
            return ket

    if UI_RE.search(text) and not assert_ads.tapped(drive):
        # Dong ta UI cua man phai lai toi, ma tool chua tap gi -> van o man mo dau.
        # Goi la "khong do duoc" la sai: do duoc, chi la chua toi noi.
        where = assert_ads.where(drive) or "màn mở đầu"
        return out(NEEDS_HUMAN,
                   f"dòng này tả UI của màn cần lái tới, tool mới dừng ở {where}", text)
    return out(NOT_VERIFIABLE, "dòng này phải nhìn mắt mới kết luận được (design/màu/animation)", text)


def check_all(expects, ads: dict, drive: dict, crash: dict, rc_keys=(), overrides=(),
              events=()) -> dict:
    """Cham ca case -> {verdict, lines: [...]}"""
    lines = []
    # Vi tri unit cua ca case: dong "Impressions = 0" khong tu nhac ten unit,
    # ten no nam o dong Expected phia tren.
    scope = assert_ads.case_position(expects)
    # Cau phu dinh chung chung noi ve cac vi tri chinh case nay bat/tat.
    vi_tri = assert_ads.vi_tri_cua_case(overrides)
    for index, line in enumerate(expects, 1):
        row = check(line, ads or {}, drive or {}, crash or {}, rc_keys, scope, vi_tri, events)
        lines.append({"n": index, "expected": " ".join(line.split()), **row})
    if not lines:
        return {"verdict": NOT_VERIFIABLE, "lines": [], "note": "case không có dòng Expected nào"}

    measured = [r["verdict"] for r in lines if r["verdict"] in (PASS, FAIL)]
    # Dong cua PO khong tinh vao "can nguoi": tester khong vao duoc AdMob console
    # nen bao ho di lam la bao sai viec. Van hien trong report, chi dem rieng.
    po = sum(1 for r in lines if r.get("scope") == "po")
    pending = len(lines) - len(measured) - po
    # Verdict case = muc xau nhat trong MOI dong (tru dong cua PO). Truoc day
    # dong chua do duoc bi loai ra, nen mot case chi cham duoc dong "khong
    # crash" van ra PASS trong khi dong quyet dinh khong ai cham - PASS hut
    # (do 2026-09-28, case 17 va 18: 2/3 dong NOT_VERIFIABLE ma case bao PASS).
    ke = [r["verdict"] for r in lines if r.get("scope") != "po"]
    verdict = worst(ke) if ke else worst(r["verdict"] for r in lines)
    return {"verdict": verdict, "lines": lines, "measured": len(measured),
            "pending": pending, "po": po}
