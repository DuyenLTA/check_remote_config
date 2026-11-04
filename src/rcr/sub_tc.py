"""Bo TC check sub Android (sheet `SUB_Android`, tab `TC Sub Android`) -> danh sach case + lich chay.

Sheet chung cho moi app (user chot 04/11/2026): cot N°, Feature, Test Description, Sub-scenario, Precondition,
Action, Expected Result. Dong bat dau bang "▌" la tieu de nhom; o Feature / Test Description de trong la ke thua
dong tren (merge cell). Doc theo TEN cot o dong tieu de, khong theo vi tri - sheet them cot van doc dung.

Moi case duoc gan:
- `can`: dieu kien ngoai app - "may_2" (thiet bi thu 2 cung tai khoan), "tai_khoan_2" (tai khoan Google thu 2),
  "nguoi" (refund qua ASO...), "play_console" (Grace Period / Account Hold phai bat san), "" khi tu chay duoc.
- `bat_dau`: trang thai tai khoan can co truoc case - "chua_mua" | "active" | "da_cancel" | "het_han" |
  "grace" | "hold" - de xep lich: case cung trang thai chay lien nhau, do phai mua / cho het ky nhieu lan.
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

LINK = "https://docs.google.com/spreadsheets/d/1q1fhu11wcpwAxbN_v7ZvRHtzgr3Uq-_N2ofKTp4ayw4/edit"
TAB = "TC Sub Android"
COT = {"so": "n°", "nhom": "feature", "mo_ta": "test description", "kich_ban": "sub-scenario",
       "precondition": "precondition", "action": "action", "expected": "expected result"}
# Thu tu trang thai trong mot vong: mua -> dung -> cancel -> het han. Case "grace"/"hold" can doi the luc gia han,
# xep cuoi vi lam hong gia han cua cac case khac.
THU_TU = ("chua_mua", "active", "da_cancel", "het_han", "grace", "hold")


def _khong_dau(s: str) -> str:
    s = unicodedata.normalize("NFD", s or "").replace("đ", "d").replace("Đ", "D")
    return "".join(c for c in s if unicodedata.category(c) != "Mn").lower()


def phan_loai_can(c: dict) -> str:
    """Dieu kien ngoai app ma case can (rong = tu chay duoc tren 1 may, 1 tai khoan)."""
    t = _khong_dau(" ".join(str(c.get(k) or "") for k in ("kich_ban", "precondition", "action")))
    if "aso" in re.findall(r"[a-z]+", t):
        return "nguoi"
    if "thiet bi b" in t or "thiet bi khac" in t or "thiet bi moi" in t:
        return "may_2"
    if "doi tai khoan" in t or "tai khoan google tren play store sang" in t:
        return "tai_khoan_2"
    if "play console da bat" in t:
        return "play_console"
    return ""


def trang_thai_dau(c: dict) -> str:
    """Trang thai tai khoan precondition doi hoi."""
    t = _khong_dau(c.get("precondition") or "")
    if "account hold" in t:
        return "hold"
    if "grace period" in t:
        return "grace"
    if "da cancel nhung chua het" in t:
        return "da_cancel"
    if "da het han" in t or "vua het han" in t or "bi revoke" in t:
        return "het_han"
    if "khong co sub active" in t or "chua mua" in t or "user free" in t:
        return "chua_mua"
    if re.search(r"da mua|sub active|da premium|dang co goi|co sub active|gui order id|sap het chu ky", t):
        return "active"
    return "chua_mua"


def _o(v) -> str:
    """Gia tri o -> chu. So nguyen tu xlsx doc ra float (1.0) -> "1"."""
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v if v is not None else "").strip()


def doc_bang(rows: list[list]) -> list[dict]:
    """Cac dong cua tab (gia tri tho) -> danh sach case."""
    hang_tieu_de = next((i for i, r in enumerate(rows) if r and _o(r[0]).lower() == COT["so"]), None)
    if hang_tieu_de is None:
        raise ValueError(f"không thấy dòng tiêu đề có cột {COT['so']!r}")
    ten = [_o(x).lower() for x in rows[hang_tieu_de]]
    vi_tri = {k: ten.index(v) for k, v in COT.items() if v in ten}
    thieu = [v for k, v in COT.items() if k not in vi_tri]
    if thieu:
        raise ValueError(f"tab thiếu cột: {thieu}")
    ra, nhom, mo_ta = [], "", ""
    for r in rows[hang_tieu_de + 1:]:
        o = lambda k: _o(r[vi_tri[k]]) if vi_tri[k] < len(r) else ""  # noqa: E731
        dau = _o(r[0]) if r else ""
        if dau.startswith("▌") or dau.startswith("▶"):     # tieu de nhom / bao cao coverage
            nhom = mo_ta = ""
            if dau.startswith("▶"):
                break
            continue
        if not dau or not o("action"):
            continue
        nhom, mo_ta = o("nhom") or nhom, o("mo_ta") or mo_ta
        c = {"so": dau, "nhom": nhom, "mo_ta": mo_ta, "kich_ban": o("kich_ban"),
             "precondition": o("precondition"), "action": o("action"), "expected": o("expected")}
        c["can"], c["bat_dau"] = phan_loai_can(c), trang_thai_dau(c)
        c["suy_doan"] = "[inferred" in c["expected"].lower()       # Expected chua chot voi spec
        ra.append(c)
    return ra


def doc_file(path: str | Path, tab: str = TAB) -> list[dict]:
    import openpyxl

    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        if tab not in wb.sheetnames:
            raise ValueError(f"file không có tab {tab!r} (có: {wb.sheetnames})")
        return doc_bang([list(r) for r in wb[tab].iter_rows(values_only=True)])
    finally:
        wb.close()


def tai(out_dir: Path, link: str = LINK, tab: str = TAB) -> list[dict]:
    """Tai sheet ve (ban moi nhat) roi doc. Mang loi -> dung ban da tai lan truoc neu co."""
    from . import tc_source
    from .models import RcError

    try:
        path = tc_source.tai_ve(link, out_dir)
    except RcError:
        path = tc_source.file_da_tai(link, out_dir)
        if path is None:
            raise
    return doc_file(path, tab)


def lich(cases: list[dict], chon: set[str] | None = None) -> list[dict]:
    """Thu tu chay: theo trang thai dau (THU_TU), giu thu tu sheet trong cung trang thai. Case `can` khac rong van
    nam trong lich (driver tu kiem du may / tai khoan chua, thieu thi ghi can test tay)."""
    cac = [c for c in cases if chon is None or c["so"] in chon]
    return sorted(cac, key=lambda c: THU_TU.index(c["bat_dau"]))
