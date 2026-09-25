"""Do ban SDK First Open cua app tu logcat.

Bo TC chung chia tab theo ban SDK, nen phai biet app dang chay ban nao moi lay
dung base + delta. Ban nay KHONG doc duoc tu versionName cua app: app 2.8.0 co
the dang nhung SDK 3.5.4 - hai con so khong lien quan.

Nguon su that la dong log SDK tu in ra luc khoi dong:
    VslTemplate4FirstOpenSDK: Using version 3.5.3

PHAI LOC THEO PID CUA APP DICH. Tag nay KHONG rieng cua app nao - moi app nhung
SDK VisionLab deu in cung tag, ma logcat thi chung ca may. Doc ca buffer roi lay
bua la nhat ban SDK CUA APP KHAC (da vap: doc ra 3.5.4-alpha02 trong khi app dich
dung 3.5.3, chi vi app khac vua chay truoc do).

App chua chay -> khong co PID -> khong doc buffer nua ma mo lai app: doc buffer
"chung" con nguy hiem hon la khong doc.
"""

from __future__ import annotations

import asyncio
import logging

from . import device_app, tc_catalog
from .adb_parsers import AdbError
from .app_sandbox import guard

log = logging.getLogger(__name__)

TAG = "VslTemplate4FirstOpenSDK"
LOGCAT_TIMEOUT = 20.0
WAIT_AFTER_LAUNCH = 15.0
POLL_INTERVAL = 1.5


async def pid_of(client, serial: str, package: str) -> str:
    """PID cua app, "" neu app khong chay."""
    guard(serial, package)
    out, _, _ = await client.shell(serial, "pidof", package)
    return out.split()[0] if out.split() else ""


async def read_log(client, serial: str, pid: str) -> str:
    """Logcat cua RIENG tien trinh app, loc san theo tag."""
    guard(serial)
    out, _, _ = await client._run(
        "-s", serial, "logcat", "-d", "--pid", pid, "-s", f"{TAG}:I",
        timeout=LOGCAT_TIMEOUT,
    )
    return out


def last_version(log_text: str) -> str:
    """Ban SDK o dong MOI NHAT. App vua duoc nang cap thi dong cu van con trong
    buffer - lay dong dau la lay ban da cu."""
    hits = tc_catalog.SDK_LOG_RE.findall(log_text or "")
    return hits[-1] if hits else ""


async def detect(client, serial: str, package: str, relaunch: bool = True) -> dict:
    """-> {version, source}. Khong doc duoc -> raise AdbError kem cach lam tay.

    `relaunch=False` de chi soi buffer, khong dong cham app dang chay.
    """
    guard(serial, package)
    pid = await pid_of(client, serial, package)
    if pid:
        version = last_version(await read_log(client, serial, pid))
        if version:
            return {"version": version, "source": f"logcat cua pid {pid}"}
    if not relaunch:
        raise AdbError(
            f"Khong thay dong `{TAG}: Using version` trong logcat cua {package}."
        )

    # Buffer khong co -> mo lai app cho SDK in ra. Xoa buffer truoc de khong
    # nhat phai ban cua LUOT TRUOC (app vua duoc nang cap thi ban do da cu).
    await client._run("-s", serial, "logcat", "-c", timeout=LOGCAT_TIMEOUT)
    await device_app.restart(client, serial, package)

    waited = 0.0
    while waited < WAIT_AFTER_LAUNCH:
        pid = await pid_of(client, serial, package)
        if pid:
            version = last_version(await read_log(client, serial, pid))
            if version:
                return {"version": version, "source": f"mo lai app (pid {pid})"}
        await asyncio.sleep(POLL_INTERVAL)
        waited += POLL_INTERVAL

    raise AdbError(
        f"Khong doc duoc ban SDK cua {package} sau khi mo lai app.\n"
        f"  App co the khong dung SDK First Open cua VisionLab (khong co tag {TAG}).\n"
        "  Kiem tra bang tay:\n"
        f"    adb -s {serial} logcat -d --pid $(adb -s {serial} shell pidof {package}) -s {TAG}:I\n"
        "  Biet ban roi thi truyen thang: --sdk <X.Y.Z>"
    )
