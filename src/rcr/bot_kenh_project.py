"""Bao dev o kenh rieng cua project (tin bug vua log Jira, bug verify van FAIL).

Kenh project nam cung server voi kenh build cua dev, ten bat dau bang ma app viet thuong
(`aip920-ai-english-official-group`). Tag dev mac dinh lay tu `DISCORD_DEV_IDS` (user chot
28/10/2026: tam thoi tag co dinh, chua co bang ma app -> dev). Khong tim duoc kenh / bot khong
co quyen gui (kenh Publishing) -> dang o kenh QA kem noi dung de QA chuyen tay.
"""

from __future__ import annotations

import logging
import re

import discord

log = logging.getLogger("rcr-bot")
LINK_RE = re.compile(r"/channels/(\d+)/(\d+)(?:/(\d+))?")


def dev_ids(gia_tri: str) -> list[int]:
    return [int(x) for x in (gia_tri or "").split(",") if x.strip().isdigit()]


def chon_kenh(kenh: list, ma: str, co_quyen) -> object | None:
    """Kenh text dau tien ten `<ma>-...` ma bot gui duoc (ma khop nguyen, `aip92` khong an `aip920-`)."""
    dau = f"{ma.lower()}-"
    return next((k for k in kenh if k.name.startswith(dau) and co_quyen(k)), None)


async def _kenh_project(bot, c: dict):
    m = LINK_RE.search(c.get("link_tin") or "")
    if not m:
        return None
    g = bot.get_guild(int(m.group(1)))
    if g is None:
        return None

    def co_quyen(k) -> bool:
        p = k.permissions_for(g.me)
        return p.view_channel and p.send_messages

    return chon_kenh(sorted(g.text_channels, key=lambda k: k.position), c.get("ma", ""), co_quyen)


async def bao(bot, c: dict, tin: str, tin_qa) -> None:
    """Gui `tin` o kenh project cua `c['ma']`, tag dev; that bai thi tra loi duoi `tin_qa`."""
    try:
        ids = dev_ids(getattr(bot, "dev_ids", ""))
        tag = " ".join(f"<@{i}>" for i in ids)
        noi_dung = f"{tag}\n{tin}" if tag else tin
        kenh = await _kenh_project(bot, c)
        if kenh is not None:
            await kenh.send(noi_dung[:2000], allowed_mentions=discord.AllowedMentions(
                users=[discord.Object(i) for i in ids], roles=False, everyone=False))
            return
        ly_do = f"không thấy kênh `{c.get('ma', '').lower()}-…` bot gửi được"
    except Exception as exc:             # noqa: BLE001 - bao dev hong khong duoc lam mat ket qua Jira
        log.warning("khong bao duoc dev o kenh project: %s", exc)
        ly_do = str(exc)
    await tin_qa.reply(f"⚠️ Không báo được dev ({ly_do}) — gửi tin này cho dev:\n{tin}"[:2000])
