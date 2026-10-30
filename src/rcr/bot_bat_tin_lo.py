"""Bot vua khoi dong / ket noi lai: doc lai tin bao build o kenh project + qa-auto ma bot lo trong luc mat ket noi.

30/10/2026 dev bao AIP882 v4.4.0 (41) dung luc bot dang khoi dong lai -> Discord khong gui lai tin cu,
bot im luon. Khi khoi dong, quet tin gan day cua cac kenh project (`aip882-...`), tin nao doc ra ma app +
version thi cho qua `on_message` nhu tin moi. Build da hoi roi thi `on_message` tu bo qua ("build da hoi
roi"), nen quet trung cung khong hoi lai. Chi tin co version: chat thuong / cau hoi trong kenh khong phat lai.
"""

from __future__ import annotations

import datetime as dt
import logging

from . import build_ma_app

log = logging.getLogger("rcr-bot")
CUA_SO = dt.timedelta(hours=3)       # chi xem tin trong 3 gio gan nhat (bot co the doi luot dang chay moi restart)
TOI_DA = 20                          # so tin gan nhat moi kenh


async def quet(bot) -> int:
    """Phat lai tin bao build bi lo; tra so tin da phat lai."""
    tu = dt.datetime.now(dt.timezone.utc) - CUA_SO
    so = 0
    kenh_build = getattr(bot, "kenh_build", set())
    for g in getattr(bot, "guilds", None) or []:
        for k in g.text_channels:
            ma = build_ma_app.ma_cua_kenh(k.name)
            # qa-auto (DISCORD_BUILD_CHANNEL_ID): QA gui build o day - mat mang dung luc gui thi cung phai bat lai
            # (30/10/2026 AIP886 gui luc bot dang reconnect, bot im).
            o_qa = k.id in kenh_build
            if not (ma or o_qa) or not k.permissions_for(g.me).read_message_history:
                continue
            try:
                tin = [m async for m in k.history(limit=TOI_DA, after=tu, oldest_first=True)]
            except Exception as exc:         # noqa: BLE001 - mot kenh loi khong chan kenh khac
                log.warning("khong doc duoc lich su kenh %s: %s", k.name, exc)
                continue
            for m in tin:
                tin_build = build_ma_app.tach(m.content or "", ma)
                if m.author.id == bot.user.id or tin_build is None:
                    continue
                # Tin o qa-auto ma build da hoi roi thi bo: phat lai se lam bot tro ve tin Check cu moi lan reconnect.
                if o_qa and _da_hoi(bot, tin_build):
                    continue
                log.info("phat lai tin build bi lo: %s", m.jump_url)
                await bot.on_message(m)
                so += 1
    return so


def _da_hoi(bot, tin: dict) -> bool:
    q = getattr(bot, "q", None)
    return any(c.get("ma") == tin["ma"] and c.get("version") == tin["version"]
               for c in (getattr(q, "tin", None) or {}).values())
