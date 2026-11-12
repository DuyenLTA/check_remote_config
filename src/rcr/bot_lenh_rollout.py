"""Lenh slash /rollout <ma app>: tra link trang Rollout + link Checklist cua app tren Confluence.

Chi doc Confluence (va <title> sheet de loc checklist cua app khac), khong xep luot, khong dung may -> ai trong
server cung go duoc. Tra loi rieng cho nguoi go (ephemeral) nhu cac lenh khac cua bot.
"""

from __future__ import annotations

import asyncio
import logging

import discord
from discord import app_commands

from . import build_ma_app, confluence_rollout

log = logging.getLogger("rcr-bot")


def dang_ky(tree: app_commands.CommandTree, goi_y_ma) -> None:
    """Gan /rollout vao `tree`; `goi_y_ma` la autocomplete ma app dung chung voi /check."""

    @tree.command(name="rollout", description="Link trang Rollout và link Checklist của app trên Confluence")
    @app_commands.describe(ma_app="Mã app, vd AIP924")
    @app_commands.autocomplete(ma_app=goi_y_ma)
    async def rollout(it: discord.Interaction, ma_app: str):
        await lenh_rollout(it, ma_app)


async def lenh_rollout(it: discord.Interaction, ma_app: str) -> None:
    ma = (ma_app or "").strip().upper()
    if not build_ma_app.MA_RE.fullmatch(ma):
        await it.response.send_message(f"Mã app `{ma_app}` sai mẫu — cần 3 chữ + 3 số, vd `AIP924`.", ephemeral=True)
        return
    await it.response.defer(ephemeral=True, thinking=True)
    try:
        kq = confluence_rollout.tin_tra_loi(await asyncio.to_thread(confluence_rollout.tim, ma))
    except confluence_rollout.ConfluenceLoi as exc:
        kq = f"⛔ Không tra được Confluence: {exc}"
    except Exception as exc:              # noqa: BLE001 - loi bat ngo tra ve cho nguoi go, bot van chay
        log.exception("/rollout loi")
        kq = f"⛔ Lỗi: {exc}"
    await it.followup.send(kq[:2000], ephemeral=True)
