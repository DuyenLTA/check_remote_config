"""State dung chung giua cac route: client adb va baseline da doc.

Baseline giu trong bo nho theo (serial, package): doc no ton vai lenh adb, va
moi route sau (patch/verify/restore/testcases) deu can. Mat khi restart server
la binh thuong - tester bam "Doc baseline" lai.
"""

from __future__ import annotations

from fastapi import HTTPException

from .adb_client import AdbClient
from .models import RcBaseline

_client: AdbClient | None = None
_baselines: dict[tuple[str, str], RcBaseline] = {}


def client() -> AdbClient:
    global _client
    if _client is None:
        _client = AdbClient()
    return _client


def put_baseline(bl: RcBaseline) -> None:
    _baselines[(bl.serial, bl.package)] = bl


def get_baseline(serial: str, package: str) -> RcBaseline | None:
    return _baselines.get((serial, package))


def need_baseline(serial: str, package: str) -> RcBaseline:
    bl = get_baseline(serial, package)
    if bl is None:
        raise HTTPException(400, "Chua doc baseline cho app nay. Bam 'Doc baseline' truoc.")
    return bl


def reset() -> None:
    """Chi dung trong test."""
    global _client
    _client = None
    _baselines.clear()
