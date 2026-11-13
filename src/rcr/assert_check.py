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

from . import (ad_positions, assert_ad_area, assert_ad_theo_id, assert_ad_screen, assert_bo_cuc, assert_chu, assert_indicator,
               assert_giu_nguyen, assert_khong_co_ad, assert_luong_ad, assert_nut_lfo, assert_resume,
               assert_man_khong, assert_qa_man_tat_hung_202,
               assert_anh_content, assert_mau, assert_ads, assert_splash_media, assert_tag,
               assert_checkin, assert_rating, assert_timing, assert_trong_luc, assert_ui, assert_widget, ui_names)
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
# "Vuot chuyen man khong vuot duoc chi bam Next moi sang man khac" (TC 3.6.2 R01-09, AIP862 11/11/2026): ky vong
# NGUOC - vuot thu ma man dung yen moi la dung. Truoc day cham nhu "co the vuot" -> FAIL gia.
KHONG_VUOT_RE = re.compile(r"kh[ôo]ng\s+(?:th[ểe]\s+)?vu[ốo]t\s*(?:đ[ưu][ợo]c|sang|qua)|"
                           r"ch[ỉi]\s+(?:c[óo]\s+)?b[ấa]m\s+next|\bcan(?:no|')t\s+swipe", re.I)
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
    r"chuy[ểe]n\s*(?:sang|qua|t[ớo]i)|v[àa]o\s*m[àa]n|v[àa]o\s+(?:th[ẳa]ng\s+)?home\b|[đd]i\s*(?:[đd]ến|den|t[ớo]i)|"
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

    # Tab widget: widget tren launcher, toast, popup dong, mo app tu widget - cham bang bang chung buoc widget.
    ket = assert_widget.cham(text, drive or {}, cfg)
    if ket:
        return ket
    # Tab rating: popup / sao / nut Rate / X / thoat app / shortcut - cham bang bang chung buoc rating (act_rating).
    ket = assert_rating.cham(text, drive or {})
    if ket:
        return ket
    # Tab daily checkin: man Check-in / Unlocked / sheet unlock / gen free / event - bang chung buoc act_checkin.
    ket = assert_checkin.cham(text, drive or {}, cfg)
    if ket:
        return ket

    # Dong ve THOI GIAN / nut X tren trang native full OB3: cham bang dong thoi
    # gian do duoc (log co moc ms + khung nhin lien tuc), khong day cho nguoi.
    req_303 = [u["unit"] for u in (ads.get("units") or {}).values()
               if u.get("requested") and ad_positions._khop_vi_tri(u, "303")]
    # Unit CHI cua 303 (da tach khoi unit gop duoi ID - ad_tach_id) co load: 303 co ve, khong phai khong fill.
    co_ve_303 = any(u.get("loaded") and {m[0] for k in (u.get("rc_keys") or ())
                                         if (m := assert_ad_screen._man_cua_key(k))} == {"303"}
                    for u in (ads.get("units") or {}).values())
    ket = assert_timing.cham(text, (drive or {}).get("timeline"), dict(cfg or {}), req_303, co_ve_303)
    if ket:
        return ket

    # "Version Lib Ads = 1.2.10": doc tu log tag da xem o buoc "Xem logcat tag ...".
    ket = assert_tag.cham(text, drive or {})
    if ket:
        return ket

    # Nen splash theo media_url (anh phu kin / GIF lap / GIF mot lan) va "progress + inter splash".
    ket = (assert_splash_media.cham_nen(text, drive or {})
           or assert_splash_media.cham_progress(text, list((ads.get("units") or {}).values()), drive or {}))
    if ket:
        # "Nen GIF chay 1 lan ..., sub_title 'Gif once'": chu trong ngoac cung phai cham.
        return _gop(ket, assert_chu.cham(text, drive or {}, bo_hinh_dong=True), text)

    # "Trong luc X dang hien thi: ..." - X khong show thi ve sau dung mot cach vo nghia.
    ket = assert_trong_luc.cham(text, list((ads.get("units") or {}).values()))
    if ket:
        return ket
    # Ad resume (501 AOA / 502 native full / 503 inter) khi mo lai app - truoc day roi xuong "phai nhin mat".
    ket = assert_resume.cham(text, ads, drive or {})
    if ket:
        return ket
    # Nut Next / tick man ngon ngu (buttonLanguageNext + ban tay lottieHandPoint) - khong phai nut Next cua OB.
    ket = assert_nut_lfo.cham(text, drive or {})
    if ket:
        return ket
    # Luong man quanh quang cao: sang Inter Splash, dong inter -> sang man X, chay lai tu Splash, Inter Splash 2,
    # Question chua chon (an CTA + ban tay).
    # "Item da chon giu nguyen", "native X giu nguyen, khong reload": chi ket luan khi bang chung chac.
    # Chay chuoi: "khong reload" phai xet ca lich su chuoi (log rieng case khong co lan load dau tien).
    ket = assert_giu_nguyen.cham(text, list((ads.get("units_don") or ads.get("units") or {}).values()), drive or {})
    if ket:
        return ket
    ket = assert_luong_ad.cham(text, list((ads.get("units") or {}).values()), drive or {}, events)
    if ket:
        return ket
    # "Khong co native ad, hien thi icon SWIPE + text 'Swipe to next'": ve ad o vi tri case tat + ve chu.
    ket = assert_khong_co_ad.cham(text, list((ads.get("units") or {}).values()), cfg)
    if ket:
        chu = assert_chu.cham(text, drive or {})
        return ket if not chu else out(worst([ket["verdict"], chu["verdict"]]),
                                       f"{ket['reason']}; {chu['reason']}", text)

    # "Khong hien thi man Question ..., vao thang Home".
    ket = assert_man_khong.cham(text, drive or {}, events) or assert_indicator.cham(text, drive or {})
    if ket:
        return ket

    # "Vi tri X co / KHONG show tai man Y" (Y khong phai man cua X): cham bang
    # event ad_show gan man, khong bang request - request o man nha la dung cho.
    # Luat QA 05/11/2026 nguoc cau chu TC: "hung 202" sang man OB dau, man tat van load ad.
    ket = assert_qa_man_tat_hung_202.cham(text, events, list((ads.get("units") or {}).values()), cfg)
    if ket:
        return ket
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

    # Vi tri cum progress/nhan so voi native/banner/man hinh: cham bang bounds. Phai truoc
    # luat ads - cau co chu "native" nhung hoi vi tri, khong hoi request.
    ket = assert_bo_cuc.cham(text, drive or {})
    if ket:
        # Dong vua hoi vi tri vua hoi mau ("dong 'X' mau #888 tren progress"): cham ca hai, xau nhat thang.
        return _gop(ket, assert_mau.cham(text, drive or {}, cfg), text)
    ket = assert_mau.cham(text, drive or {}, cfg)
    if ket:
        # "Nen text #F5F5F5, button 'FR - Next', slider mau #1565C0, anh content OB1": ma mau chi la mot phan -
        # chu trong ngoac va anh content cung phai cham, khong thi PASS chi nho phan mau (AIP886 R01-03).
        return _gop(_gop(ket, assert_chu.cham(text, drive or {}), text),
                    assert_anh_content.cham(text, drive or {}, cfg), text)

    # "Layout theo layout_X": cau co chu native nhung hoi BO CUC, cham bang cay UI.
    bo_cuc = ui_names.find_in(text)
    if bo_cuc and bo_cuc.get("ids_all"):
        return assert_ui.layout_tren_man(bo_cuc, drive or {})

    kind = assert_ads.ad_type_in(text) or assert_ads.type_from_position(text, rc_keys)
    if not kind and scope and assert_ads.LOG_ADS_RE.search(text):
        ket = assert_ads.log_cua_vi_tri(text, ads, scope)
        if ket:
            return ket
    ket = assert_trong_luc.hien_thi_tron(text, don_vi, kind)
    if ket:
        return ket
    if kind or assert_ads.routes(text):
        return assert_ads.ad_line(text, kind, ads, drive, scope, vi_tri, cfg)

    if LUONG_RE.search(text):
        ket = assert_ui.luong_thong(drive)
        if ket:
            return ket

    # "Icon la animation lap, goi y huong vuot ngang theo huong chuyen man":
    # cau hoi icon CO CHUYEN DONG khong; chu "vuot ... chuyen man" chi ta huong
    # goi y. Cham bang cu vuot la PASS ma khong ai do animation (do 2026-10-06).
    # Bo chu trong ngoac truoc: "Text 'Swipe to next' dung mau primary" la chu tren UI, khong phai doi vuot
    # (AIP886 R04-01: tool vuot thu roi PASS, mau khong ai do).
    if DOI_VUOT_RE.search(QUOTED_RE.sub("", text)) and not ANIM_RE.search(text):
        ket = assert_ui.vuot_duoc(drive, phai_vuot=not KHONG_VUOT_RE.search(text))
        if ket:
            return ket

    if assert_ui.EVENT_RE.search(text):
        ket = assert_ui.event_da_ban(text, events)
        if ket and ket["verdict"] == FAIL and ket["reason"].startswith("không thấy event") \
                and not assert_ads.tapped(drive):
            # Tool chua lam buoc nao toi man ban event (vd chua gen anh de toi Result) -> vang event la do CHUA
            # TOI, khong phai app thieu event. FAIL o day la FAIL gia (AIP892 rating R01-02/03/05 12/11/2026).
            where = assert_ads.where(drive) or "màn mở đầu"
            return out(NEEDS_HUMAN, f"{ket['reason']} — nhưng tool mới dừng ở {where}, chưa lái tới chỗ bắn "
                                    "event: đo tay", text)
        if ket:
            return ket

    ket = assert_chu.cham(text, drive)
    if ket:
        # "Bam 'FR - Go' → vao Home": chu co hien CHUA DU - ve man dich cung phai dung (AIP886 O01-02).
        man = assert_ui._man_da_toi(text, drive) if TOI_MAN_RE.search(text) else None
        if man:
            return out(worst([ket["verdict"], man["verdict"]]), f"{ket['reason']}; {man['reason']}", text)
        return ket

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
    return out(NOT_VERIFIABLE, "dòng này phải nhìn mắt mới kết luận được (design/màu/animation)", text,
               tinh=True)


def _gop(a: dict, b: dict | None, text: str) -> dict:
    """Ghep hai ket qua cham cua cung mot dong (muc xau nhat thang)."""
    if not b:
        return a
    return out(worst([a["verdict"], b["verdict"]]), f"{a['reason']}; {b['reason']}", text)


def check_all(expects, ads: dict, drive: dict, crash: dict, rc_keys=(), overrides=(),
              events=()) -> dict:
    """Cham ca case -> {verdict, lines: [...]}"""
    lines = []
    # Vi tri unit cua ca case: dong "Impressions = 0" khong tu nhac ten unit,
    # ten no nam o dong Expected phia tren.
    scope = assert_ads.case_position(expects)
    # Cau phu dinh chung chung noi ve cac vi tri chinh case nay bat/tat.
    vi_tri = assert_ads.vi_tri_cua_case(overrides)
    # ID ads ghi thang trong case (bo IAA): cham theo dung ID, khong theo ma vi tri.
    so_case = sorted({s for line in expects for s in assert_ad_theo_id.ids_trong(line)})
    units = list(((ads or {}).get("units") or {}).values())
    for index, line in enumerate(expects, 1):
        row = None
        if so_case:
            if assert_ad_theo_id.ids_trong(line):
                row = assert_ad_theo_id.cham(line, units, drive or {})
            elif assert_ads.ad_type_in(line) and not ad_positions._position_token(line):
                row = assert_ad_theo_id.cham_theo_case(
                    line, units, drive or {}, so_case, bool(assert_ads.NEGATIVE_RE.search(line)))
        if row is None:
            row = check(line, ads or {}, drive or {}, crash or {}, rc_keys, scope, vi_tri, events,
                        overrides if isinstance(overrides, dict) else None)
        lines.append({"n": index, "expected": " ".join(line.split()), **row})
    if not lines:
        return {"verdict": NOT_VERIFIABLE, "lines": [], "note": "case không có dòng Expected nào"}
    lines = _ha_fail_khi_log_roi(lines, (ads or {}).get("log_roi") or 0)
    lines = _ha_fail_khi_buoc_dung(lines, drive or {})

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


# FAIL dua tren VANG MAT dong log ("khong co request ...") khong dung duoc khi may da bo dong log cua app.
KHONG_THAY_LOG_RE = re.compile(r"(không|chưa) có request", re.I)


def _ha_fail_khi_log_roi(lines: list[dict], roi: int) -> list[dict]:
    """ROM vivo gioi han 50 dong log/giay moi tien trinh, bo ca dong `AdEventLogger` luc app khoi dong
    (V2143 12/11/2026: inter 102 co load+show ma 0 request). Log da roi thi "khong co request" khong chung minh
    duoc app khong request -> NEEDS_HUMAN de do tay, khong bao bug gia."""
    if not roi:
        return lines
    ra = []
    for r in lines:
        if r.get("verdict") == FAIL and KHONG_THAY_LOG_RE.search(str(r.get("reason") or "")):
            r = {**r, "verdict": NEEDS_HUMAN,
                 "reason": f"máy bỏ {roi} dòng log của app (ratelimit ROM) — chưa kết luận được vắng request: "
                           f"{r.get('reason')}"}
        ra.append(r)
    return ra


def _ha_fail_khi_buoc_dung(lines: list[dict], drive: dict) -> list[dict]:
    """Tool dung giua cac buoc Action (buoc khong dich duoc, vd "Gen anh, cho popup.") -> chua toi man cua dong
    Expected. FAIL dua tren VANG MAT ("khong thay 'Rate' tren man nao da chup", "khong thay event ...") la FAIL
    gia -> NEEDS_HUMAN (AIP892 rating R03-01 12/11/2026). FAIL vi THAY sai van giu."""
    if drive.get("status") != "NEEDS_HUMAN":
        return lines
    buoc = drive.get("stopped_at")
    ra = []
    for r in lines:
        if r.get("verdict") == FAIL and str(r.get("reason") or "").startswith("không thấy"):
            r = {**r, "verdict": NEEDS_HUMAN,
                 "reason": f"tool dừng ở bước {buoc} (chưa làm được thao tác), chưa tới màn cần chấm: {r.get('reason')}"}
        ra.append(r)
    return ra


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
