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

from . import (ad_positions, assert_ad_area, assert_ad_screen, assert_ads, assert_timing, assert_ui,
               ui_names)
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
# Nhan "[Assume — ...]" / "[Inferred — ...]": bo nhan di la con ky vong cham duoc.
GIA_DINH_RE = re.compile(r"\[\s*(?:assume|inferred)[^\]]*\]", re.I)

# "Icon la animation lap", "hieu ung chay lien tuc" - do bang cach chup vai
# khung roi so vung cua node, KHONG phai dong "phai nhin mat".
# "User co the vuot sang man ke tiep" - chung minh bang mot cu vuot that.
DOI_VUOT_RE = re.compile(
    r"(?:c[óo]\s*th[ểe]|\bcan\b|\bable\b).{0,20}(?:vu[ốo]t|swipe)|"
    r"(?:vu[ốo]t|swipe).{0,24}(?:sang|qua|t[ớo]i|to|chuy[ểe]n)\s*(?:m[àa]n|trang|next)|"
    r"chuy[ểe]n\s+(?:đ[ưu][ợo]c\s+)?sang\s+m[àa]n.{0,20}(?:vu[ốo]t|swipe)", re.I)
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
          vi_tri=(), events=(), cfg=None) -> dict:
    """Cham mot dong Expected -> {verdict, reason, actual}.

    `scope` la vi tri unit ma ca case noi toi, cho dong khong tu nhac ten unit.
    """
    text = " ".join((line or "").split())
    if not text:
        return out(NOT_VERIFIABLE, "dòng trống", "")

    if TBD_RE.search(text):
        noi_dung = GIA_DINH_RE.sub("", text).strip(" .:")
        if TBD_RE.search(noi_dung) or not noi_dung:
            return _tbd(drive or {}, crash)
        # "[Assume]/[Inferred]": nguoi viet TC VAN ghi ky vong (doan theo
        # pattern) -> cham noi dung do nhu dong thuong, ghi chu la gia dinh.
        ket = check(noi_dung, ads, drive, crash, rc_keys, scope, vi_tri, events, cfg)
        return ket | {"reason": f"{ket['reason']} (kỳ vọng do TC giả định, chưa có spec)"}

    # Dong ve THOI GIAN / nut X tren trang native full OB3: cham bang dong thoi
    # gian do duoc (log co moc ms + khung nhin lien tuc), khong day cho nguoi.
    req_303 = [u["unit"] for u in (ads.get("units") or {}).values()
               if u.get("requested") and ad_positions._khop_vi_tri(u, "303")]
    ket = assert_timing.cham(text, (drive or {}).get("timeline"), dict(cfg or {}), req_303)
    if ket:
        return ket

    # "Vi tri X co / KHONG show tai man Y" (Y khong phai man cua X): cham bang
    # event ad_show gan man, khong bang request - request o man nha la dung cho.
    ket = assert_ad_screen.cham(text, events, list((ads.get("units") or {}).values()))
    if ket:
        return ket

    # Dong ve VUNG AD phai cham truoc luat "khong crash": cau "Phan ads khong
    # load duoc de TRONG (..., khong crash)" co ca hai ve, ma luat crash tra
    # ve ngay -> ve chinh (vung ad co trong khong) khong ai cham.
    don_vi = [u for u in (ads.get("units") or {}).values()]
    if assert_ad_area.VUNG_TRONG_RE.search(text):
        return assert_ad_area.vung_trong(
            text, don_vi, {}, crash, tuple(vi_tri), ad_positions._khop_vi_tri)
    ket = assert_ad_area.dieu_kien_ad(
        text, don_vi, {}, tuple(vi_tri), ad_positions._khop_vi_tri)
    if ket:
        return ket

    if NO_CRASH_RE.search(text):
        if crash.get("crashed"):
            return out(FAIL, "app crash trong lượt chạy", crash.get("lines", [])[:3])
        return out(PASS, "không thấy crash nào của app trong buffer crash", "")

    # "Layout theo layout_X": cau co chu native nhung hoi BO CUC, cham bang cay UI.
    bo_cuc = ui_names.find_in(text)
    if bo_cuc and bo_cuc.get("ids_all"):
        return assert_ui.layout_tren_man(bo_cuc, drive or {})

    kind = assert_ads.ad_type_in(text) or assert_ads.type_from_position(text, rc_keys)
    if not kind and scope and assert_ads.LOG_ADS_RE.search(text):
        ket = assert_ads.log_cua_vi_tri(text, ads, scope)
        if ket:
            return ket
    if kind or assert_ads.routes(text):
        return assert_ads.ad_line(text, kind, ads, drive, scope, vi_tri)

    if LUONG_RE.search(text):
        ket = assert_ui.luong_thong(drive)
        if ket:
            return ket

    # "Icon la animation lap, goi y huong vuot ngang theo huong chuyen man":
    # cau hoi icon CO CHUYEN DONG khong; chu "vuot ... chuyen man" chi ta huong
    # goi y. Cham bang cu vuot la PASS ma khong ai do animation (do 2026-10-06).
    if DOI_VUOT_RE.search(text) and not ANIM_RE.search(text):
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
        row = check(line, ads or {}, drive or {}, crash or {}, rc_keys, scope, vi_tri, events,
                    overrides if isinstance(overrides, dict) else None)
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


def _tbd(drive: dict, crash: dict) -> dict:
    """Dong TC tu danh dau TBD: spec chua chot nen KHONG co chuan dung/sai cho
    noi dung hien thi. Cham phan do duoc (app khong crash, man van ve UI cua
    app) va GHI LAI dung cai dang hien de PO chot - khong de dong treo lo lung.
    """
    if crash.get("crashed"):
        return out(FAIL, "spec chưa chốt (TBD) nhưng app crash trong lượt", crash.get("lines", [])[:3])
    vung = ui_names.find_in("vùng ad") or {}
    dumps = [st.get("dump", "") for st in drive.get("steps") or []]
    thay = ui_names.seen_in(vung, dumps) if vung else ""
    icon = ui_names.seen_in(ui_names.find_in("icon SWIPE") or {}, dumps)
    hien = ", ".join(x for x in (thay and f"vùng ad `{thay}`", icon and f"icon swipe `{icon}`") if x) \
        or "vùng ad để trống (không có view ad, không có icon swipe)"
    return out(PASS, f"spec chưa chốt (TBD) — app chạy bình thường, không crash; thực tế đang hiện: "
                     f"{hien}. Gửi PO chốt nội dung này", hien)
