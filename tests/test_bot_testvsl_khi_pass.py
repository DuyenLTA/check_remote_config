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


TT_BOT = {"co": True, "bieu_thuc": "app.version in ['1.5.0']", "so_key": 0, "nguoi_tao": "bot@x", "cua_toi": True}


def _chay_pass(monkeypatch, tt, xoa=None, dang_test=False):
    """Gia lap QA bao 'test pass' o kenh project; tra (tin gui vao kenh, tin da luu, so lan goi xoa, view gan nut)."""
    gui, nho, xoa_goi, view = [], [], [], []
    tin = SimpleNamespace(id=77, edit=AsyncMock(side_effect=lambda view: view_ghi(view)))

    def view_ghi(v):
        view.append(v)

    async def gui_kenh(_bot, text):
        gui.append(text)
        return tin

    def xoa_fn(project):
        xoa_goi.append(project)
        if isinstance(xoa, Exception):
            raise xoa
        return xoa or "Đã xoá `testvsl`."

    monkeypatch.setattr(b, "_gui_kenh_condition", gui_kenh)
    monkeypatch.setattr(b.bot_cong_viec, "package_cua", lambda _ma, _out: "com.x")
    monkeypatch.setattr(b.tv, "tim_app", lambda _p: {"project": "proj", "app_id": "1:1"})
    monkeypatch.setattr(b.tv, "trang_thai", lambda _p: tt)
    monkeypatch.setattr(b.tv, "xoa", xoa_fn)
    jobs = [{"package": "com.x"}] if dang_test else []
    q = SimpleNamespace(jobs=jobs, bao_lan_dau=lambda _k: True, nho_tin=nho.append,
                        _dang_test=lambda j: dang_test)
    bot = SimpleNamespace(kenh_forum=0, q=q)
    m = SimpleNamespace(id=5, content="AIP944 1.5.0 (9) test pass", jump_url="https://discord/x")
    assert asyncio.run(b.nhan_tin_pass(bot, m, "AIP944", b.OUT)) is True
    return gui, nho, xoa_goi, view


def test_pass_thi_tu_xoa_condition_bot_tao_chi_bao_da_xoa(monkeypatch):
    gui, nho, xoa_goi, view = _chay_pass(monkeypatch, TT_BOT, xoa="Đã xoá `testvsl` (`v`) — version 12.")
    assert xoa_goi == ["proj"]
    assert len(gui) == 1 and "đã tự xoá" in gui[0] and "version 12" in gui[0]
    assert nho == [] and view == []          # khong luu tin nhac, khong gan nut


def test_dang_co_luot_chay_thi_khong_xoa_ma_kem_nut(monkeypatch):
    gui, nho, xoa_goi, view = _chay_pass(monkeypatch, TT_BOT, dang_test=True)
    assert xoa_goi == []
    assert "chưa tự xoá được" in gui[0] and "đang có lượt chạy" in gui[0]
    assert nho and len(view) == 1


def test_xoa_loi_thi_bao_ly_do_kem_nut_thu_lai(monkeypatch):
    gui, nho, xoa_goi, view = _chay_pass(monkeypatch, TT_BOT, xoa=b.RcError("publish lỗi HTTP 409"))
    assert xoa_goi == ["proj"]
    assert "HTTP 409" in gui[0] and "thử lại" in gui[0]
    assert len(view) == 1


def test_condition_nguoi_khac_tao_thi_chi_bao_khong_xoa(monkeypatch):
    tt = {**TT_BOT, "cua_toi": False, "nguoi_tao": "qa-khac@x"}
    gui, nho, xoa_goi, view = _chay_pass(monkeypatch, tt)
    assert xoa_goi == [] and view == []
    assert "người khác tạo" in gui[0]


def test_tin_nhac_vao_condition_fb_khong_co_thi_qa_auto():
    kenh = MagicMock(spec=discord.TextChannel)
    kenh.name = "condition_fb"
    kenh.send = AsyncMock(return_value="tin-cond")
    bot, qa = _bot([], kenh=[kenh])
    assert asyncio.run(b._gui_kenh_condition(bot, "x")) == "tin-cond"
    qa.send.assert_not_awaited()
    bot2, qa2 = _bot([])
    assert asyncio.run(b._gui_kenh_condition(bot2, "x")) == "tin-qa"
