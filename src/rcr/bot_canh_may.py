"""Canh may test dang chay luot: rut cap / `offline` / `unauthorized` qua HAN_MAT_MAY -> tu Dung luot.

Truoc day adb loi trong ~20 giay va rc-check dung, nhung Claude headless khong duoc dan "mat may thi dung" nen co the
thu lai toi het gio (cai 25 phut + chay toi 135 phut) - may bi giu ~160 phut ma QA khong biet. Nay vong worker (bot
chinh, may phu) moi nhip doi chieu may dang giu luot (`bot.ban`) voi `adb devices`: vang mat (hoac khong ready) lien
tuc qua han -> `bot_tien_trinh.dung` nhu QA bam Dung (giet ca cay, bao o tin cua luot, don RC neu duoc).
`adb devices` loi thi bo nhip do - khong duoc coi moi may la mat.
"""

from __future__ import annotations

import asyncio
import logging
import time

from . import bot_tien_trinh

log = logging.getLogger("rcr-bot")
HAN_MAT_MAY = 5 * 60     # tool khong tu reboot may; rut cap cam lai / bam cho phep USB debugging kip trong han nay


class CanhMay:
    def __init__(self):
        self.mat_tu: dict[str, float] = {}      # serial -> luc bat dau vang mat
        self.da_dung: set[str] = set()          # da dung luot dang giu may nay (khong giet lap lai moi nhip)

    def qua_han(self, ban: dict[str, int], san: set[str], bay_gio: float | None = None) -> list[tuple[str, int, int]]:
        """[(serial, msg_id, phut vang mat)] can dung. `ban`: may -> job dang chay; `san`: serial ready luc nay."""
        bay_gio = time.time() if bay_gio is None else bay_gio
        for s in list(self.mat_tu):              # may da tra (luot xong) -> quen
            if s not in ban:
                self.mat_tu.pop(s)
        self.da_dung &= set(ban)
        ra = []
        for serial, msg_id in ban.items():
            if not serial or serial in san:
                self.mat_tu.pop(serial, None)
                continue
            tu = self.mat_tu.setdefault(serial, bay_gio)
            if bay_gio - tu >= HAN_MAT_MAY and serial not in self.da_dung:
                self.da_dung.add(serial)
                ra.append((serial, msg_id, int((bay_gio - tu) // 60)))
        return ra


async def kiem(bot, san: set[str]) -> None:
    """Goi moi nhip sau khi doc duoc `adb devices`. Bot chua co `canh_may` (test) thi tao."""
    canh = getattr(bot, "canh_may", None)
    if canh is None:
        canh = bot.canh_may = CanhMay()
    for serial, msg_id, phut in canh.qua_han(dict(bot.ban), san):
        log.warning("may %s mat ket noi adb %d phut: dung luot %s", serial, phut, msg_id)
        await asyncio.to_thread(bot_tien_trinh.dung, serial,
                                f"máy `{serial}` mất kết nối adb (rút cáp / offline / unauthorized) {phut} phút, "
                                f"bot tự dừng", msg_id)
