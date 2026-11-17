"""Key Remote Config ghi trong cot Ad description cua muc IAA (ngoai cap `show_<ten>` bat/tat vi tri).

User chot 17/11/2026 (AIP921 `free_scan_nutrition_limit_per_day`...): cot Ad description co key RC nao thi phai
check het - doi gia tri key do roi xem app co an key khong (soi DEX + config tren may nhan dung gia tri moi).
Truoc day tool chi bat/tat `show_*`, cac key nay chi nam trong cau Expected nen khong ai doi.
"""

from __future__ import annotations

import re

# `free_scan_nutrition_limit_per_day = 3`, `reward_amount: 2` - ten key snake_case co it nhat mot `_`.
KEY_GIA_TRI_RE = re.compile(r"\b([a-z][a-z0-9]*(?:_[a-z0-9]+)+)\s*[=:]\s*([^\s,;()]+)")
SO_RE = re.compile(r"-?\d+")
SO_THUC_RE = re.compile(r"-?\d+\.\d+")


def gia_tri_khac(goc: str) -> str | None:
    """Gia tri moi khac han mac dinh de thay app co an key: so +1, true/false dao. Khong doan duoc -> None."""
    v = goc.strip().strip("'\"`.")
    if SO_RE.fullmatch(v):
        return str(int(v) + 1)
    if SO_THUC_RE.fullmatch(v):
        return str(float(v) + 1)
    if v.lower() in ("true", "false"):
        return "false" if v.lower() == "true" else "true"
    return None


def key_trong_mo_ta(mo_ta: str, bo_qua: set[str]) -> list[tuple[str, str, str | None]]:
    """[(key, gia tri ghi trong mo ta, gia tri moi de doi)] theo thu tu xuat hien, khong trung; bo key trong `bo_qua`
    (cap `show_*` cua cac vi tri - da co case bat/tat rieng)."""
    ra: dict[str, tuple[str, str, str | None]] = {}
    for m in KEY_GIA_TRI_RE.finditer(mo_ta or ""):
        key, goc = m.group(1), m.group(2).strip().strip("'\"`.")
        if key in bo_qua or key in ra:
            continue
        ra[key] = (key, goc, gia_tri_khac(goc))
    return list(ra.values())
