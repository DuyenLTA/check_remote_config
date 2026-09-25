"""App co crash trong luot chay khong.

188/1421 assertion trong bo TC chung la "Khong crash" - chấm duoc bang du lieu
co san, khong can nhin man hinh.

Doc buffer `crash` rieng cua Android chu khong grep logcat chinh: buffer do chi
chua crash that (java crash + native tombstone), khong lan voi dong log co chu
"exception" cua app.

KHONG loc theo PID: app crash xong thi tien trinh chet, PID bien mat - loc theo
PID la bo sot dung cai minh dang tim. Loc theo ten package trong noi dung dong.
"""

from __future__ import annotations

from .adb_parsers import PACKAGE_RE, AdbError
from .app_sandbox import guard

LOGCAT_TIMEOUT = 30.0


async def clear(client, serial: str) -> None:
    guard(serial)
    await client._run("-s", serial, "logcat", "-b", "crash", "-c", timeout=LOGCAT_TIMEOUT)


async def read(client, serial: str, package: str) -> dict:
    """-> {crashed: bool, lines: [...]} cua rieng app nay."""
    guard(serial, package)
    if not PACKAGE_RE.fullmatch(package):
        raise AdbError(f"Package khong hop le: {package!r}")
    out, _, _ = await client._run(
        "-s", serial, "logcat", "-b", "crash", "-d", timeout=LOGCAT_TIMEOUT
    )
    lines = [l.strip() for l in (out or "").splitlines() if package in l]
    return {"crashed": bool(lines), "lines": lines[:20]}
