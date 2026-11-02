"""Gui ket qua luot chay len Discord cho toi khi duoc.

Luot `/rc-check` chay 30-60 phut; mang rot dung luc vua chay xong (29/10/2026 22:42: DNS loi khi sua tin
ket qua) thi truoc day job bi xoa khoi hang -> ket qua + danh sach bug mat han, QA khong biet. Nay:
ket qua (`kq`) duoc ghi vao job trong hang doi NGAY khi chay xong; gui loi mang -> tra may test cho
job khac, cho roi goi lai luot - luot thay `kq` thi chi gui ket qua, khong cai / chay lai. Bot khoi
dong lai giua luc cho -> worker lay job co `kq` (`HangDoi.lay_cho_gui`) va gui tiep.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Awaitable, Callable

import aiohttp
import discord

log = logging.getLogger("rcr-bot")
# Loi tam thoi cua mang / Discord. Loi 4xx (tin bi xoa, thieu quyen) gui lai cung vo ich -> khong o day.
LOI_MANG = (aiohttp.ClientError, asyncio.TimeoutError, discord.DiscordServerError)
CHO_GUI_LAI = 60            # giay giua hai lan gui lai
HAN_GUI_LAI = 12 * 3600     # mat mang qua 12 gio thi thoi, bo job, ghi log
# May phu: luot dai nhat + cai + muc nay phai < bot_may_phu.HAN_MAY_PHU (du phong 15 phut) -> luc bot chinh
# thu hoi job thi may phu chac chan da thoi gui, khong co hai ban ket qua.
HAN_GUI_LAI_MAY_PHU = 10 * 60


async def chay_toi_khi_gui_duoc(mot_luot: Callable[[], Awaitable[None]], job: dict, tra_may: Callable[[], None],
                                cho: float | None = None, han: float | None = None, ngu=asyncio.sleep) -> None:
    """Goi `mot_luot()` (cai + chay + gui ket qua). Loi mang SAU khi job da co `kq` -> tra may, cho `cho`
    giay roi goi lai. Loi mang truoc khi co `kq` (dang cai / chay) hoac qua `han` -> nem ra nhu cu."""
    cho = CHO_GUI_LAI if cho is None else cho
    han = HAN_GUI_LAI if han is None else han
    bat_dau = time.monotonic()
    while True:
        try:
            await mot_luot()
            return
        except LOI_MANG as exc:
            if job.get("kq") is None or time.monotonic() - bat_dau > han:
                raise
            tra_may()          # may test da chay xong, de job khac dung trong luc cho mang
            log.warning("chua gui duoc ket qua %s %s (%s), %ds sau gui lai",
                        job.get("ma"), job.get("version"), exc, cho)
            await ngu(cho)
