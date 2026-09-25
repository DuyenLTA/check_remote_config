"""Luu nguyen van config goc ra dia, de con duong ve sau khi giu patch.

VI SAO CAN: `rc_patch.restore` chi tra ve duoc baseline doc TRONG CUNG LUOT.
Giu patch lai (`--keep`) roi chay luot khac thi baseline doc duoc DA LA BAN DA
PATCH - "restore" luc do ghi lai chinh gia tri ban, may nam ban vinh vien ma
khong ai biet.

Chi luu 3 thu can de ghi nguoc: noi dung activate.json, settings.xml va cac file
mirror. Khong luu `configs` da parse: restore phai ghi lai DUNG TUNG BYTE.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from .models import RcBaseline, RcError

FIELDS = (
    "package", "serial", "app_id", "activate_name", "settings_name",
    "activate_raw", "settings_raw", "write_mode",
)


def path_for(directory: str | Path, package: str, serial: str) -> Path:
    return Path(directory) / f"restore-{package}-{serial}.json"


def save(baseline: RcBaseline, directory: str | Path) -> Path:
    """Ghi snapshot. Tra duong dan file."""
    out = path_for(directory, baseline.package, baseline.serial)
    out.parent.mkdir(parents=True, exist_ok=True)
    data = {f: getattr(baseline, f) for f in FIELDS}
    data["fetch_time_ms"] = baseline.fetch_time_ms
    data["mirror_raw"] = dict(baseline.mirror_raw)
    data["saved_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    out.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return out


def load(path: str | Path) -> RcBaseline:
    """Doc snapshot thanh RcBaseline du de `rc_patch.restore` chay.

    `configs`/`mirrors` chi con ten file: restore khong doc gia tri, no ghi
    nguyen van. Ten file van phai giu - `_assert_writable` chan theo danh sach do.
    """
    p = Path(path)
    if not p.exists():
        raise RcError(
            f"Khong co snapshot {p}.\n"
            "Snapshot chi sinh ra o luot chay co --keep. Luot truoc khong giu "
            "patch thi config da duoc tra ve ngay luc do, khong can restore."
        )
    data = json.loads(p.read_text(encoding="utf-8"))
    mirror_raw = data.get("mirror_raw") or {}
    return RcBaseline(
        **{f: data[f] for f in FIELDS},
        fetch_time_ms=data.get("fetch_time_ms", 0),
        mirror_raw=mirror_raw,
        mirrors={name: {} for name in mirror_raw},
    )
