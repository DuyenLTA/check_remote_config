"""Doc baseline remote config that cua 1 app tren may.

Firebase RC SDK ghi cung mot cho, cung mot ten, o MOI app (da do thuc te tren
2 may / 2 ban Android / 5 app):
    files/frc_<appId>_firebase_activate.json   <- gia tri, moi value la string
    shared_prefs/frc_<appId>_firebase_settings.xml  <- moc throttle fetch

NHAN MIRROR BANG GIAO TEN KEY, KHONG THEO TEN FILE. Khong phai file `vsl_*` nao
cung la mirror cua remote config: `vsl_template4_prefs.xml` (0/5 key giao) va
`vsl_widget_local_prefs.xml` (0/2) la STATE NOI BO app - ghi vao la lam hong
trang thai app. Ten file khong dang tin: `vsl_rating_remote_prefs.xml` co chu
`remote` ma chi 3/5 key la RC.
"""

from __future__ import annotations

import json
import logging

from . import app_sandbox
from .adb_parsers import AdbError, find_activate_file
from .mirror_xml import parse_nodes, read_long
from .models import RcBaseline, RcError

log = logging.getLogger(__name__)

FILES_DIR = "files"
PREFS_DIR = "shared_prefs"
MIRROR_PREFIX = "vsl_"


def _q(path: str) -> str:
    """Boc nhay duong dan: ten frc_* chua dau ':' va di qua `sh` tren device."""
    return "'" + path.replace("'", "'\\''") + "'"


async def read(client, serial: str, package: str) -> RcBaseline:
    """Doc baseline. Raise RcError kem thong bao that cua adb."""
    try:
        mode = await app_sandbox.detect_mode(client, serial, package)
    except AdbError as exc:
        raise RcError(str(exc)) from exc

    names, problem = await app_sandbox.ls(client, serial, package, FILES_DIR, mode=mode)
    if problem:
        raise RcError(f"Khong doc duoc {FILES_DIR}/ cua {package}: {problem}")
    found = find_activate_file(names)
    if not found:
        raise RcError(
            f"{package} khong co file remote config cua Firebase trong {FILES_DIR}/.\n"
            "App chua fetch lan nao, hoac khong dung Firebase Remote Config.\n"
            "Thu mo app mot lan roi doc lai."
        )
    activate_name, app_id = found

    activate_raw, problem = await app_sandbox.cat(
        client, serial, package, _q(f"{FILES_DIR}/{activate_name}"), mode=mode
    )
    if problem:
        raise RcError(f"Khong doc duoc {activate_name}: {problem}")
    configs, fetch_ms, tpl = _parse_activate(activate_raw, activate_name)

    settings_name = f"frc_{app_id}_firebase_settings.xml"
    settings_raw, problem = await app_sandbox.cat(
        client, serial, package, _q(f"{PREFS_DIR}/{settings_name}"), mode=mode
    )
    if problem or not settings_raw.strip():
        raise RcError(
            f"Khong doc duoc {settings_name}: {problem or 'file rong'}.\n"
            "Thieu file nay thi khong chan duoc app fetch de mat patch."
        )
    if read_long(settings_raw, "last_fetch_time_in_millis") is None:
        raise RcError(
            f"{settings_name} khong co <long name=\"last_fetch_time_in_millis\">.\n"
            "Khong set duoc moc throttle -> app se fetch de mat patch."
        )

    mirrors, mirror_raw, non_mirror = await _read_mirrors(
        client, serial, package, mode, set(configs)
    )

    return RcBaseline(
        package=package,
        serial=serial,
        app_id=app_id,
        activate_name=activate_name,
        settings_name=settings_name,
        activate_raw=activate_raw,
        settings_raw=settings_raw,
        configs=configs,
        fetch_time_ms=fetch_ms,
        template_version=tpl,
        mirrors=mirrors,
        mirror_raw=mirror_raw,
        non_mirror_files=tuple(sorted(non_mirror)),
        write_mode=mode,
    )


def _parse_activate(raw: str, name: str) -> tuple[dict[str, str], int, str]:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RcError(f"{name} khong phai JSON hop le: {exc}") from exc
    configs = data.get("configs_key")
    if not isinstance(configs, dict):
        raise RcError(f"{name} khong co object 'configs_key' - khong dung schema Firebase RC.")
    # RC luu MOI value duoi dang string; ep lai cho chac de tang sau khong phai doan.
    out = {str(k): v if isinstance(v, str) else json.dumps(v) for k, v in configs.items()}
    fetch_ms = data.get("fetch_time_key") or 0
    tpl = str(data.get("template_version_number_key") or "")
    return out, int(fetch_ms), tpl


async def _read_mirrors(client, serial, package, mode, rc_keys: set[str]):
    """Doc cac file vsl_* va phan loai mirror / state noi bo."""
    names, problem = await app_sandbox.ls(client, serial, package, PREFS_DIR, mode=mode)
    if problem:
        log.warning("khong liet ke duoc %s/: %s", PREFS_DIR, problem)
        return {}, {}, set()

    mirrors: dict[str, dict] = {}
    mirror_raw: dict[str, str] = {}
    non_mirror: set[str] = set()
    for name in names:
        if not name.startswith(MIRROR_PREFIX) or not name.endswith(".xml"):
            continue
        raw, problem = await app_sandbox.cat(
            client, serial, package, _q(f"{PREFS_DIR}/{name}"), mode=mode
        )
        if problem:
            log.warning("bo qua mirror %s: %s", name, problem)
            continue
        nodes = parse_nodes(raw)
        shared = {k: n for k, n in nodes.items() if k in rc_keys}
        if shared:
            mirrors[name] = shared
            mirror_raw[name] = raw
        else:
            # 0 key giao -> state noi bo app. Giu ten de hien len UI, khong ghi vao.
            non_mirror.add(name)
    return mirrors, mirror_raw, non_mirror
