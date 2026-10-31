"""Ban dich chuoi + mau `color/primary` doc tu resource cua APK tren may (aapt2), cache theo (package, versionCode).

Can cho hai loai dong Expected (AIP886 31/10/2026, R04-01):
  - "text 'Swipe to next'" khi case chon Francais: man hien ban dich 'Balayez pour continuer' -> tool phai biet
    do la ban dich CUA CHINH chuoi do trong app, khong phai chu la;
  - "dung mau primary cua app": mau lay tu resource `color/primary`, khong doan.
Doc hong (khong co aapt2, APK split thieu resource...) -> {} : dong do khong PASS nho tai nguyen nay.
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import tempfile
from pathlib import Path

from .dex_check import PUSH_TIMEOUT, apk_paths

log = logging.getLogger(__name__)

TEN_RE = re.compile(r"^\s*resource 0x[0-9a-f]+ (string|color)/(\S+)")
GIA_TRI_RE = re.compile(r'^\s*\(([^)]*)\)\s+(?:"(.*)"|(#[0-9a-fA-F]{6,8}))\s*$')


def _cache(cache_dir, package: str, version_code: str) -> Path:
    return Path(cache_dir) / f"res-{package}-{version_code or 'unknown'}.json"


def phan_tich(dump: str) -> dict:
    """Output `aapt2 dump resources` -> {"ban_dich": {chu goc: [ban dich...]}, "primary": "#RRGGBB" | ""}."""
    ban_dich: dict[str, list[str]] = {}
    primary, loai, ten, goc, khac = "", "", "", None, []

    def chot():
        if loai == "string" and goc and khac:
            ban_dich.setdefault(goc, [])
            ban_dich[goc] += [k for k in khac if k != goc and k not in ban_dich[goc]]

    for dong in dump.splitlines():
        m = TEN_RE.match(dong)
        if m:
            chot()
            loai, ten, goc, khac = m.group(1), m.group(2), None, []
            continue
        v = GIA_TRI_RE.match(dong)
        if not v or not loai:
            continue
        cau_hinh, chu, mau = v.group(1), v.group(2), v.group(3)
        if loai == "color" and ten == "primary" and not cau_hinh and mau and not primary:
            primary = "#" + mau[-6:].upper()
        elif loai == "string" and chu is not None:
            if cau_hinh == "":
                goc = chu
            else:
                khac.append(chu)
    chot()
    return {"ban_dich": ban_dich, "primary": primary}


async def doc(client, serial: str, package: str, cache_dir) -> dict:
    version_code = await client.version_code(serial, package)
    f = _cache(cache_dir, package, version_code)
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        pass
    try:
        ra = await _doc_may(client, serial, package)
    except Exception as exc:  # noqa: BLE001 - thieu tai nguyen chi lam dong lien quan khong PASS
        log.warning("khong doc duoc resource APK %s: %s", package, exc)
        return {}
    try:
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(ra, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass
    return ra


async def _doc_may(client, serial: str, package: str) -> dict:
    from .rc_firebase_app import _aapt2

    duong = await apk_paths(client, serial, package)
    if not duong:
        return {}
    fd, ten = tempfile.mkstemp(prefix="rcr_res_", suffix=".apk")
    os.close(fd)
    local = Path(ten)
    try:
        _, err, code = await client._run("-s", serial, "pull", duong[0], str(local), timeout=PUSH_TIMEOUT * 4)
        if code != 0:
            raise OSError(f"không kéo được {duong[0]}: {err.strip()}")
        dump = subprocess.run([_aapt2(), "dump", "resources", str(local)], capture_output=True,
                              encoding="utf-8", errors="replace").stdout
    finally:
        local.unlink(missing_ok=True)
    return phan_tich(dump)
