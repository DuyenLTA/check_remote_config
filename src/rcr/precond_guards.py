"""Precondition doi mot DIEU KIEN MOI TRUONG - tool tao duoc hay khong?

VI SAO PHAI CO: case 22/23/24 cua bo TC 3.5.0 mo ta ba dieu kien khac han
nhau (simulate no-fill / chan mang toi ad server / throttle <=50kbps), nhung
neu tool khong tao dieu kien nao thi ca ba deu chay duoi DUNG MOT trang thai
that: ad duoc request roi tu khong fill. Ba case cung ra PASS, doc report
tuong da phu ba nhanh - that ra moi phu mot (do 2026-09-28).

Chia lam hai nhom, vi cach xu ly khac han nhau:
  EP_DUOC      - ep ad fail bang cach doi `id_*` sang mot unit khong ton tai.
                 Day la cach team QA van dung, khong phai meo moi.
  KHONG_EP_DUOC- throttle bang thong, mediation test mode: may khong root,
                 khong co proxy -> khong tao duoc. Case do KHONG duoc ra PASS.
"""

from __future__ import annotations

import re

# Dieu kien ep duoc: bat ad fail / khong fill / chan duong toi ad server.
EP_DUOC = (
    (re.compile(r"simulate\s+(?:admob\s+)?no[\s-]*fill|no[\s-]*fill\s+cho", re.I),
     "ép ad không fill"),
    (re.compile(r"ch[ặa]n\s+m[ạa]ng\s+[đd][ếe]n\s+ad\s*server|block\s+ad\s*server", re.I),
     "chặn đường tới ad server"),
    (re.compile(r"mock\s+.{0,20}(?:no[\s-]*fill|fail)|ep\s+unit\s+fail", re.I),
     "ép unit fail"),
)
# Dieu kien KHONG tao duoc tren may test hien tai.
KHONG_EP_DUOC = (
    (re.compile(r"throttle|m[ạa]ng\s+ch[ậa]m|\d+\s*kbps|charles\s*proxy", re.I),
     "throttle băng thông (máy không root, không có proxy)"),
    (re.compile(r"mediation\s+test\s+mode|mediation\s+inspector", re.I),
     "bật mediation test mode (tester không có quyền vào AdMob console)"),
    (re.compile(r"debug\s+menu|adb\s+root|thi[ếe]t\s*b[ịi]\s+root", re.I),
     "cần quyền root trên máy"),
)


def _khop(precondition: str, luat) -> list[str]:
    ra = []
    for dong in (precondition or "").splitlines():
        for mau, ten in luat:
            if mau.search(dong) and ten not in ra:
                ra.append(ten)
    return ra


def ep_duoc(precondition: str) -> list[str]:
    """Dieu kien tool CO THE tao bang cach doi config."""
    return _khop(precondition, EP_DUOC)


def khong_ep_duoc(precondition: str) -> list[str]:
    """Dieu kien tool KHONG tao duoc -> case khong duoc ra PASS im lang."""
    return _khop(precondition, KHONG_EP_DUOC)


# Slot khong ton tai trong tai khoan -> AdMob tra ERROR_CODE_INVALID_REQUEST,
# unit khong bao gio fill. Giu nguyen publisher that cua app: doi ca publisher
# thi request khong con di ve tai khoan dang test nua.
SLOT_KHONG_TON_TAI = "0000000001"


def khoa_ep_fail(vi_tri, configs: dict) -> dict[str, str]:
    """Cac key `id_*` can doi de ep unit cua `vi_tri` khong bao gio fill.

    Doi ID sang mot slot khong ton tai la cach team QA van dung de ep fail:
    request van di, van dem duoc trong log, nhung khong bao gio co ad tra ve.
    KHAC voi tat `show_*`: tat thi khong con request nao, con day la
    "co request, khong co fill" - dung trang thai ma case no-fill can.
    """
    ra = {}
    for token in vi_tri or ():
        khoa = f"id_{token}"
        goc = configs.get(khoa, "")
        if not goc.startswith("ca-app-pub"):
            continue
        ra[khoa] = goc.rsplit("/", 1)[0] + "/" + SLOT_KHONG_TON_TAI
    return ra


def da_khong_fill(units, vi_tri, khop) -> bool:
    """Quan sat co cho thay dieu kien "ad khong fill" da xay ra khong?

    Dieu kien dat hay khong la do TRANG THAI THAT, khong phai do ai gay ra no:
    may test von rat hay khong fill, va mot lan khong fill that con chac hon
    mot lan ep. Nhung phai KIEM, khong duoc mac dinh.
    """
    thuoc = [u for u in units if not vi_tri or any(khop(u, t) for t in vi_tri)]
    if not thuoc:
        return False
    return not any(u["loaded"] or u["shown"] for u in thuoc)
