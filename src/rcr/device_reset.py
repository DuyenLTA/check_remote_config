"""Dua app ve trang thai case doi, TRUOC khi patch config.

Ba muc do, chon theo Precondition - luat de o `data/reset_rules.yaml`:

    force-stop : mac dinh. Case chi doi mot co config -> khong dong vao du lieu
    reset mem  : lat `ARG_KEY_SHOW_ONBOARDING` = true -> app vao lai onboarding
                 ma GIU nguyen login/ngon ngu/data
    pm clear   : xoa sach du lieu app. Chi khi khong co co onboarding de lat

THU TU BAT BUOC: reset TRUOC, patch SAU. `pm clear` xoa luon file vua ghi, nen
patch truoc roi clear la mat trang.

Sau `pm clear` phai cho app tu sinh lai `frc_*.json` roi moi patch duoc: tool ghi
bang redirect (`cat tmp > dest`) de giu owner + nhan SELinux, ma redirect can
file dich TON TAI SAN. Cho theo trang thai that (file da xuat hien chua), khong
`sleep` cung.

Reset mem ghi vao `vsl_template4_prefs.xml` - dung file ma `rc_patch` tuyet doi
cam ghi. Khong mau thuan: day la THAO TAC RESET, khac han doi config. Cam o
rc_patch la de khong ai nham file state noi bo voi file mirror config.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from . import app_sandbox, device_app, mirror_xml, rc_baseline, rc_write
from .adb_parsers import AdbError
from .models import RcBaseline, RcError

log = logging.getLogger(__name__)

DATA = Path(__file__).parent / "data" / "reset_rules.yaml"
PREFS_DIR = "shared_prefs"
WAIT_FRC = 45.0      # may yeu qua splash ad rat lau moi fetch xong lan dau
POLL_INTERVAL = 1.5


def rules() -> dict:
    import yaml

    return yaml.safe_load(DATA.read_text(encoding="utf-8")) or {}


def needs_clean(precondition: str, data: dict | None = None) -> str:
    """Mau khop trong Precondition, "" neu case khong doi state sach."""
    text = (precondition or "").casefold()
    for pattern in (data or rules()).get("clean_state_patterns") or ():
        if pattern.casefold() in text:
            return pattern
    return ""


async def _flip_onboarding(client, baseline: RcBaseline, data: dict) -> str:
    """Lat co onboarding ve true. Tra ten file da ghi, "" neu app khong co co do."""
    flag = data.get("onboarding_flag") or {}
    key = flag.get("key")
    if not key:
        return ""
    # File khai trong luat truoc, roi den cac file state noi bo doc duoc tu may:
    # app khac co the dat ten khac, nhung co van cung ten.
    candidates = list(flag.get("files") or ()) + [
        n for n in baseline.non_mirror_files if n not in (flag.get("files") or ())
    ]
    for name in candidates:
        raw, problem = await app_sandbox.cat(
            client, baseline.serial, baseline.package,
            app_sandbox.quote(f"{PREFS_DIR}/{name}"), mode=baseline.write_mode,
        )
        if problem or not raw.strip():
            continue
        node = mirror_xml.parse_nodes(raw).get(key)
        if node is None:
            continue
        await rc_write.write_file(
            client, baseline.serial, baseline.package, baseline.write_mode,
            f"{PREFS_DIR}/{name}", mirror_xml.set_value(raw, node, "true"),
        )
        return name
    return ""


async def _clear_and_wait(client, baseline: RcBaseline) -> None:
    """`pm clear` roi mo app cho SDK sinh lai file config, sau do tat han app."""
    serial, package = baseline.serial, baseline.package
    app_sandbox.guard(serial, package)
    out, err, _ = await client.shell(serial, "pm", "clear", package)
    if "Success" not in out:
        raise AdbError(f"pm clear {package} that bai: {(err or out).strip()}")

    await device_app.launch(client, serial, package)
    waited = 0.0
    while waited < WAIT_FRC:
        names, problem = await app_sandbox.ls(
            client, serial, package, "files", mode=baseline.write_mode
        )
        if not problem and rc_baseline.find_activate_file(names):
            await device_app.force_stop(client, serial, package)
            return
        await asyncio.sleep(POLL_INTERVAL)
        waited += POLL_INTERVAL

    raise RcError(
        f"Sau `pm clear`, {package} chua sinh lai file remote config trong {WAIT_FRC:g}s.\n"
        "App can mang de fetch lan dau. Kiem tra may co mang khong, roi chay lai.\n"
        "Chua co file do thi khong patch duoc (tool ghi de len file san co)."
    )


async def prepare(client, baseline: RcBaseline, precondition: str = "") -> dict:
    """Dua app ve trang thai case doi. Tra ve da lam gi.

    `baseline_stale=True` nghia la file config da bi sinh lai -> NGUOI GOI phai
    doc lai baseline truoc khi patch, ban cu tro toi noi dung khong con nua.
    """
    data = rules()
    matched = needs_clean(precondition, data)
    if not matched:
        await device_app.force_stop(client, baseline.serial, baseline.package)
        return {"mode": "force-stop", "matched": "", "baseline_stale": False}

    await device_app.force_stop(client, baseline.serial, baseline.package)
    flipped = await _flip_onboarding(client, baseline, data)
    if flipped:
        # Re hon pm clear rat nhieu, va giu duoc login/ngon ngu -> khong phai
        # dung lai tai khoan test tu dau.
        return {"mode": "soft", "matched": matched, "file": flipped, "baseline_stale": False}

    log.warning("khong tim thay co onboarding -> phai pm clear %s", baseline.package)
    await _clear_and_wait(client, baseline)
    return {"mode": "clear", "matched": matched, "baseline_stale": True}
