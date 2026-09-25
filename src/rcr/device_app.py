"""Bat/tat app tren may. Chi vong doi app, khong dung toi sandbox du lieu.

Tach khoi adb_client vi hai viec khac nhau: adb_client la tang GOI LENH
(transport, guard, timeout), day la HANH VI tren app. Gop lam mot thi module
vuot 200 LOC va lan lon hai tang.

`pm clear` KHONG nam o day - no xoa sach du lieu app (mat login, mat ca file
frc_ vua ghi). Thao tac do chi duoc goi tu device_reset, sau khi canh bao.

Mo app bang `am start` vao dung component do PMS tra ve, KHONG dung `monkey`:
monkey ban su kien that vao man hinh, gap quang cao hay paywall la bam bua.
"""

from __future__ import annotations

import asyncio
import logging
import re
import time

from .adb_parsers import AdbError, output_error
from .app_sandbox import guard

log = logging.getLogger(__name__)

# `dumpsys window` doi ten field theo doi Android -> bat ca 3 ten thuong gap.
_FOCUS_RE = re.compile(
    r"(?:mCurrentFocus|mFocusedApp|mResumedActivity)=[^\n]*?"
    r"([A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z0-9_]+)+)/([A-Za-z0-9_.$]+)"
)

LAUNCH_TIMEOUT = 25.0
POLL_INTERVAL = 0.7


async def force_stop(client, serial: str, package: str) -> None:
    """Tat HAN app. Bat buoc truoc khi patch: app dang chay giu config cu trong RAM."""
    guard(serial, package)
    out, err, _ = await client.shell(serial, "am", "force-stop", package)
    problem = output_error(out, err)
    if problem:
        raise AdbError(f"Khong tat duoc {package}: {problem}")


async def resolve_launcher(client, serial: str, package: str) -> str:
    """Component man hinh mo dau, dang `pkg/.MainActivity`.

    PMS khong resolve duoc thi thuong la MAY DANG KHOA - nhin y het app hong.
    Noi thang de nguoi dung mo khoa, dung di tim bug trong app.
    """
    guard(serial, package)
    out, _, _ = await client.shell(
        serial, "cmd", "package", "resolve-activity", "--brief", package
    )
    hits = [
        line.strip()
        for line in out.splitlines()
        if line.strip().startswith(f"{package}/")
    ]
    if not hits:
        raise AdbError(
            f"Khong tim duoc man hinh mo dau cua {package}.\n"
            "  - May dang khoa? Mo khoa man hinh roi chay lai "
            "(may khoa thi PMS khong resolve duoc activity nao).\n"
            "  - App da cai tren may chua? `adb shell pm list packages | grep <pkg>`"
        )
    return hits[-1]


async def launch(client, serial: str, package: str) -> str:
    """Mo app tu launcher. Tra component da mo."""
    component = await resolve_launcher(client, serial, package)
    out, err, _ = await client.shell(
        serial,
        "am", "start",
        "-a", "android.intent.action.MAIN",
        "-c", "android.intent.category.LAUNCHER",
        "-n", component,
    )
    joined = f"{out} {err}"
    if "Error" in joined or "Exception" in joined:
        raise AdbError(f"Mo {component} that bai: {joined.strip()}")
    return component


async def focus(client, serial: str) -> tuple[str, str]:
    """(package, activity) dang o foreground. ("", "") neu khong doc duoc."""
    guard(serial)
    out, _, _ = await client.shell(serial, "dumpsys", "window")
    match = _FOCUS_RE.search(out)
    return (match.group(1), match.group(2)) if match else ("", "")


async def foreground(client, serial: str) -> str:
    """Package dang o foreground, "" neu khong doc duoc."""
    return (await focus(client, serial))[0]


async def tap(client, serial: str, x: int, y: int) -> None:
    """Bam vao toa do pixel. CHI goi khi resolver chac chan node nao la dung -
    tap sai cho tren may that la bam quang cao hoac mua hang that."""
    guard(serial)
    out, err, _ = await client.shell(serial, "input", "tap", str(int(x)), str(int(y)))
    problem = output_error(out, err)
    if problem:
        raise AdbError(f"Tap ({x},{y}) that bai: {problem}")


async def wait_foreground(
    client, serial: str, package: str, timeout: float = LAUNCH_TIMEOUT
) -> float:
    """Cho app len foreground. Tra so giay da cho; het gio -> raise AdbError.

    Cho theo TRANG THAI THAT chu khong `sleep` cung: may yeu qua splash ad mat
    hang chuc giay, may khoe xong trong 2s - so cung thi hoac cho thua hoac
    doc config khi app chua kip khoi dong.
    """
    started = time.monotonic()
    last = ""
    while time.monotonic() - started < timeout:
        last = await foreground(client, serial)
        if last == package:
            return round(time.monotonic() - started, 1)
        await asyncio.sleep(POLL_INTERVAL)
    raise AdbError(
        f"{package} khong len foreground sau {timeout:g}s "
        f"(dang o foreground: {last or 'khong doc duoc'}). "
        "Man hinh khoa, hoac app dang ket o splash/quang cao."
    )


async def restart(client, serial: str, package: str) -> dict:
    """force-stop -> mo lai -> cho len foreground. Dung sau khi patch config.

    Phai tat HAN roi mo lai: app con trong RAM thi no tra gia tri da doc tu
    truoc, verify se thay dung ma app van chay theo config cu.
    """
    await force_stop(client, serial, package)
    component = await launch(client, serial, package)
    waited = await wait_foreground(client, serial, package)
    return {"component": component, "waited_s": waited}
