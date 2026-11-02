"""Phan giao dien Discord dung chung cua bot build-watch: nut bam, menu tick bug, doc chu tin, tha tim.

custom_id cua moi nut / menu: `rcr:<hanh_dong>:<msg_id>` - `msg_id` la tin cua bot o kenh QA (khoa cua build
trong `HangDoi.tin`). View `timeout=None`: bot khoi dong lai nut van bam duoc (BuildBot.on_interaction doc
custom_id, khong can view con song).
"""

from __future__ import annotations

import logging

import discord

from . import bot_cong_viec

log = logging.getLogger("rcr-bot")

XANH, XAM = discord.ButtonStyle.success, discord.ButtonStyle.secondary
NUT_HOI = (("check", "Check", XANH), ("bo", "Bỏ qua", XAM), ("verify", "Verify bug Jira", XAM))
# QA gui lai tin build: tin hoi moi chi mang thong tin build, khong mang ket qua / bug / Jira cua luot cu.
GIU_KHI_HOI_LAI = ("ma", "ten", "version", "next_gen", "tutorial", "sdk", "package", "loai_ban")
NUT_BUG = (("jira", "Log Jira", XANH), ("khongbug", "Không có bug thật", XAM))
NUT_HUY = (("huy", "Huỷ", XAM),)            # job dang cho trong hang doi


def noi_dung(m) -> str:
    """Chu cua tin, ke ca tin CHUYEN TIEP: Discord de `content` rong, chu nam trong
    `message_snapshots` (do 2026-10-27, QA forward tin build sang kenh khac)."""
    phan = [m.content or ""] + [s.content or "" for s in getattr(m, "message_snapshots", None) or []]
    return "\n".join(p for p in phan if p)


def nut(*cac: tuple[str, str, discord.ButtonStyle], msg_id: int) -> discord.ui.View:
    v = discord.ui.View(timeout=None)
    for hanh_dong, nhan, kieu in cac:
        v.add_item(discord.ui.Button(label=nhan, style=kieu, custom_id=f"rcr:{hanh_dong}:{msg_id}"))
    return v


async def tha_tim(m) -> None:
    """Tha ❤️ vao tin bao build de dev biet bot da nhan. Thieu quyen Add Reactions / tin da xoa -> bo qua,
    khong duoc chan viec hoi QA."""
    try:
        await m.add_reaction("❤️")
    except Exception as exc:                 # noqa: BLE001
        log.warning("khong tha tim duoc vao tin build %s: %s", getattr(m, "jump_url", ""), exc)


def view_bug(bugs: list[dict], chon: list[int], msg_id: int) -> discord.ui.View:
    """Menu tick bug (nhieu lua chon) + nut Log Jira / Khong co bug. Ve lai sau moi lan tick
    -> lua chon da tick phai la `default`, khong thi menu tu xoa trang."""
    v = discord.ui.View(timeout=None)
    v.add_item(discord.ui.Select(
        custom_id=f"rcr:chon:{msg_id}", placeholder="Tick bug thật…", min_values=0, max_values=len(bugs),
        options=[discord.SelectOption(label=nhan, value=gt, description=mo_ta, default=int(gt) in chon)
                 for gt, nhan, mo_ta in bot_cong_viec.lua_chon_bug(bugs)]))
    for hanh_dong, nhan, kieu in NUT_BUG:
        v.add_item(discord.ui.Button(label=nhan, style=kieu, custom_id=f"rcr:{hanh_dong}:{msg_id}"))
    return v
