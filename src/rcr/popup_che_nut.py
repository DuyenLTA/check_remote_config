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


# Popup validator (khung cua so ~320 x 155 dp, ca bong + mui ten) che TRON nut nho nam duoi native (AIP944 Pixel 7
# 17/11/2026: nut Generate man Image to Image nam gon trong popup -> khong ne duoc, phai Dismiss). Nut "Dismiss" o goc
# duoi-phai: tam cach mep phai ~65dp, mep duoi ~37dp. Chi bam popup dung kich thuoc nay (cua so phu khac cua app la
# menu / dialog thi khong dung).
VALIDATOR_DP = ((280, 360), (120, 190))
DISMISS_DP = (65, 37)


def diem_dismiss(khung: list[tuple[int, int, int, int]], mat_do: float) -> list[tuple[int, int]]:
    """Diem bam Dismiss cua moi popup validator trong `khung` (px); `mat_do` = density/160."""
    (wmin, wmax), (hmin, hmax) = VALIDATOR_DP
    ra = []
    for l, t, r, b in khung:
        w, h = (r - l) / mat_do, (b - t) / mat_do
        if wmin <= w <= wmax and hmin <= h <= hmax:
            ra.append((r - int(DISMISS_DP[0] * mat_do), b - int(DISMISS_DP[1] * mat_do)))
    return ra


def la_nut_dismiss(png: bytes, x: int, y: int, ban_kinh: int = 12) -> bool:
    """Diem (x, y) tren anh chup nam tren nut "Dismiss" xanh cua validator (~#1A73E8): >= 1/2 diem quanh do xanh.

    Co cua so khong noi duoc popup co dang hien that: Pixel 7 17/11/2026 popup DANG HIEN van bao `mViewVisibility=0x8`,
    `isReadyForDisplay()=false`, con 5 cua so validator cua man truoc cung co y nhu vay ma KHONG hien -> bam mu vao
    diem Dismiss trung man duoi (mo trang validator / nut cua app). Chi bam khi anh chup thay dung nut."""
    try:
        from io import BytesIO
        from PIL import Image
        im = Image.open(BytesIO(png)).convert("RGB")
    except Exception:                      # noqa: BLE001 - khong doc duoc anh -> coi nhu khong thay nut
        return False
    xanh = tong = 0
    for dx in range(-ban_kinh, ban_kinh + 1, 3):
        for dy in range(-ban_kinh, ban_kinh + 1, 3):
            px, py = x + dx, y + dy
            if 0 <= px < im.width and 0 <= py < im.height:
                r, g, b = im.getpixel((px, py))
                tong += 1
                xanh += r < 80 and 90 <= g <= 150 and b >= 200
    return tong > 0 and xanh * 2 >= tong


async def dong_validator(client, serial: str, package: str) -> int:
    """Bam Dismiss moi popup validator DANG HIEN cua `package` (kiem bang anh chup); tra so popup da dong."""
    from . import screencap
    try:
        out, _, _ = await client.shell(serial, "dumpsys", "window", "windows")
        khung = khung_popup(out, package)
        if not khung:
            return 0
        ds, _, _ = await client.shell(serial, "wm", "density")
        so = re.findall(r"density:\s*(\d+)", ds or "")       # dong cuoi = Override density neu co
        diem = diem_dismiss(khung, int(so[-1]) / 160 if so else 2.75)
        if not diem:
            return 0
        png = await screencap.raw(client, serial)
        bam = [d for d in dict.fromkeys(diem) if la_nut_dismiss(png, *d)]
        for x, y in bam:
            await client.shell(serial, "input", "tap", str(x), str(y))
        return len(bam)
    except Exception:                      # noqa: BLE001 - doc popup hong thi bo qua, buoc sau tu bao loi
        return 0
