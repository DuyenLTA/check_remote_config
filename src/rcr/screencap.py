"""Chup man hinh may de dan vao report.

Anh la bang chung NGU CANH: no noi man nao dang hien luc chup, khong noi duoc
thoi diem event/ad ban ra. Ket luan van lay tu log va dump.

Thu nho truoc khi nhung: anh goc 1080x2400 PNG ~1-3MB, mot luot 14 case thi
report vuot 16MB. Nen thu ve be ngang 360px + JPEG chat luong 70 (~25KB/anh).

Man hinh TAT thi `screencap` van thanh cong nhung tra ve anh gan nhu den, rat
nho - bat lay va noi ro, khong thi ca report toan anh den ma khong ai hieu.
"""

from __future__ import annotations

import base64
import io
import logging

from .adb_parsers import AdbError
from .app_sandbox import guard

log = logging.getLogger(__name__)

CAPTURE_TIMEOUT = 30.0
THUMB_WIDTH = 360
JPEG_QUALITY = 70
# PNG mot mau (man hinh tat) rat nho; anh that co noi dung thuong > 50KB.
SUSPICIOUS_BYTES = 50_000


def warning(png: bytes) -> str:
    """Cau canh bao neu anh dang nghi, "" neu binh thuong."""
    if not png.startswith(b"\x89PNG"):
        return "du lieu tra ve khong phai PNG"
    if len(png) < SUSPICIOUS_BYTES:
        return f"anh chi {len(png) / 1000:.0f}KB - man hinh co the dang tat hoac khoa"
    return ""


def to_thumb(png: bytes) -> str:
    """PNG goc -> data URI JPEG da thu nho. Loi thi tra "" chu khong lam hong luot chay."""
    try:
        from PIL import Image

        img = Image.open(io.BytesIO(png))
        img.thumbnail((THUMB_WIDTH, THUMB_WIDTH * 4))
        buf = io.BytesIO()
        img.convert("RGB").save(buf, format="JPEG", quality=JPEG_QUALITY, optimize=True)
        return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
    except Exception as exc:  # noqa: BLE001 - anh hong khong duoc lam hong ca luot test
        log.warning("khong thu nho duoc anh: %s", exc)
        return ""


async def capture(client, serial: str) -> dict:
    """-> {thumb: data URI, warning: str}. Khong raise: thieu anh thi bao chu
    khong lam do ca case dang chay."""
    guard(serial)
    runner = getattr(client, "run_binary", None)
    if runner is None:
        return {"thumb": "", "warning": "tang adb nay khong chup anh duoc"}
    try:
        out, err, code = await runner(
            "-s", serial, "exec-out", "screencap", "-p", timeout=CAPTURE_TIMEOUT
        )
    except AdbError as exc:
        return {"thumb": "", "warning": f"khong chup duoc: {exc}"}
    if code != 0 or not out:
        return {"thumb": "", "warning": f"khong chup duoc: {(err or '').strip() or 'anh rong'}"}
    note = warning(out)
    return {"thumb": to_thumb(out), "warning": note}
