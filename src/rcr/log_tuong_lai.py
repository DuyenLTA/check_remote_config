"""Bo dong logcat co gio "tuong lai" (dong ho may tung chay truoc roi chinh lai).

OPPO CPH2375 (f3466cdb, 19/11/2026): dong ho may tung nhay toi 21/11 roi ve 19/11. logd xep buffer theo gio
nen ~26k dong ghi luc 21/11 (FA-SVC cua app khac, AdInitializer ...) nam cuoi buffer: `logcat -c`, `-G` khong xoa
duoc, `-T <moc>` cung khong loai duoc (gio cua chung lon hon moi moc). `logcat -d` nao cung tra lai chung -> event
cua app khac lan vao case dang chay. Dong nao gio lon hon gio hien tai + `BIEN` la dong cu, bo di.
"""

from __future__ import annotations

import re
import time

BIEN = 3600.0  # lech dong ho may <-> may tinh chi ~1s; dong muon hon 1 gio chac chan khong phai cua lenh vua chay
NUA_NAM = 182 * 86400

_EPOCH = re.compile(r"^\s*(\d{9,11}\.\d+)\s")
_NGAY = re.compile(r"^(\d\d)-(\d\d) (\d\d):(\d\d):(\d\d)(?:\.\d+)?\s")


def _gio(dong: str, bay_gio: float) -> float | None:
    m = _EPOCH.match(dong)
    if m:
        return float(m.group(1))
    m = _NGAY.match(dong)
    if not m:
        return None
    thang, ngay, gio, phut, giay = (int(x) for x in m.groups())
    nam = time.localtime(bay_gio).tm_year
    try:
        t = time.mktime((nam, thang, ngay, gio, phut, giay, 0, 0, -1))
    except (OverflowError, ValueError):
        return None
    # Log thang 12 doc vao thang 1: gan nam hien tai thi thanh "tuong lai" gia -> lui mot nam.
    if t - bay_gio > NUA_NAM:
        t = time.mktime((nam - 1, thang, ngay, gio, phut, giay, 0, 0, -1))
    return t


def loc(text: str, bay_gio: float | None = None) -> str:
    """Bo dong co gio > bay_gio + BIEN. Dong khong co gio (header, dong noi) giu nguyen."""
    if not text:
        return text
    now = time.time() if bay_gio is None else bay_gio
    giu = []
    bo = 0
    for dong in text.split("\n"):
        t = _gio(dong, now)
        if t is not None and t > now + BIEN:
            bo += 1
            continue
        giu.append(dong)
    return text if not bo else "\n".join(giu)


def la_lenh_doc_log(args: tuple[str, ...]) -> bool:
    """`adb ... logcat ... -d ...` (doc buffer roi thoat)."""
    return "logcat" in args and "-d" in args
