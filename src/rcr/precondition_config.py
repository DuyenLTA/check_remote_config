"""Them config Test Data hay quen ghi tu cau Precondition (data/precondition_config.yaml).

AIP892 checkin 16/11/2026: Precondition "App bat man Add widget" ma Test Data khong dat `widget_screen_placement` ->
popup Add Widget khong hien, case "Checkin hien sau Add widget" ra BLOCKED / FAIL gia.
"""

from __future__ import annotations

import re
from pathlib import Path

DATA = Path(__file__).parent / "data" / "precondition_config.yaml"


def them(precondition: str, whitelist, found: dict) -> dict:
    """Cap key=value suy tu Precondition; key da co trong `found` hoac khong co trong whitelist thi bo."""
    import yaml
    luat = yaml.safe_load(DATA.read_text(encoding="utf-8")) or []
    ra = {}
    for l in luat:
        if re.search(l["mau"], precondition or "", re.I):
            ra |= {k: str(v) for k, v in (l.get("dat") or {}).items() if k in whitelist and k not in found}
    return ra
