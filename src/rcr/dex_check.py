"""App co THAT SU doc key nay khong - soi chuoi trong file DEX.

VI SAO CAN: key co trong remote config KHAC voi app doc key do. Template
Firebase dung chung nhieu app, nen app van thay key ma code khong tham chieu.
Da do: `songmaker` khong co chuoi `splash_banner_change` trong DEX, va runtime
xac nhan banner show bat ke true/false -> cham ngay tho se ra PASS GIA.

Key khong co trong DEX -> `KEY_NOT_USED`, khong ton mot luot mo app, va nhat la
khong bao PASS cho case ma app chang he doc key.

PHAI QUET MOI APK, KHONG CHI `base.apk`: app cai tu AAB qua Play bi chia thanh
base + split, key co the nam trong `split_*.apk` cua feature module -> grep
mot minh base.apk se bao KEY_NOT_USED OAN.

Ket qua cache theo `(package, versionCode)`: keo APK vai chuc MB, khong keo lai
moi case. Ban app doi -> versionCode doi -> cache tu mat hieu luc.
"""

from __future__ import annotations

import json
import logging
import re
import tempfile
import zipfile
from pathlib import Path

from .adb_client import PUSH_TIMEOUT
from .adb_parsers import AdbError
from .app_sandbox import guard

log = logging.getLogger(__name__)

PATH_RE = re.compile(r"^package:(\S+\.apk)$", re.M)
DEX_RE = re.compile(r"classes\d*\.dex$")


async def apk_paths(client, serial: str, package: str) -> list[str]:
    """Moi duong dan APK cua app (base + split)."""
    guard(serial, package)
    out, err, _ = await client.shell(serial, "pm", "path", package)
    paths = PATH_RE.findall(out)
    if not paths:
        raise AdbError(f"Khong thay APK cua {package}: {(err or out).strip() or 'pm path rong'}")
    return paths


def scan_apk(local: Path, keys: list[str]) -> set[str]:
    """Key nao co chuoi trong classes*.dex cua file APK nay."""
    found: set[str] = set()
    needles = {k: k.encode() for k in keys}
    with zipfile.ZipFile(local) as zf:
        for name in (n for n in zf.namelist() if DEX_RE.search(n)):
            blob = zf.read(name)
            for key, needle in needles.items():
                if key not in found and needle in blob:
                    found.add(key)
            if len(found) == len(keys):
                break
    return found


def _cache_file(cache_dir, package: str, version_code: str) -> Path:
    return Path(cache_dir) / f"dex-{package}-{version_code or 'unknown'}.json"


def load_cache(cache_dir, package: str, version_code: str) -> dict[str, bool]:
    path = _cache_file(cache_dir, package, version_code)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        log.warning("cache dex hong, quet lai: %s", path)
        return {}


def save_cache(cache_dir, package: str, version_code: str, data: dict[str, bool]) -> None:
    path = _cache_file(cache_dir, package, version_code)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


async def check(client, serial: str, package: str, keys, cache_dir) -> dict[str, bool]:
    """-> {key: app co doc key do khong}. Chi keo APK khi con key chua biet."""
    keys = sorted(set(keys))
    if not keys:
        return {}
    version_code = await client.version_code(serial, package)
    cache = load_cache(cache_dir, package, version_code)
    missing = [k for k in keys if k not in cache]
    if missing:
        cache |= await _scan_device(client, serial, package, missing)
        save_cache(cache_dir, package, version_code, cache)
    return {k: cache.get(k, False) for k in keys}


async def _scan_device(client, serial: str, package: str, keys: list[str]) -> dict[str, bool]:
    found: set[str] = set()
    for remote in await apk_paths(client, serial, package):
        local = Path(tempfile.mkstemp(prefix="rcr_apk_", suffix=".apk")[1])
        try:
            out, err, code = await client._run(
                "-s", serial, "pull", remote, str(local), timeout=PUSH_TIMEOUT * 4
            )
            if code != 0:
                raise AdbError(f"Khong keo duoc {remote}: {(err or out).strip()}")
            found |= scan_apk(local, [k for k in keys if k not in found])
        except zipfile.BadZipFile as exc:
            raise AdbError(f"{remote} khong doc duoc nhu file zip: {exc}") from exc
        finally:
            local.unlink(missing_ok=True)
        if len(found) == len(keys):
            break  # du roi, khong keo tiep split con lai
    return {k: k in found for k in keys}
