"""Bat man + mo khoa may test (PIN 0000 hoac pattern chu "L") de luot chay khong dung cho nguoi.

Luat user 12/11/2026: moi may test mo bang PIN 0000; may dat pattern thi ve chu L (diem 1 -> 4 -> 7 -> 8 -> 9:
xuong cot trai roi sang phai theo hang duoi). May tat man / khoa / khoi dong lai giua luot -> tool tu bat man,
mo khoa roi chay tiep.

Dau hieu may dang khoa: uiautomator bao "null root node", anh chup den, activity khong resolve.
`wm dismiss-keyguard` chi bo duoc man khoa vuot, may dat PIN / pattern thi vo dung.

Ham duoc goi rat thuong xuyen (dau moi case, moi lan dump hong) -> kiem trang thai truoc bang MOT lenh
dumpsys co grep (~0,3s); may dang sang + khong khoa thi tra True ngay, khong gui phim nao.
"""

from __future__ import annotations

import asyncio
import logging
import re

from . import ui_dump
from .app_sandbox import guard

log = logging.getLogger(__name__)

PIN = "0000"
LAN_THU = 3
NGHI = 0.6           # cho keyguard ve xong sau moi thao tac
NGHI_SAU_NHAP = 1.5  # PIN / pattern dung -> keyguard tat mat ~1s
BUOC_NOI = 4         # so diem MOVE noi giua hai diem pattern, cho LockPatternView bat du cac o di qua
# Thu tu o cua chu L tren luoi 3x3 (cot, hang): 1 -> 4 -> 7 -> 8 -> 9.
CHU_L = ((0, 0), (0, 1), (0, 2), (1, 2), (2, 2))

# Mot lenh: wakefulness (dumpsys power) + co keyguard (dumpsys window). Ten co khac nhau theo hang/ban Android:
# Pixel/AOSP "isKeyguardShowing", vivo/OPPO/Redmi ban cu "mShowingLockscreen", "mDreamingLockscreen".
LENH_TRANG_THAI = ("dumpsys power | grep -m1 mWakefulness=; "
                   "dumpsys window | grep -E 'isKeyguardShowing|mShowingLockscreen|mDreamingLockscreen'")
_KHOA_RE = re.compile(r"(isKeyguardShowing|mShowingLockscreen|mDreamingLockscreen)=true")
_SIZE_RE = re.compile(r"(Physical|Override) size:\s*(\d+)x(\d+)")
_PIN_RE = re.compile(r"pinEntry|passwordEntry|pin_entry|password_entry|PasswordTextView|PinView|lockPassword|"
                     r"PasswordView|digit_text|key_enter", re.I)


async def trang_thai(client, serial) -> tuple[bool, bool]:
    """-> (man_sang, dang_khoa). Doc khong ra (lenh loi) -> coi nhu sang + khong khoa, khong lam gi bay."""
    guard(serial)
    try:
        res = await client.shell(serial, LENH_TRANG_THAI)
    except Exception as exc:  # noqa: BLE001 - adb chap chon: khong duoc lam do ca case vi buoc kiem nay
        log.warning("mo_khoa %s: khong doc duoc trang thai man khoa: %s", serial, exc)
        return True, False
    out = (res[0] if isinstance(res, tuple) else "") or ""
    sang = "mWakefulness=" not in out or "mWakefulness=Awake" in out
    return sang, bool(_KHOA_RE.search(out))


async def can_mo(client, serial) -> bool:
    """True neu man dang tat hoac dang khoa."""
    sang, khoa = await trang_thai(client, serial)
    return not sang or khoa


async def _kich_thuoc(client, serial) -> tuple[int, int]:
    out, _, _ = await client.shell(serial, "wm", "size")
    tim = {m.group(1): (int(m.group(2)), int(m.group(3))) for m in _SIZE_RE.finditer(out or "")}
    return tim.get("Override") or tim.get("Physical") or (1080, 2400)


async def _dump_tho(client, serial) -> str:
    """Dump UI truc tiep, KHONG qua ui_dump.dump (ham do goi nguoc mo_khoa khi null root -> de quy)."""
    await client.shell(serial, "uiautomator", "dump", ui_dump.DUMP_PATH)
    xml, _, _ = await client.shell(serial, "cat", ui_dump.DUMP_PATH)
    return xml if "<hierarchy" in (xml or "") else ""


def tim_pattern(xml: str):
    """Node LockPatternView (Pixel: LockPatternView, vivo/OPPO: lop rieng nhung ten van co 'LockPattern')."""
    if not xml:
        return None
    try:
        nodes = ui_dump.parse_dump(xml)
    except Exception:  # noqa: BLE001 - dump hong thi coi nhu khong thay, roi ve nhanh PIN
        return None
    for n in nodes:
        if ("lockpattern" in n.cls.lower() or "lockpattern" in n.resource_id.lower()) and not n.bounds.empty:
            return n
    return None


def diem_chu_l(bounds) -> list[tuple[int, int]]:
    """Tam 5 o cua chu L tinh tu bounds cua LockPatternView (luoi 3x3 chia deu)."""
    w, h = bounds.right - bounds.left, bounds.bottom - bounds.top
    return [(bounds.left + w * (2 * c + 1) // 6, bounds.top + h * (2 * r + 1) // 6) for c, r in CHU_L]


def _noi(diem: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Them diem trung gian giua hai o lien tiep -> chuoi MOVE min, khong nhay coc."""
    ra = [diem[0]]
    for (x0, y0), (x1, y1) in zip(diem, diem[1:]):
        for i in range(1, BUOC_NOI + 1):
            ra.append((x0 + (x1 - x0) * i // BUOC_NOI, y0 + (y1 - y0) * i // BUOC_NOI))
    return ra


async def ve_pattern(client, serial, bounds) -> None:
    """Ve chu L bang `input motionevent` (mot net lien). May khong co motionevent -> noi tung doan `input swipe`."""
    diem = diem_chu_l(bounds)
    (x, y), duong = diem[0], _noi(diem)
    out, err, code = await client.shell(serial, "input", "motionevent", "DOWN", str(x), str(y))
    loi = f"{out} {err}".lower()
    if code == 0 and "error" not in loi and "unknown" not in loi and "usage" not in loi:
        for mx, my in duong[1:]:
            await client.shell(serial, "input", "motionevent", "MOVE", str(mx), str(my))
        await client.shell(serial, "input", "motionevent", "UP", str(diem[-1][0]), str(diem[-1][1]))
        return
    log.info("mo_khoa %s: may khong ho tro input motionevent -> ve bang input swipe tung doan", serial)
    for (x0, y0), (x1, y1) in zip(diem, diem[1:]):
        await client.shell(serial, "input", "swipe", str(x0), str(y0), str(x1), str(y1), "150")


async def _nhap_pin(client, serial) -> None:
    await client.shell(serial, "input", "text", PIN)
    await client.shell(serial, "input", "keyevent", "KEYCODE_ENTER")


async def mo_khoa(client, serial) -> bool:
    """Bat man + mo khoa. True khi may sang va khong khoa; False khi thu het LAN_THU van khoa."""
    sang, khoa = await trang_thai(client, serial)
    if sang and not khoa:
        return True
    log.warning("mo_khoa %s: man %s, %s -> tu bat man + mo khoa", serial,
                "sang" if sang else "tat", "dang khoa" if khoa else "khong khoa")
    for lan in range(1, LAN_THU + 1):
        await client.shell(serial, "input", "keyevent", "KEYCODE_WAKEUP")
        await client.shell(serial, "wm", "dismiss-keyguard")
        await asyncio.sleep(NGHI)
        sang, khoa = await trang_thai(client, serial)
        if sang and not khoa:
            log.info("mo_khoa %s: mo duoc (man khoa vuot / chi can bat man), lan %d", serial, lan)
            return True
        # Vuot len de hien o nhap PIN / luoi pattern.
        w, h = await _kich_thuoc(client, serial)
        await client.shell(serial, "input", "swipe", str(w // 2), str(h * 4 // 5), str(w // 2), str(h // 5), "300")
        await asyncio.sleep(NGHI)
        xml = await _dump_tho(client, serial)
        node = tim_pattern(xml)
        if node is not None:
            log.info("mo_khoa %s: thay LockPatternView %s -> ve chu L", serial, node.bounds)
            await ve_pattern(client, serial, node.bounds)
        else:
            # Thay o PIN, hoac dump khong doc duoc (nhieu may chan dump man khoa) -> van nhap PIN theo luat user.
            log.info("mo_khoa %s: %s -> nhap PIN %s + ENTER", serial,
                     "thay o PIN/mat khau" if _PIN_RE.search(xml or "") else "khong nhan ra man khoa", PIN)
            await _nhap_pin(client, serial)
        await asyncio.sleep(NGHI_SAU_NHAP)
        sang, khoa = await trang_thai(client, serial)
        if sang and not khoa:
            log.info("mo_khoa %s: da mo khoa, lan %d", serial, lan)
            return True
        log.warning("mo_khoa %s: lan %d van khoa", serial, lan)
    log.error("mo_khoa %s: thu %d lan van khong mo duoc khoa", serial, LAN_THU)
    return False
