"""Phat lai tin build bi lo khi bot khoi dong: kenh gia, khong cham Discord that."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

from rcr import bot_bat_tin_lo as b

BOT_ID = 99


class _Kenh:
    def __init__(self, ten, tin, doc=True, id=0):
        self.name, self._tin, self._doc, self.id = ten, tin, doc, id

    def permissions_for(self, me):
        return SimpleNamespace(read_message_history=self._doc)

    def history(self, **kw):
        async def gen():
            for m in self._tin:
                yield m
        return gen()


def _tin(chu, tac_gia=1):
    return SimpleNamespace(content=chu, author=SimpleNamespace(id=tac_gia), jump_url=f"u/{chu[:6]}")


def test_chi_phat_lai_tin_co_version_o_kenh_project():
    build = _tin("Bản build **AIP882---AI-Video** v4.4.0 (41) đã được hoàn thiện")
    kenh = [_Kenh("aip882-artspire-official-group", [_tin("app hết policy rồi em nhé"), build,
                                                     _tin("🐞 Nhờ dev check bug AIP882 v4.3.0 (40)", BOT_ID)]),
            _Kenh("build-notification", [_tin("AIP927 v1.0.0 (1) đã lên QA")]),
            _Kenh("aip918-x", [_tin("AIP918 v1.0.0 (2)")], doc=False)]
    nhan = []

    async def on_message(m):
        nhan.append(m)
    bot = SimpleNamespace(guilds=[SimpleNamespace(text_channels=kenh, me=None)], user=SimpleNamespace(id=BOT_ID),
                          on_message=on_message)
    assert asyncio.run(b.quet(bot)) == 1
    assert nhan == [build]


def test_qa_auto_phat_lai_build_moi_bo_build_da_hoi():
    """30/10/2026: QA gui AIP886 o qa-auto dung luc bot mat mang -> bot phai bat lai khi ket noi lai."""
    moi = _tin("Bản build AIP886 v2.7.0 (20) đã được hoàn thiện. apply tutorial 3.6.1")
    cu = _tin("AIP882 v4.4.0 (41) chạy lại giúp")
    kenh = [_Kenh("qa-auto", [_tin("ok em"), cu, moi], id=7)]
    nhan = []

    async def on_message(m):
        nhan.append(m)
    bot = SimpleNamespace(guilds=[SimpleNamespace(text_channels=kenh, me=None)], user=SimpleNamespace(id=BOT_ID),
                          on_message=on_message, kenh_build={7},
                          q=SimpleNamespace(tin={"1": {"ma": "AIP882", "version": "4.4.0 (41)"}}))
    assert asyncio.run(b.quet(bot)) == 1
    assert nhan == [moi]
