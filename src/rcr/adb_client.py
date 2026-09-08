"""Goi adb: truy van may, chay shell. Parse output nam o adb_parsers.py.

Phan doc/ghi trong sandbox cua app (run-as / su) nam o app_sandbox.py.

DIEM QUAN TRONG: `_run` KHONG raise, tra nguyen `(stdout, stderr, code)`.
Thong bao cua `run-as` la thu duy nhat phan biet "app khong debuggable" voi
"chua cai app" voi "SELinux chan" - nuot no di la mat chan doan.
Muon raise thi dung `_checked`.
"""

from __future__ import annotations

import asyncio
import logging

from .adb_parsers import (
    PACKAGE_RE,
    SERIAL_RE,
    AdbError,
    AdbTransportError,
    Device,
    find_adb,
    parse_devices,
    parse_packages,
)

log = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 20.0
PUSH_TIMEOUT = 60.0  # day file qua USB cham hon han lenh shell thuong

TRANSPORT_HINTS = (
    "device not found",
    "device offline",
    "device unauthorized",
    "no devices/emulators found",
    "daemon not running",
)


class AdbClient:
    def __init__(self, adb_path: str | None = None) -> None:
        self.adb = find_adb(adb_path)

    async def _run(
        self, *args: str, timeout: float | None = None
    ) -> tuple[str, str, int]:
        """Chay 1 lenh adb. Tra (stdout, stderr, returncode) - khong raise."""
        proc = await asyncio.create_subprocess_exec(
            self.adb,
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            out, err = await asyncio.wait_for(
                proc.communicate(), timeout=timeout or DEFAULT_TIMEOUT
            )
        except TimeoutError:
            proc.kill()
            await proc.wait()
            raise AdbError(f"adb {' '.join(args)} qua thoi gian cho") from None
        so = out.decode("utf-8", "replace").replace("\r", "")
        se = err.decode("utf-8", "replace").replace("\r", "")
        self._raise_if_transport(se)
        return so, se, proc.returncode or 0

    @staticmethod
    def _raise_if_transport(stderr: str) -> None:
        low = stderr.lower()
        for hint in TRANSPORT_HINTS:
            if hint in low:
                raise AdbTransportError(stderr.strip())

    async def _checked(self, *args: str, timeout: float | None = None) -> str:
        out, err, code = await self._run(*args, timeout=timeout)
        if code != 0:
            raise AdbError((err or out).strip() or f"adb {' '.join(args)} that bai")
        return out

    # ---- truy van may ------------------------------------------------------

    async def devices(self) -> list[Device]:
        return parse_devices(await self._checked("devices", "-l"))

    async def packages(self, serial: str) -> list[str]:
        return parse_packages(
            await self._shell_checked(serial, "pm", "list", "packages", "-3")
        )

    async def version_code(self, serial: str, package: str) -> str:
        """versionCode - dung lam khoa cache cho dex_check (phase 4)."""
        out = await self._shell_checked(serial, "dumpsys", "package", package)
        for line in out.splitlines():
            if "versionCode=" in line:
                return line.split("versionCode=")[1].split()[0]
        return ""

    async def is_debuggable(self, serial: str, package: str) -> bool:
        """Doc co DEBUGGABLE tu `dumpsys package`. Nguon su that ve run-as."""
        out = await self._shell_checked(serial, "dumpsys", "package", package)
        for line in out.splitlines():
            s = line.strip()
            if s.startswith(("flags=", "pkgFlags=")):
                return "DEBUGGABLE" in s
        return False

    # ---- shell -------------------------------------------------------------

    def _guard(self, serial: str, package: str | None = None) -> None:
        if not SERIAL_RE.fullmatch(serial):
            raise AdbError(f"Serial khong hop le: {serial!r}")
        if package is not None and not PACKAGE_RE.fullmatch(package):
            raise AdbError(f"Package khong hop le: {package!r}")

    async def shell(
        self, serial: str, *args: str, timeout: float | None = None
    ) -> tuple[str, str, int]:
        self._guard(serial)
        return await self._run("-s", serial, "shell", *args, timeout=timeout)

    async def _shell_checked(
        self, serial: str, *args: str, timeout: float | None = None
    ) -> str:
        self._guard(serial)
        return await self._checked("-s", serial, "shell", *args, timeout=timeout)

    async def shell_line(
        self, serial: str, line: str, timeout: float | None = None
    ) -> tuple[str, str, int]:
        """Chay 1 dong shell nguyen van (co pipe/redirect).

        CHI dung khi that su can pipe (vd `cat tmp | run-as pkg sh -c 'cat > x'`).
        Moi thanh phan bien doi trong `line` phai da qua _guard hoac la hang so.
        """
        self._guard(serial)
        return await self._run("-s", serial, "shell", line, timeout=timeout)
