"""Firebase CLI con dang nhap khong (doi Remote Config qua Firebase can CLI con han).

Dem 16-17/11/2026: CLI het han luc 01:40 giua luot AIP892 -> 7 case BLOCKED (khong dat duoc config) ma bot van nhan
job. `firebase login:list` noi doi (van ghi tai khoan khi token het han) -> thu `projects:list` that.
Ket qua nho CACHE_GIAY de vong chia job (vai giay/lan) khong goi CLI lien tuc.
"""

from __future__ import annotations

import shutil
import subprocess
import time

CACHE_GIAY = 600
_nho: tuple[float, bool] = (0.0, True)


def con_han(bay_gio: float | None = None) -> bool:
    global _nho
    now = time.monotonic() if bay_gio is None else bay_gio
    if now - _nho[0] < CACHE_GIAY:
        return _nho[1]
    cli = shutil.which("firebase")
    if not cli:
        ok = True              # may khong dung Firebase CLI (doi RC qua cach khac) -> khong chan
    else:
        try:
            ok = subprocess.run([cli, "projects:list", "--json"], capture_output=True, text=True,
                                timeout=90).returncode == 0
        except (subprocess.TimeoutExpired, OSError):
            ok = False
    _nho = (now, ok)
    return ok


def xoa_nho() -> None:
    global _nho
    _nho = (0.0, True)
