"""`--tc` nhan duong dan file HOAC link Google Sheet.

Bo TC chuan nam tren Google Sheet (workbook chung moi ban SDK). Doc ban tai tay
trong Downloads la de lech: 02/10 chay ca buoi bang `(2).xlsx` trong khi da co
`(3).xlsx` moi hon. Link sheet thi moi lan chay tai ban MOI NHAT ve `out/`.

Tai qua `/export?format=xlsx` - sheet phai mo cho "ai co link deu xem duoc".
Khong tai duoc thi dung han, khong lui ve file cu nao ca.
"""

from __future__ import annotations

import http.client
import os
import re
import tempfile
import time
import urllib.request
from pathlib import Path

from .models import RcError

SHEET_RE = re.compile(r"docs\.google\.com/spreadsheets/d/([A-Za-z0-9_-]{20,})")
TIMEOUT = 60
LAN_TAI = 3
LAN_THAY = 6


def la_link(tc: str) -> bool:
    return bool(SHEET_RE.search(tc or ""))


def tai_ve(tc: str, out_dir) -> str:
    """Link sheet -> duong dan file .xlsx vua tai. Duong dan file -> giu nguyen."""
    m = SHEET_RE.search(tc or "")
    if not m:
        return tc
    sheet_id = m.group(1)
    dich = Path(out_dir) / f"tc-{sheet_id}.xlsx"
    dich.parent.mkdir(parents=True, exist_ok=True)
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=xlsx"
    # Google cat ngang luong tai (IncompleteRead, do 2026-10-07) -> tai lai: loi
    # mang thoang qua khong duoc giet ca luot 50 phut truoc khi no kip chay.
    for lan in range(1, LAN_TAI + 1):
        try:
            with urllib.request.urlopen(url, timeout=TIMEOUT) as resp:
                kieu = resp.headers.get("Content-Type", "")
                data = resp.read()
            break
        except (OSError, http.client.HTTPException) as exc:
            if lan == LAN_TAI:
                raise RcError(f"Khong tai duoc sheet testcase {sheet_id}: {exc}") from exc
            time.sleep(2 * lan)
    if "spreadsheetml" not in kieu or not data.startswith(b"PK"):
        # Sheet rieng tu -> Google tra trang dang nhap HTML, khong phai xlsx.
        raise RcError(
            f"Sheet {sheet_id} khong tai duoc ve dang xlsx (nhan '{kieu}'). "
            "Mo quyen 'Bat ky ai co duong link deu xem duoc' roi chay lai."
        )
    _ghi_thay(dich, data)
    return str(dich)


def _ghi_thay(dich: Path, data: bytes) -> None:
    """Ghi ra file tam roi thay vao: hai luot song song (hai may) cung tai sheet ID ads
    thi luot kia khong bao gio doc phai file dang ghi do (do 2026-10-27).

    Windows khong cho thay file ma process khac dang mo (openpyxl read_only giu file)
    -> thu lai vai nhip; van bi giu thi giu ban dang co: no vua duoc luot kia tai ve.
    """
    fd, tam = tempfile.mkstemp(dir=dich.parent, prefix=dich.stem + "-", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        for lan in range(LAN_THAY):
            try:
                os.replace(tam, dich)
                return
            except PermissionError:
                if lan == LAN_THAY - 1 and dich.exists():
                    return
                if lan == LAN_THAY - 1:
                    raise
                time.sleep(0.5)
    finally:
        if os.path.exists(tam):
            os.remove(tam)
