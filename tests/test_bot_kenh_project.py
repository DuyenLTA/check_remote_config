"""Bao dev o kenh project: chon kenh theo ma app, tag dev, khong gui duoc thi bao kenh QA."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

from rcr import bot_kenh_project as kp


class _Kenh:
    def __init__(self, name, position=0, gui=True):
        self.name, self.position, self.gui, self.sent = name, position, gui, []

    def permissions_for(self, me):
        return SimpleNamespace(view_channel=True, send_messages=self.gui)

    async def send(self, chu, **k):
        self.sent.append((chu, k))


class _Tin:
    def __init__(self):
        self.replies = []

    async def reply(self, chu, **k):
        self.replies.append(chu)


def _bot(kenh, dev="784763920862674944,1023384330803879977"):
    g = SimpleNamespace(me=object(), text_channels=kenh)
    return SimpleNamespace(dev_ids=dev, get_guild=lambda gid: g if gid == 1531654065128214658 else None)


C = {"ma": "AIP920", "link_tin": "https://discord.com/channels/1531654065128214658/1562042798134263920/1564553382080028742"}


def test_chon_kenh_dung_ma_va_co_quyen():
    ks = [_Kenh("aip9200-khac"), _Kenh("aip920-ai-english-official-group", gui=False),
          _Kenh("aip920-ai-english-2"), _Kenh("build-notification")]
    assert kp.chon_kenh(ks, "AIP920", lambda k: k.gui).name == "aip920-ai-english-2"
    assert kp.chon_kenh(ks, "AIP92", lambda k: True) is None


def test_gui_kenh_project_va_tag_dev():
    k = _Kenh("aip920-ai-english-official-group")
    tin = _Tin()
    asyncio.run(kp.bao(_bot([_Kenh("aip918-x"), k]), C, "🐞 Nhờ dev check bug", tin))
    chu, opt = k.sent[0]
    assert chu.startswith("<@784763920862674944> <@1023384330803879977>\n🐞 Nhờ dev check bug")
    am = opt["allowed_mentions"]
    assert [u.id for u in am.users] == [784763920862674944, 1023384330803879977] and not am.everyone
    assert tin.replies == []


def test_khong_co_kenh_thi_bao_o_kenh_qa():
    tin = _Tin()
    asyncio.run(kp.bao(_bot([_Kenh("apb925-ai-video", gui=False)]), {**C, "ma": "APB925"}, "bug", tin))
    assert "Không báo được dev" in tin.replies[0] and tin.replies[0].endswith("bug")
    tin = _Tin()
    asyncio.run(kp.bao(_bot([]), {**C, "link_tin": "https://discord.com/channels/1/2/3"}, "bug", tin))
    assert tin.replies                         # tin build chuyen tiep tu server khac


def test_dev_ids_bo_rac():
    assert kp.dev_ids("1, x,2,") == [1, 2] and kp.dev_ids("") == []


def test_tin_build_o_server_test_thi_tim_kenh_project_o_server_khac():
    """QA gui lai tin build o qa-auto (server test, khong co kenh project) -> van bao dung kenh dev."""
    k = _Kenh("aip922-nexsus-ai-video-official-group")
    test = SimpleNamespace(me=object(), text_channels=[_Kenh("qa-auto")])
    that = SimpleNamespace(me=object(), text_channels=[_Kenh("aip920-x"), k])
    bot = SimpleNamespace(dev_ids="", guilds=[test, that],
                          get_guild=lambda gid: test if gid == 1535317341943107676 else None)
    tin = _Tin()
    c = {"ma": "AIP922", "link_tin": "https://discord.com/channels/1535317341943107676/1562794153082097695/1"}
    asyncio.run(kp.bao(bot, c, "🐞 Nhờ dev check bug", tin))
    assert k.sent and k.sent[0][0] == "🐞 Nhờ dev check bug" and tin.replies == []
