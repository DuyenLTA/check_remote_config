"""Bo sung key server CHUA khai nhung app CO doc vao baseline (truong `dex_keys`).

VI SAO: whitelist key lay tu config Firebase tren may. Key server chua tung
tra ve thi khong co trong do, du app doc no voi gia tri mac dinh trong code.
Bo TC SDK 3.6.1 dat `onboard_config_content_new` (noi dung OB/Question theo ngon
ngu) - AI Home Design 1.8.0 co chuoi key trong DEX nhung server chua khai, nen
tool coi la "param analytics", bo di, roi chay ca bo R01..O02 tren noi dung mac
dinh cua app: dong "FR - OB1 title" FAIL / NEEDS_HUMAN oan (30/10/2026).

Chi nhan key co chuoi trong DEX: key go sai ten hay param analytics (`source`)
van bi loai nhu truoc. Ten phai co `_` - chuoi ngan kieu `n`, `source` gan nhu
APK nao cung co, khong noi duoc app doc no qua remote config.
"""

from __future__ import annotations

import re
from dataclasses import replace

from . import dex_check
from .models import RcBaseline

KEY_RE = re.compile(r"^[a-z][a-z0-9]*(_[a-z0-9]+)+$")


def ung_vien(keys, baseline: RcBaseline) -> list[str]:
    """Key chua co trong config cua app, trong giong ten key RC."""
    return sorted({k for k in keys if k not in baseline.configs and KEY_RE.match(k)})


async def bo_sung(client, baseline: RcBaseline, keys, cache_dir, log_fn) -> RcBaseline:
    """Tra baseline co them `dex_keys` = cac key trong `keys` ma app co doc."""
    can_soi = ung_vien(keys, baseline)
    if not can_soi:
        return baseline
    co = await dex_check.check(client, baseline.serial, baseline.package, can_soi, cache_dir)
    them = frozenset(k for k, ok in co.items() if ok)
    if them:
        log_fn("  key server chua khai nhung app co doc (DEX) -> van dat: " + ", ".join(sorted(them)))
    return replace(baseline, dex_keys=baseline.dex_keys | them)
