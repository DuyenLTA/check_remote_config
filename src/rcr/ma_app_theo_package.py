"""Tra ma app (AIP944) tu package de dat len tieu de report.

User phan nan 19/11/2026: report "Luot cham AI Photo Video Creator 1.4.0" khong biet la app nao - ten app
trung nhau giua cac du an, chi ma app la duy nhat. Nguon: hang doi bot (`jobs` + `tin`) cua may chinh
(`bot-hang-doi.json`) va may phu (`bot-hang-doi-may-phu.json`) - bot luu package cua moi tin build.
Khong tra duoc -> "" (tieu de giu nhu cu, khong doan).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

OUT = Path(__file__).resolve().parents[2] / "out"
FILE_HANG_DOI = ("bot-hang-doi.json", "bot-hang-doi-may-phu.json")
MA_RE = re.compile(r"[A-Za-z]{3}\d{3}")


def ma_app(package: str, out: Path = OUT) -> str:
    """Ma app moi nhat (theo msg_id) cua package trong hang doi bot; '' khi khong co."""
    hop: list[tuple[int, str]] = []
    for ten in FILE_HANG_DOI:
        try:
            d = json.loads((out / ten).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        tin = d.get("tin") or {}
        cac = list(d.get("jobs") or []) + [dict(c, msg_id=k) for k, c in tin.items() if isinstance(c, dict)]
        for c in cac:
            ma = str(c.get("ma") or "")
            if c.get("package") == package and MA_RE.fullmatch(ma):
                try:
                    hop.append((int(c.get("msg_id") or 0), ma.upper()))
                except (TypeError, ValueError):
                    hop.append((0, ma.upper()))
    return max(hop)[1] if hop else ""


def gan_ma(nhan: str, package: str, out: Path = OUT) -> str:
    """"AI Photo Video Creator 1.4.0" -> "AIP944 · AI Photo Video Creator 1.4.0"; nhan da co ma thi giu nguyen."""
    if MA_RE.search(nhan or ""):
        return nhan
    ma = ma_app(package, out)
    if not ma:
        return nhan
    return f"{ma} · {nhan}" if nhan else ma
