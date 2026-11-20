"""QA bao test pass: xoa bai Forum qa-builds cua app (tru bai dang chay), tin nhac xoa testvsl gui vao #condition_fb."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import discord

from rcr import bot_testvsl as b

BOT = 42


def _bai(tid, ten, owner=BOT):
    t = SimpleNamespace(id=tid, name=ten, owner_id=owner, last_message_id=tid)
    t.delete = AsyncMock()
    return t


def _bot(bai, jobs=(), kenh=()):
    async def archived(limit=None):
        for t in ():
            yield t
    forum = SimpleNamespace(threads=bai, archived_threads=archived)
    qa = MagicMock()
    qa.send = AsyncMock(return_value="tin-qa")
    return SimpleNamespace(kenh_forum=9, get_channel=lambda _i: forum, user=SimpleNamespace(id=BOT),
                           q=SimpleNamespace(jobs=list(jobs), tin_cua=lambda _m: None),
                           get_all_channels=lambda: list(kenh), _kenh_qa=AsyncMock(return_value=qa)), qa


def test_xoa_moi_bai_cua_app_tru_bai_dang_chay_va_bai_nguoi():
    a = _bai(1 << 30, "AIP944 · 1.5.0 (9) · AI Photo")
    c = _bai(2 << 30, "AIP944 · 1.4.0 (7) · AI Photo")
    dang = _bai(3 << 30, "AIP944 · 1.6.0 (1) · AI Photo")
    khac = _bai(4 << 30, "AIP895 · 3.2.0 (24) · Photoshoot")
    nguoi = _bai(5 << 30, "AIP944 · hỏi", owner=7)
    bot, _ = _bot([a, c, dang, khac, nguoi], jobs=[{"msg_id": dang.id}])
    assert asyncio.run(b.don_bai_forum(bot, "AIP944")) == 2
    a.delete.assert_awaited_once(); c.delete.assert_awaited_once()
    for t in (dang, khac, nguoi):
        t.delete.assert_not_awaited()


def test_forum_tat_thi_khong_xoa():
    bot, _ = _bot([])
    bot.kenh_forum = 0
    assert asyncio.run(b.don_bai_forum(bot, "AIP944")) == 0


def test_tin_nhac_vao_condition_fb_khong_co_thi_qa_auto():
    kenh = MagicMock(spec=discord.TextChannel)
    kenh.name = "condition_fb"
    kenh.send = AsyncMock(return_value="tin-cond")
    bot, qa = _bot([], kenh=[kenh])
    assert asyncio.run(b._gui_kenh_condition(bot, "x")) == "tin-cond"
    qa.send.assert_not_awaited()
    bot2, qa2 = _bot([])
    assert asyncio.run(b._gui_kenh_condition(bot2, "x")) == "tin-qa"
