"""Gop nhieu luot cua MOT case thanh mot the tren report.

Truoc day the case chi lay luot dau (`runs[0]`) trong khi verdict lay luot XAU
NHAT: case runtime `false → true → false` FAIL o luot 2 ma report chi hien
luot 1 toan PASS - nguoi doc khong tim duoc cho sai. Gio moi dong Expected,
moi buoc va moi unit ads deu mang nhan luot cua no.
"""

from __future__ import annotations

from .rc_variants import ABSENT


def nhan_luot(runs: list[dict]) -> list[str]:
    """Nhan tung luot theo gia tri KHAC nhau giua cac luot: "Lượt 2 (swipe_onb2=false)"."""
    if len(runs) <= 1:
        return [""] * len(runs)
    tat_ca = [r.get("overrides") or {} for r in runs]
    doi = [k for k in tat_ca[0] if len({str(o.get(k)) for o in tat_ca}) > 1]
    ra = []
    for i, o in enumerate(tat_ca, 1):
        cap = ", ".join(f"{k}={_hien(o.get(k))}" for k in doi)
        ra.append(f"Lượt {i}" + (f" ({cap})" if cap else ""))
    return ra


def overrides_gop(runs: list[dict]) -> dict[str, str]:
    """Key doi giua cac luot hien thanh chuoi `a → b → c`."""
    tat_ca = [r.get("overrides") or {} for r in runs] or [{}]
    keys = dict.fromkeys(k for o in tat_ca for k in o)
    ra = {}
    for k in keys:
        vals = [_hien(o.get(k)) for o in tat_ca]
        ra[k] = vals[0] if len(set(vals)) == 1 else " → ".join(vals)
    return ra


def gan_nhan(nhan: str, items: list[dict], field: str) -> list[dict]:
    """Them nhan luot vao dau `field` cua tung phan tu (khong doi khi chi 1 luot)."""
    if not nhan:
        return items
    return [{**it, field: f"{nhan}: {it.get(field, '')}"} for it in items]


def _hien(v) -> str:
    if v is None:
        return "(không đặt)"
    return "<absent> (xoá key)" if v == ABSENT else str(v)
