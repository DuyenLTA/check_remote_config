"""Cham cac dong Expected noi ve MAN HINH: chu, phan tu, man da toi, animation.

Tach khoi `assert_check` de moi file duoi 200 dong: `assert_check` phan loai
dong va goi, file nay lo phan doc bang chung tu dump/anh da chup.
"""

from __future__ import annotations

import re

from . import assert_ads, fo_screens, ui_names

# "KHONG hien thi icon SWIPE" - phu dinh cua mot phan tu UI.
NOT_SHOW_RE = re.compile(r"kh[oô]ng\s+(?:c[óo]\s+)?(?:hi[ểe]n|th[ấa]y|xu[ấa]t hi[ệe]n)", re.I)

from .verdict_levels import FAIL, NEEDS_HUMAN, PASS, out

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


def _man_da_toi(text: str, drive: dict) -> dict | None:
    """Dong "chuyen sang man X" -> so voi man dang focus SAU buoc cuoi.

    `None` khi cau khong neu man nao trong bo luat - de cac nhanh sau xu ly.
    """
    target = fo_screens.target_for(text)
    if not target:
        return None
    cuoi = drive.get("final") or {}
    activity = cuoi.get("activity") or ""
    if not activity:
        return out(NEEDS_HUMAN, "chưa chụp được màn sau bước cuối nên không đối chiếu được", text)
    ten, _, trang = target.partition("#")
    gon = activity.split(".")[-1]
    if ten not in activity:
        return out(FAIL, f"sau bước cuối đang ở {gon}, không phải {target}", gon)
    if trang:
        # Cac trang OB dung chung activity -> phan biet bang cham chi trang.
        now = cuoi.get("page") or 0
        if not now:
            return out(NEEDS_HUMAN, f"đang ở {gon} nhưng không đọc được đang ở trang thứ mấy", gon)
        # Trang suy ra (OB3 khong co cham chi trang) phai noi ro trong ly do:
        # nguoi doc can biet so nay do duoc hay tinh ra.
        cach = (" (suy từ trang đo được + số lần vuốt, màn đã đổi thật)"
                if cuoi.get("page_nguon") == "suy_ra" else "")
        if str(now) != trang:
            return out(FAIL, f"đang ở {gon} trang {now}, kỳ vọng trang {trang}{cach}",
                       f"{gon} trang {now}")
        return out(PASS, f"sau bước cuối đang ở {gon} trang {now} — đúng kỳ vọng{cach}",
                   f"{gon} trang {now}")
    return out(PASS, f"sau bước cuối đang ở {gon} — đúng kỳ vọng", gon)


def _animation_cua(element: dict | None, text: str, drive: dict) -> dict | None:
    """Dong doi phan tu phai la animation -> doc ket qua da do luc lai may.

    Cau thuong KHONG nhac ten phan tu ("Icon la animation lap, goi y ro huong
    vuot ngang") nen khong tra ra `element` nao. Luc do: man chi co DUNG MOT
    node animation thi lay no; nhieu node thi khong doan, tra None.
    """
    do_duoc: dict[str, dict] = {}
    for buoc in drive.get("steps") or ():
        for node_id, ket in (buoc.get("anim") or {}).items():
            if ket and not ket.get("loi"):
                do_duoc.setdefault(node_id, ket)
    if not do_duoc:
        return None
    if element:
        node_id = next((i for i in element.get("ids", []) if i in do_duoc), "")
    else:
        node_id = next(iter(do_duoc)) if len(do_duoc) == 1 else ""
    if not node_id:
        return None

    ket = do_duoc[node_id]
    ten = (element or {}).get("name") or node_id
    if not ket["doi"]:
        return out(FAIL, f"{ten} đứng yên giữa các khung chụp (lệch tối đa "
                         f"{ket.get('lech_max', 0)}/255) — không phải animation", node_id)
    so = ket.get("so_khung", 0)
    if re.search(r"l[ặa]p|loop|li[êe]n\s*t[ụu]c", text, re.I) and not ket["lap"]:
        return out(FAIL, f"{ten} chạy rồi dừng hẳn — {so} khung cuối đứng yên "
                         f"(lệch {ket.get('lech_cuoi', 0)}/255), không phải animation lặp",
                   node_id)
    return out(PASS, f"{ten} chuyển động suốt {so} khung chụp, không dừng lại "
                     f"(lệch tối đa {ket.get('lech_max', 0)}/255)", node_id)
