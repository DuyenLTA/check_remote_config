"""Thoi gian chay tren report: tung case (`thoi_gian_s` run_batch ghi) va tong ca luot.

User theo doi toc do luot (03/11/2026: "note them thoi gian chay vao report"). Record cua luot cu (--gop,
truoc khi co do thoi gian) khong co `thoi_gian_s` -> khong tinh vao tong, ghi so case chua do.
"""

from __future__ import annotations


def ngan(giay) -> str:
    """75 -> '1:15', 3725 -> '1:02:05'. Khong co so -> ''."""
    if not isinstance(giay, (int, float)) or giay < 0:
        return ""
    g = int(round(giay))
    h, m, s = g // 3600, g % 3600 // 60, g % 60
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def the_tong(records: list[dict]) -> dict | None:
    """The "thoi gian chay" canh the PASS/FAIL tren report (user 03/11/2026: chi can tong, khong can tung case):
    {tong, tb, so, thieu}; khong case nao co so -> None (khong hien the)."""
    co = [r["thoi_gian_s"] for r in records if isinstance(r.get("thoi_gian_s"), (int, float))]
    if not co:
        return None
    return {"tong": ngan(sum(co)), "tb": ngan(sum(co) / len(co)), "so": len(co), "thieu": len(records) - len(co)}


def tong_luot(records: list[dict]) -> str:
    """'1:02:05 · TB 4:10/case (15 case)' ; case chua do thi ghi them; khong case nao co so -> '—'."""
    co = [r["thoi_gian_s"] for r in records if isinstance(r.get("thoi_gian_s"), (int, float))]
    if not co:
        return "—"
    tong = sum(co)
    ra = f"{ngan(tong)} · TB {ngan(tong / len(co))}/case ({len(co)} case)"
    thieu = len(records) - len(co)
    return ra + (f" · {thieu} case từ lượt cũ chưa đo" if thieu else "")
