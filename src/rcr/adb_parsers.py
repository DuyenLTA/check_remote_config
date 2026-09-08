"""Parse output cua adb + regex loc dau vao. THUAN DU LIEU - khong goi adb.

Tach khoi adb_client de test duoc bang fixture, khong can cam may.

VI SAO PHAI LOC PACKAGE/SERIAL: ten package tester chon di THANG vao dong lenh
`adb shell`, ma adb shell noi cac arg lai roi chay qua `sh` TREN DEVICE. Khong
loc thi "x; pm uninstall com.y" se xoa that app khac tren may.
"""

from __future__ import annotations

import os
import re
import shutil
from dataclasses import dataclass

# Chi cho ky tu hop le cua package/serial that. Khong cho ; | & ` $ ( ) space.
PACKAGE_RE = re.compile(r"[A-Za-z0-9._]+")
SERIAL_RE = re.compile(r"[A-Za-z0-9.:_-]+")

# Ten file frc_* chua dau ':' (vd frc_1:310944273102:android:abc_firebase_activate.json).
# Duong dan tren device luon phai boc nhay khi qua `sh`.
FRC_ACTIVATE_RE = re.compile(r"^frc_(.+)_firebase_activate\.json$")


class AdbError(Exception):
    """Loi adb da doc duoc, hien thang len UI."""


class AdbTransportError(AdbError):
    """Mat ket noi may / chua authorize - khac han loi cua lenh."""


@dataclass(frozen=True, slots=True)
class Device:
    serial: str
    state: str
    model: str = ""

    @property
    def ready(self) -> bool:
        return self.state == "device"

    @property
    def label(self) -> str:
        return f"{self.model or self.serial} ({self.serial})" if self.model else self.serial


def find_adb(explicit: str | None = None) -> str:
    """Tim adb: tham so -> ADB_PATH -> PATH -> duong dan SDK quen thuoc."""
    for cand in (explicit, os.environ.get("ADB_PATH")):
        if cand and os.path.isfile(cand) and os.access(cand, os.X_OK):
            return cand
    found = shutil.which("adb")
    if found:
        return found
    for guess in (
        os.path.expanduser("~/Android/Sdk/platform-tools/adb"),
        os.path.expanduser("~/Library/Android/sdk/platform-tools/adb"),
    ):
        if os.path.isfile(guess) and os.access(guess, os.X_OK):
            return guess
    raise AdbError(
        "Khong tim thay adb. Cai Android platform-tools, hoac dat ADB_PATH=/duong/dan/adb"
    )


def parse_devices(output: str) -> list[Device]:
    """Parse `adb devices -l`. Bo dong header va dong rong."""
    out: list[Device] = []
    for line in output.splitlines():
        line = line.strip()
        if not line or line.startswith("List of devices"):
            continue
        parts = line.split()
        if len(parts) < 2 or not SERIAL_RE.fullmatch(parts[0]):
            continue
        model = ""
        for token in parts[2:]:
            if token.startswith("model:"):
                model = token[len("model:") :]
        out.append(Device(serial=parts[0], state=parts[1], model=model))
    return out


def parse_packages(output: str) -> list[str]:
    """Parse `adb shell pm list packages`. Loc ca ten khong hop le."""
    out = []
    for line in output.splitlines():
        name = line.strip().removeprefix("package:").strip()
        if name and PACKAGE_RE.fullmatch(name):
            out.append(name)
    return sorted(out)


def parse_ls(output: str) -> list[str]:
    """Parse `ls` tren device thanh list ten file. Bo dong loi cua run-as."""
    out = []
    for line in output.splitlines():
        name = line.strip()
        # `run-as` in loi ra stdout tren mot so ROM -> khong duoc coi la ten file.
        if not name or ":" in name and name.startswith(("run-as", "ls")):
            continue
        out.append(name)
    return out


def find_activate_file(names: list[str]) -> tuple[str, str] | None:
    """Tim file activate cua namespace `firebase` -> (ten_file, app_id).

    Bo qua namespace khac (`_fireperf_activate.json`) va file `_defaults.json`:
    chi namespace `firebase` moi la remote config cua app.
    """
    for name in names:
        m = FRC_ACTIVATE_RE.match(name)
        if m:
            return name, m.group(1)
    return None


# `run-as`/`pm`/`am` bao loi ma van exit 0 tren nhieu ROM -> phai quet output.
ERROR_HINTS = (
    "not debuggable",
    "unknown package",
    "permission denied",
    "is not an app",
    "no such file",
    "inaccessible or not found",
)


def output_error(*chunks: str) -> str | None:
    """Tra ve loi thuc su tim thay trong output, hoac None neu sach.

    Dung cho moi lenh run-as/su: returncode khong dang tin.
    """
    joined = " ".join(chunks).lower()
    for hint in ERROR_HINTS:
        if hint in joined:
            return " ".join(c.strip() for c in chunks if c.strip()) or hint
    return None
