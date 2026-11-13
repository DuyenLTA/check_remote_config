"""/xoa-bai: chon bai build cu trong Forum qa-builds de xoa (bai bot tao, khop app/version/ngay, tru bai dang chay)."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import discord

from rcr import bot_lenh_xoa_bai as x

BOT = 42
BAY_GIO = datetime(2026, 11, 13, tzinfo=timezone.utc)


def _bai(ten, ngay_truoc, owner=BOT, tid=None):
    sf = discord.utils.time_snowflake(BAY_GIO - timedelta(days=ngay_truoc))
    t = SimpleNamespace(id=tid or sf, name=ten, owner_id=owner, last_message_id=sf)
    t.delete = AsyncMock()
    return t


def test_loc_theo_app_version_ngay_va_chu_bai():
    a = _bai("AIP893 · 2.6.0 (23) · AI Photo", 10)
    b = _bai("AIP893 · 2.5.0 (20) · AI Photo", 30)
    c = _bai("AIP916 · 1.3.0 (5) · Fravix", 40)
    nguoi = _bai("AIP893 · hỏi đáp", 50, owner=7)
    ds = [a, b, c, nguoi]
    assert x.chon_bai(ds, BOT, "AIP893", "", None, set(), BAY_GIO) == [b, a]
    assert x.chon_bai(ds, BOT, "AIP893", "2.6.0", None, set(), BAY_GIO) == [a]     # 2.6.0 khop 2.6.0 (23)
    assert x.chon_bai(ds, BOT, "AIP893", "2.6.0 (23)", None, set(), BAY_GIO) == [a]
    assert x.chon_bai(ds, BOT, "AIP893", "2.6", None, set(), BAY_GIO) == []        # khong khop nua chung
    assert x.chon_bai(ds, BOT, "", "", 20, set(), BAY_GIO) == [c, b]                # cu nhat truoc, bo bai nguoi
    assert x.chon_bai(ds, BOT, "AIP893", "", None, {b.id}, BAY_GIO) == [a]          # bai dang chay


def test_bai_dang_dung_lay_ca_kenh_id_tu_tin():
    q = SimpleNamespace(jobs=[{"msg_id": 11, "kenh_id": 100}, {"msg_id": 12}],
                        tin_cua=lambda m: {"12": {"kenh_id": 200}}.get(str(m)))
    assert x.bai_dang_dung(SimpleNamespace(q=q)) == {11, 100, 12, 200}


def test_xoa_dung_som_khi_thieu_quyen():
    a, b = _bai("AIP893 · 1 (1)", 1), _bai("AIP893 · 2 (2)", 1)
    a.delete.side_effect = discord.Forbidden(MagicMock(status=403), "Missing Permissions")
    da, loi = asyncio.run(x.xoa([a, b]))
    assert da == 0 and "Manage Threads" in loi[0]
    b.delete.assert_not_awaited()


def test_tin_xac_nhan_liet_ke_va_bao_bo_qua():
    chu = x.tin_xac_nhan([_bai("AIP893 · 2.6.0 (23) · AI Photo", 3)], 2)
    assert "**1** bài" in chu and "AIP893 · 2.6.0 (23)" in chu and "Bỏ qua 2 bài" in chu


def test_lenh_khong_dieu_kien_thi_tu_choi():
    it = SimpleNamespace(user=SimpleNamespace(id=1), response=SimpleNamespace(send_message=AsyncMock()))
    bot = SimpleNamespace(_duoc_duyet=lambda u: True, kenh_forum=99)
    asyncio.run(x.lenh_xoa_bai(bot, it, None, None, None))
    assert "ma_app" in it.response.send_message.await_args.args[0]


def test_don_chu_nhat_chi_xoa_bai_cu_hon_7_ngay_tru_bai_dang_chay():
    from rcr import bot_don_forum_chu_nhat as d
    cn = datetime(2026, 11, 15, 23, 5)                              # Chu nhat
    assert d.toi_luot(cn, "") and not d.toi_luot(cn, "2026-11-15")
    assert not d.toi_luot(datetime(2026, 11, 15, 22, 0), "")        # chua toi gio
    assert not d.toi_luot(datetime(2026, 11, 14, 23, 30), "")       # thu bay
    a, b = _bai("AIP893 · 2.6.0 (23)", 10), _bai("AIP916 · 1.3.0 (5)", 9)
    moi = _bai("AIP900 · 1.0.0 (1)", 2)                              # build trong tuan: giu
    forum = SimpleNamespace(threads=[a, b, moi], archived_threads=lambda limit=None: _rong())
    bot = SimpleNamespace(kenh_forum=99, get_channel=lambda i: forum, user=SimpleNamespace(id=BOT),
                          q=SimpleNamespace(jobs=[{"msg_id": a.id}], tin_cua=lambda m: None))
    assert asyncio.run(d.don(bot)) == (1, 1, [])
    a.delete.assert_not_awaited()
    b.delete.assert_awaited_once()
    moi.delete.assert_not_awaited()


async def _rong():
    for t in ():
        yield t
