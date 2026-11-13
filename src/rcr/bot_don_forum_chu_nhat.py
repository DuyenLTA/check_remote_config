"""Tu don Forum `qa-builds` moi Chu nhat (user chot 13/11/2026): moi app moi version mot bai -> cang ngay cang nhieu.

Tu GIO_DON gio toi Chu nhat (gio may bot), xoa bai bot tao khong co tin moi qua CU_HON_NGAY ngay (bai build vua test
trong tuan giu lai de xem report / log bug), tru bai cua build con trong hang doi / dang chay (lan sau don tiep). Moi Chu nhat mot lan: ngay da don ghi vao `out/bot-don-forum.json` nen restart bot khong don lai.
Bai cua nguoi (khong phai bot tao) giu nguyen. Thieu quyen Manage Threads -> chi ghi log.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path

from . import bot_lenh_xoa_bai as x

log = logging.getLogger("rcr-bot")
CHU_NHAT = 6                       # datetime.weekday()
GIO_DON = 23
CU_HON_NGAY = 7
CHU_KY = 600


def toi_luot(bay_gio: datetime, lan_cuoi: str) -> bool:
    """Chu nhat, tu GIO_DON gio, va hom nay chua don."""
    return bay_gio.weekday() == CHU_NHAT and bay_gio.hour >= GIO_DON and lan_cuoi != bay_gio.date().isoformat()


def _doc(f: Path) -> str:
    try:
        return json.loads(f.read_text(encoding="utf-8")).get("lan_cuoi", "")
    except (OSError, ValueError):
        return ""


async def don(bot) -> tuple[int, int, list[str]]:
    """Xoa bai bot tao im qua CU_HON_NGAY ngay (tru bai dang dung). Tra (da xoa, tong chon, loi)."""
    forum = bot.get_channel(bot.kenh_forum) or await bot.fetch_channel(bot.kenh_forum)
    chon = x.chon_bai(await x.tat_ca_bai(forum), bot.user.id, "", "", CU_HON_NGAY, x.bai_dang_dung(bot))
    da, loi = await x.xoa(chon)
    return da, len(chon), loi


async def vong_lap(bot) -> None:
    await bot.wait_until_ready()
    f = Path(bot.out) / "bot-don-forum.json"
    while not bot.is_closed():
        bay_gio = datetime.now()
        if getattr(bot, "kenh_forum", 0) and toi_luot(bay_gio, _doc(f)):
            try:
                da, tong, loi = await don(bot)
                log.info("don Forum Chu nhat: xoa %d/%d bai %s", da, tong, "; ".join(loi[:3]))
                f.write_text(json.dumps({"lan_cuoi": bay_gio.date().isoformat(), "da_xoa": da}), encoding="utf-8")
            except Exception as exc:          # noqa: BLE001 - loi Discord khong duoc giet vong lap, 10 phut thu lai
                log.warning("don Forum Chu nhat loi: %s", exc)
        await asyncio.sleep(CHU_KY)
