"""Tim diem bam tren nut KHONG bi cua so popup cua app de len (popup "AdMob native ad validator" tren may test).

Popup validator la cua so rieng (ty=APPLICATION, NOT_FOCUSABLE) cua chinh app, khong co trong cay `uiautomator
dump` cua man. Mot popup che nua tren / nua trai nut Next thi diem goc duoi-phai van trong; HAI popup chong nhau
(native OB1 + OB4, vivo V2143 12/11/2026) che ca diem do -> bam vao popup, OB4 lap "nut tiep tuc" toi het gio.
Doc khung cac popup tu `dumpsys window windows` roi chon diem trong nut nam ngoai moi popup.
"""

from __future__ import annotations

import re

_FRAME_RE = re.compile(r"\bframe=\[(-?\d+),(-?\d+)\]\[(-?\d+),(-?\d+)\]")
# Thu tu uu tien (ti le trong nut): goc duoi-phai truoc (cach cu), roi cac diem khac.
DIEM_THU = ((3 / 4, 5 / 6), (0.95, 0.9), (0.95, 0.5), (0.5, 0.9), (0.05, 0.9), (0.5, 0.5), (0.05, 0.1),
            (0.95, 0.1), (0.5, 0.1))
# Nut thuong (buttonLanguageNext, o cau hoi): giua nut truoc nhu cach cu, bi che moi thu cac diem khac.
DIEM_GIUA_TRUOC = ((0.5, 0.5),) + DIEM_THU


def khung_popup(dumpsys: str, package: str) -> list[tuple[int, int, int, int]]:
    """Khung (l, t, r, b) cac cua so phu (ty=APPLICATION) DANG HIEN cua `package`."""
    ra = []
    for khoi in re.split(r"\n\s*Window #\d+ ", dumpsys or ""):
        dau = khoi.split("\n", 1)[0]
        if f"{package}/" not in dau or "ty=APPLICATION " not in khoi or "isVisible=true" not in khoi:
            continue
        m = _FRAME_RE.search(khoi)
        if m:
            ra.append(tuple(int(g) for g in m.groups()))
    return ra


def diem_trong(b, che: list[tuple[int, int, int, int]], thu=DIEM_THU) -> tuple[int, int] | None:
    """Diem dau tien trong `thu` nam trong nut `b` (Bounds) ma ngoai moi khung `che`; het cho -> None."""
    for fx, fy in thu:
        x = b.left + int((b.right - b.left) * fx)
        y = b.top + int((b.bottom - b.top) * fy)
        if not any(l <= x < r and t <= y < bo for l, t, r, bo in che):
            return x, y
    return None


async def diem_bam(client, serial: str, package: str, b, thu=DIEM_THU) -> tuple[int, int]:
    """Diem bam cho nut `b`: ne popup dang de len; khong doc duoc / khong cho nao trong -> diem dau cua `thu`."""
    che: list = []
    if package:
        try:
            out, _, _ = await client.shell(serial, "dumpsys", "window", "windows")
            che = khung_popup(out, package)
        except Exception:                  # noqa: BLE001 - doc popup hong thi bam diem cu
            che = []
    return diem_trong(b, che, thu) or diem_trong(b, [], thu)
