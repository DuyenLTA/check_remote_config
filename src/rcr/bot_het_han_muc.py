"""Phien `claude -p` cua bot chet vi tai khoan Claude het han muc 5 tieng -> job KHONG duoc dong.

17/11/2026: AIP944 1.5.0 (9) va AIP927 1.1.0 (3) (job tinh nang 5 tab) chet o tab 1-2 voi
"You've hit your 5-hour limit · resets 5:50pm"; bot ghi LOI, bao ket qua roi bo job -> cac tab con lai khong ai chay.
Gio: job giu trong hang voi `cho_den` = gio reset (+ chut du), toi gio thi chay tiep; tab da xong khong chay lai.
"""

from __future__ import annotations

import json
import re
import time
from datetime import datetime, timedelta
from pathlib import Path

HET_HAN_MUC = "HET_HAN_MUC"
# Reset xong cho them chut: dong ho may va server lech, goi som qua lai dinh 429 ngay.
DU_SAU_RESET = 120
# Khong doc duoc gio reset -> thu lai sau chung nay (het van con han muc thi lai cho tiep).
CHO_MAC_DINH = 30 * 60
RESET_RE = re.compile(r"resets\s+(?:(?P<thang>[A-Z][a-z]{2})\s+(?P<ngay>\d{1,2}),?\s+(?:at\s+)?)?"
                      r"(?P<gio>\d{1,2})(?::(?P<phut>\d{2}))?\s*(?P<ap>am|pm)", re.I)


def la_het_han_muc(d: dict) -> bool:
    """`d`: JSON ket qua cua `claude -p --output-format json`."""
    if d.get("api_error") == "usage_limit_reached":
        return True
    text = str(d.get("result") or "")
    return bool(d.get("is_error")) and "hit your" in text and "limit" in text


def gio_reset(text: str, bay_gio: float | None = None) -> float:
    """"resets 5:50pm (Asia/Bangkok)" / "resets Nov 18, 9am" -> epoch (gio may, may bot dat cung mui gio)."""
    now = datetime.fromtimestamp(bay_gio if bay_gio is not None else time.time())
    m = RESET_RE.search(text or "")
    if not m:
        return now.timestamp() + CHO_MAC_DINH
    gio = int(m["gio"]) % 12 + (12 if m["ap"].lower() == "pm" else 0)
    moc = now.replace(hour=gio, minute=int(m["phut"] or 0), second=0, microsecond=0)
    if m["thang"]:
        try:
            moc = moc.replace(month=datetime.strptime(m["thang"], "%b").month, day=int(m["ngay"]))
        except ValueError:
            pass
        if moc < now - timedelta(days=180):          # "Jan 2" doc vao thang 12 -> sang nam
            moc = moc.replace(year=moc.year + 1)
    elif moc <= now:
        moc += timedelta(days=1)
    return moc.timestamp() + DU_SAU_RESET


def tab_da_xong(repo: Path, package: str, tu_luc: float) -> list[Path]:
    """File luot (`*.luot.json`) cua package da chay XONG tu `tu_luc` - tab do khong chay lai o phien sau."""
    ra = []
    for f in sorted(Path(repo, "out").glob(f"run-{package}-*.luot.json"), key=lambda p: p.stat().st_mtime):
        if f.stat().st_mtime < tu_luc:
            continue
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if d.get("xong") and d.get("records"):
            ra.append(f)
    return ra


def nhac_tab_da_xong(repo: Path, package: str, tu_luc: float | None) -> str:
    """Prompt cho phien chay tiep sau khi het han muc: tab nao da co file luot xong thi giu ket qua."""
    if not tu_luc:
        return ""
    ds = tab_da_xong(repo, package, tu_luc)
    dau = ("\nPhien truoc cua job nay bi cat vi tai khoan Claude het han muc (khong phai loi app). Day la phien CHAY "
           "TIEP: chi chay phan con thieu. ")
    if not ds:
        return dau + "Chua tab nao chay xong.\n"
    return (dau + "Cac file luot sau da chay XONG, KHONG chay lai tu dau: " + ", ".join(f"`{f}`" for f in ds)
            + ". Tab cua file do chi chay lai case chua PASS bang `--case <ds> --gop <file>`; tab khong co file thi "
              "chay binh thuong. Report tong ket gom ca ket qua cac file tren.\n")
