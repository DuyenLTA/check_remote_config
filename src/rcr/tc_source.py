"""`--tc` nhan duong dan file HOAC link Google Sheet.

Bo TC chuan nam tren Google Sheet (workbook chung moi ban SDK). Doc ban tai tay
trong Downloads la de lech: 02/10 chay ca buoi bang `(2).xlsx` trong khi da co
`(3).xlsx` moi hon. Link sheet thi moi lan chay tai ban MOI NHAT ve `out/`.

Tai qua `/export?format=xlsx` - sheet phai mo cho "ai co link deu xem duoc".
Khong tai duoc thi dung han, khong lui ve file cu nao ca.
"""

from __future__ import annotations

import re
import urllib.request
from pathlib import Path

from .models import RcError

SHEET_RE = re.compile(r"docs\.google\.com/spreadsheets/d/([A-Za-z0-9_-]{20,})")
TIMEOUT = 60


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
    try:
        with urllib.request.urlopen(url, timeout=TIMEOUT) as resp:
            kieu = resp.headers.get("Content-Type", "")
            data = resp.read()
    except OSError as exc:
        raise RcError(f"Khong tai duoc sheet testcase {sheet_id}: {exc}") from exc
    if "spreadsheetml" not in kieu or not data.startswith(b"PK"):
        # Sheet rieng tu -> Google tra trang dang nhap HTML, khong phai xlsx.
        raise RcError(
            f"Sheet {sheet_id} khong tai duoc ve dang xlsx (nhan '{kieu}'). "
            "Mo quyen 'Bat ky ai co duong link deu xem duoc' roi chay lai."
        )
    dich.write_bytes(data)
    return str(dich)
