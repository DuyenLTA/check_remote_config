"""Forum qa-builds: moi build mot bai, tin dau bai la tin goc, nhan theo trang thai."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import discord

from rcr import bot_forum as f


def _tag(ten):
    return SimpleNamespace(name=ten)


def _bot(forum=None, kenh=None, tin=None, kenh_forum=99):
    kenh = kenh or {}
    if forum is not None:
        kenh[99] = forum
    return SimpleNamespace(kenh_forum=kenh_forum, duyet={7}, get_channel=lambda i: kenh.get(i),
                           fetch_channel=AsyncMock(side_effect=lambda i: kenh[i]),
                           q=SimpleNamespace(tin=tin or {}, tin_cua=lambda m: (tin or {}).get(str(m))),
                           _kenh_qa=AsyncMock())


def _thread(tid, parent=None):
    t = MagicMock(spec=discord.Thread)
    t.id, t.parent = tid, parent
    t.send = AsyncMock(return_value=SimpleNamespace(id=555, channel=t))
    t.edit = AsyncMock()
    return t


C = {"ma": "AIP916", "version": "1.3.0 (5)", "ten": "Fravix"}


def _forum(*tags):
    forum = MagicMock(spec=discord.ForumChannel)
    forum.available_tags = [_tag(t) for t in tags]
    bai = _thread(1001, forum)
    forum.create_thread = AsyncMock(return_value=SimpleNamespace(thread=bai, message=SimpleNamespace(id=1001, channel=bai)))
    return forum


def test_forum_tat_gui_o_kenh_cu():
    gui = AsyncMock(return_value="tin")
    assert asyncio.run(f.gui_goc(_bot(kenh_forum=0), C, "x", gui)) == "tin"
    gui.assert_awaited_once_with("x")


def test_build_moi_tao_bai_tag_nguoi_duyet_nhan_cho_duyet():
    forum = _forum("PASS", "Chờ duyệt")
    msg = asyncio.run(f.gui_goc(_bot(forum), C, "**AIP916**…"))
    k = forum.create_thread.await_args.kwargs
    assert k["name"] == "AIP916 · 1.3.0 (5) · Fravix" and "<@7>" in k["content"]
    assert [t.name for t in k["applied_tags"]] == ["Chờ duyệt"]
    assert f.kenh_cua(msg) == {"kenh_id": 1001}            # id tin dau bai == id bai


def test_bai_chi_co_verify_khong_gan_cho_duyet():
    forum = _forum("Chờ duyệt")
    asyncio.run(f.gui_goc(_bot(forum), {**C, "loai_job": "verify"}, "verify…"))
    assert forum.create_thread.await_args.kwargs["applied_tags"] == []


def test_forum_sai_cau_hinh_gui_o_qa_auto():
    gui = AsyncMock(return_value="tin qa-auto")
    bot = _bot(SimpleNamespace(id=99))                      # id tro vao kenh van ban, khong phai Forum
    assert asyncio.run(f.gui_goc(bot, C, "x", gui)) == "tin qa-auto"
    forum = _forum()
    forum.create_thread.side_effect = discord.HTTPException(MagicMock(status=403), "Missing Access")
    assert asyncio.run(f.gui_goc(_bot(forum), C, "x", gui)) == "tin qa-auto"


def test_link_tin_tro_vao_bai_forum():
    tin = {"5": {"msg_id": 5, "kenh_id": 1001}}
    bot = _bot(tin=tin)
    assert f.link_tin(bot, {"msg_id": 5}, "https://discord.com/channels/1/2") == "https://discord.com/channels/1/1001/5"
    assert f.link_tin(bot, {"msg_id": 6}, "https://discord.com/channels/1/2") == "https://discord.com/channels/1/2/6"


def test_bai_archive_thi_mo_lai():
    bai = _thread(1001)
    bai.archived = True
    asyncio.run(f.mo_lai(bai))
    bai.edit.assert_awaited_once_with(archived=False)


def test_build_da_co_bai_thi_gui_vao_bai():
    bai = _thread(1001)
    forum = SimpleNamespace(available_tags=[], create_thread=AsyncMock())
    tin = {"1001": {**C, "msg_id": 1001, "kenh_id": 1001}}
    msg = asyncio.run(f.gui_goc(_bot(forum, {1001: bai}, tin), {**C, "loai_job": "verify"}, "verify…"))
    bai.send.assert_awaited_once()
    forum.create_thread.assert_not_awaited()
    assert f.kenh_cua(msg) == {"kenh_id": 1001}


def test_tin_o_kenh_thuong_khong_co_kenh_id():
    assert f.kenh_cua(SimpleNamespace(channel=SimpleNamespace(id=5))) == {}


def test_dat_nhan_theo_ten_bo_qua_verify_va_nhan_thieu():
    forum = SimpleNamespace(available_tags=[_tag("PASS"), _tag("FAIL")])
    bai = _thread(1001, forum)
    tin = {"1001": {**C, "msg_id": 1001, "kenh_id": 1001}}
    bot = _bot(forum, {1001: bai}, tin)
    asyncio.run(f.dat_nhan(bot, {"msg_id": 1001}, f.FAIL))          # job khong mang kenh_id: lay tu tin
    assert [t.name for t in bai.edit.await_args.kwargs["applied_tags"]] == ["FAIL"]
    assert bai.edit.await_args.kwargs["archived"] is False
    bai.edit.reset_mock()
    asyncio.run(f.dat_nhan(bot, {"msg_id": 1001, "loai_job": "verify"}, f.PASS))
    asyncio.run(f.dat_nhan(bot, {"msg_id": 1001}, f.DANG_CHAY))     # forum chua tao nhan nay
    bai.edit.assert_not_awaited()


def test_nhan_ket_qua():
    assert f.nhan_ket_qua({"trang_thai": "XONG"}) == f.PASS
    assert f.nhan_ket_qua({"trang_thai": "XONG", "bugs": [{"case": "1"}]}) == f.FAIL
    assert f.nhan_ket_qua({"trang_thai": "DUNG"}) == f.CAN_XEM


def test_kenh_build_notification_bi_chan_theo_ten():
    from rcr import build_ma_app
    assert build_ma_app.la_kenh_bo("build-notification")
    assert not build_ma_app.la_kenh_bo("qa-auto") and not build_ma_app.la_kenh_bo("aip920-ai-english")


def test_build_khong_sdk_chi_bao_mot_lan(tmp_path):
    from rcr.bot_hang_doi import HangDoi
    q = HangDoi(tmp_path / "q.json")
    assert q.bao_lan_dau("AIP893|2.6.0 (16)") is True
    assert HangDoi(tmp_path / "q.json").bao_lan_dau("AIP893|2.6.0 (16)") is False   # sau restart van nho
