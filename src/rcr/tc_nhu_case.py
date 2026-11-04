"""Test Data ghi "key = <mo ta> (nhu R01)" thay vi dan gia tri: lay gia tri that cua `key` tu nhom case duoc nhac.

AIP936 RG10-01 03/11/2026: "onboard_config_content_new = JSON co khoi language_code=fr (nhu R01)". Truoc day tool
dung case nay (gia tri la cau mo ta); QA khong phai dan lai JSON dai neu tool tu lay dung gia tri cua nhom R01.
Khong tim thay case / key duoc nhac -> giu nguyen dong (rc_extract se dung case va bao ro).
"""

from __future__ import annotations

import dataclasses
import re

from . import rc_extract

NHU_RE = re.compile(r"\(\s*nh(?:ư|u)\s+([A-Z]{1,3}\d+(?:-\d+)?)\s*\)", re.I)
KEY_RE = re.compile(r"^\s*([A-Za-z][A-Za-z0-9_]*)\s*[=:]")


def _gia_tri(pairs, ma: str, key: str, whitelist) -> str | None:
    """Gia tri `key` cua case DAU TIEN thuoc nhom/case `ma` (vd R01 -> SDK361-R01-01) co dat key do."""
    for _tab, c in pairs:
        if f"-{ma.upper()}-" not in f"{c.n.upper()}-":
            continue
        if NHU_RE.search(c.test_data or ""):
            continue                         # case nguon cung tham chieu -> bo, tranh vong
        v = rc_extract.extract(c, whitelist).overrides.get(key)
        if v:
            return v
    return None


def thay_nhu(pairs: list, whitelist) -> list:
    """[(tab, Case)] -> cung danh sach, dong "key = ... (nhu X)" da thay bang gia tri that."""
    ra = []
    for tab, c in pairs:
        td = c.test_data or ""
        if not NHU_RE.search(td):
            ra.append((tab, c))
            continue
        dong = []
        for line in td.split("\n"):
            m, k = NHU_RE.search(line), KEY_RE.match(line)
            v = _gia_tri(pairs, m.group(1), k.group(1), whitelist) if (m and k) else None
            dong.append(f"{k.group(1)}={v}" if v else line)
        ra.append((tab, dataclasses.replace(c, test_data="\n".join(dong))))
    return ra
