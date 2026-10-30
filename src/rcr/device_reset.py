"""Dua app ve trang thai case doi, TRUOC khi patch config.

Cot "User State" cua file TC quyet TRUOC (user chot 2026-10-02, khop sheet
"Automation Convention" cua bo TC 3.5.0):

    new_user   : `pm clear` that roi mo app
    old_user   : `pm clear`, lai het FO toi Home, tat app - lan mo SAU moi la
                 lan do. Vi tri `_o_` (106...) chi chay voi old user: chay nham
                 nhanh user moi thi khong bao gio co request, PASS gia.

Reset mem KHONG dung cho hai truong hop tren: no ep app ve luong user moi ma
van giu ngon ngu da chon - khong phai "clear data", cang khong phai old user.

File TC cu khong co cot do -> ba muc do, chon theo Precondition - luat de o
`data/reset_rules.yaml`:

    force-stop : mac dinh. Case chi doi mot co config -> khong dong vao du lieu
    reset mem  : lat `ARG_KEY_SHOW_ONBOARDING` = true -> app vao lai onboarding
                 ma GIU nguyen login/ngon ngu/data
    pm clear   : xoa sach du lieu app. Chi khi khong co co onboarding de lat

THU TU BAT BUOC: reset TRUOC, patch SAU. `pm clear` xoa luon file vua ghi, nen
patch truoc roi clear la mat trang.

Sau `pm clear` phai cho app tu sinh lai `frc_*.json` roi moi patch duoc: tool ghi
bang redirect (`cat tmp > dest`) de giu owner + nhan SELinux, ma redirect can
file dich TON TAI SAN. Cho theo trang thai that, khong `sleep` cung - va "co
file" CHUA du: app tao file rong truoc roi moi ghi config vao. Tat app ngay luc
file vua xuat hien la de lai file 0 byte, baseline doc ra khong phai JSON (do
tren Pixel 4, 2026-10-02). Phai cho toi khi file la JSON co `configs_key`.

Reset mem ghi vao `vsl_template4_prefs.xml` - dung file ma `rc_patch` tuyet doi
cam ghi. Khong mau thuan: day la THAO TAC RESET, khac han doi config. Cam o
rc_patch la de khong ai nham file state noi bo voi file mirror config.
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path

from . import app_sandbox, device_app, fo_flow, mirror_xml, rc_baseline, rc_write
from .adb_parsers import AdbError
from .models import RcBaseline, RcError

log = logging.getLogger(__name__)

DATA = Path(__file__).parent / "data" / "reset_rules.yaml"
PREFS_DIR = "shared_prefs"
WAIT_FRC = 45.0      # may yeu qua splash ad rat lau moi fetch xong lan dau
POLL_INTERVAL = 1.5
# Sau khi dong paywall, Home co the hien cham hon vong lai cua fo_flow.
CHO_HOME = 10.0


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


async def _activate_filled(client, baseline: RcBaseline, name: str) -> bool:
    """File activate da co config that chua - khong chi la da ton tai."""
    raw, problem = await app_sandbox.cat(
        client, baseline.serial, baseline.package,
        rc_baseline._q(f"files/{name}"), mode=baseline.write_mode,
    )
    if problem or not raw.strip():
        return False
    try:
        return isinstance(json.loads(raw).get("configs_key"), dict)
    except (json.JSONDecodeError, AttributeError):
        return False  # app dang ghi do -> cho vong sau


NOTIFICATION_PERMISSION = "android.permission.POST_NOTIFICATIONS"


async def _grant_notifications(client, serial: str, package: str) -> None:
    """Cap san quyen thong bao de app mo len KHONG bi dialog he thong che.

    `pm clear` xoa ca quyen da cap. Tu Android 13, app khai POST_NOTIFICATIONS
    mo lan dau la hien dialog cua permissioncontroller de tren app: app khong
    bao gio len foreground, case nao cung het gio cho roi chay lai (do 10/10/2026,
    Sorapix 1.6.0 tren Pixel 6: 20/23 case ket, 2 tieng cho suong). Cap bang
    `pm grant` thay vi bam Allow: khong tap gi tren man, luong FO dang test
    khong doi.

    Loi thi bo qua: Android < 13 hoac app khong khai quyen nay thi `pm grant`
    tu choi, ma cung khong co dialog nao de chan.
    """
    out, err, code = await client.shell(serial, "pm", "grant", package, NOTIFICATION_PERMISSION)
    if code or (err or "").strip():
        log.debug("pm grant %s bo qua: %s", NOTIFICATION_PERMISSION, (err or out).strip())


async def _clear_and_wait(client, baseline: RcBaseline) -> None:
    """`pm clear` roi mo app cho SDK sinh lai file config, sau do tat han app."""
    serial, package = baseline.serial, baseline.package
    app_sandbox.guard(serial, package)
    out, err, _ = await client.shell(serial, "pm", "clear", package)
    if "Success" not in out:
        raise AdbError(f"pm clear {package} that bai: {(err or out).strip()}")

    await _grant_notifications(client, serial, package)
    await device_app.launch(client, serial, package)
    waited = 0.0
    while waited < WAIT_FRC:
        names, problem = await app_sandbox.ls(
            client, serial, package, "files", mode=baseline.write_mode
        )
        found = None if problem else rc_baseline.find_activate_file(names)
        if found and await _activate_filled(client, baseline, found[0]):
            await device_app.force_stop(client, serial, package)
            return
        await asyncio.sleep(POLL_INTERVAL)
        waited += POLL_INTERVAL

    raise RcError(
        f"Sau `pm clear`, {package} chua sinh lai file remote config trong {WAIT_FRC:g}s.\n"
        "App can mang de fetch lan dau. Kiem tra may co mang khong, roi chay lai.\n"
        "Chua co file do thi khong patch duoc (tool ghi de len file san co)."
    )


async def _make_old_user(client, baseline: RcBaseline, log_fn) -> None:
    """Mot session di het FO toi Home roi tat app -> lan mo sau la old user.

    Khong toi duoc Home thi RAISE: chay tiep la do luong user moi ma report
    van ghi old user.
    """
    serial, package = baseline.serial, baseline.package
    await device_app.launch(client, serial, package)
    await device_app.wait_foreground(client, serial, package)
    log_fn("  tao old user: lai het FO toi Home...")
    walk = await fo_flow.walk_to(client, serial, package, "", log_fn=log_fn)
    home = fo_flow.rules().get("home_match", "MainActivity")
    waited = 0.0
    while not walk["reached"] and waited < CHO_HOME:
        _, activity = await device_app.focus(client, serial)
        if home in activity:
            walk = {"reached": True, "activity": activity}
            break
        await asyncio.sleep(POLL_INTERVAL)
        waited += POLL_INTERVAL
    if not walk["reached"]:
        raise RcError(
            f"Khong tao duoc old user: lai FO khong toi {home} "
            f"(dung o {walk.get('activity') or '?'}). Case old_user khong chay tiep."
        )
    await device_app.force_stop(client, serial, package)
    log_fn(f"  da toi {walk['activity'].split('.')[-1]} -> tat app, lan mo sau la old user")


async def prepare_firebase(client, baseline: RcBaseline, user_state: str = "", log_fn=lambda _m: None) -> dict:
    """Ban release (RC doi tren server qua `testvsl`): app CHI lay RC moi o lan mo dau sau `pm clear` - tat / mo
    lai giu ban RC cu (do 30/10/2026, AIP886 2.7.0). Nen moi luot: RC da publish TRUOC -> `pm clear` -> old_user
    thi lai FO toi Home roi tat app (lan mo sau la old user, van giu RC cua case) -> nguoi goi mo app."""
    serial, package = baseline.serial, baseline.package
    await device_app.force_stop(client, serial, package)
    app_sandbox.guard(serial, package)
    out, err, _ = await client.shell(serial, "pm", "clear", package)
    if "Success" not in out:
        raise AdbError(f"pm clear {package} that bai: {(err or out).strip()}")
    await _grant_notifications(client, serial, package)
    if user_state == "old_user":
        await _make_old_user(client, baseline, log_fn)
        return {"mode": "old_user", "matched": "User State: old_user (RC qua Firebase)", "baseline_stale": False}
    return {"mode": "clear", "matched": "RC qua Firebase: app chỉ nhận RC mới sau pm clear", "baseline_stale": False}


async def prepare(client, baseline: RcBaseline, precondition: str = "",
                  user_state: str = "", log_fn=lambda _m: None) -> dict:
    """Dua app ve trang thai case doi. Tra ve da lam gi.

    `baseline_stale=True` nghia la file config da bi sinh lai -> NGUOI GOI phai
    doc lai baseline truoc khi patch, ban cu tro toi noi dung khong con nua.
    """
    if user_state == "new_user":
        await device_app.force_stop(client, baseline.serial, baseline.package)
        await _clear_and_wait(client, baseline)
        return {"mode": "clear", "matched": "User State: new_user", "baseline_stale": True}
    if user_state == "old_user":
        await device_app.force_stop(client, baseline.serial, baseline.package)
        await _clear_and_wait(client, baseline)
        await _make_old_user(client, baseline, log_fn)
        return {"mode": "old_user", "matched": "User State: old_user", "baseline_stale": True}

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
