"""Chua co / sai dieu kien testvsl: bot nhac QA tao, khong chay, khong publish gi len Firebase."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from rcr import bot_kiem_testvsl as k
from rcr import rc_firebase
from rcr.models import RcError

INFO = {"project": "proj-x", "version": "1.6.0", "app_id": "1:2:android:3"}


@pytest.fixture
def firebase(monkeypatch):
    """Template gia + chan moi lenh ghi."""
    tpl = {"conditions": []}
    monkeypatch.setattr(rc_firebase, "da_dang_nhap", lambda: True)
    monkeypatch.setattr(rc_firebase, "token", lambda: "tok")
    monkeypatch.setattr(rc_firebase, "doc", lambda project, tok: (tpl, "etag"))
    monkeypatch.setattr(rc_firebase, "_sua", lambda *a, **kw: pytest.fail("không được publish"))
    monkeypatch.setattr(rc_firebase, "_goi", lambda *a, **kw: pytest.fail("không được gọi API ghi"))

    async def info(client, serial, package):
        return INFO
    monkeypatch.setattr(k.rc_firebase_app, "thong_tin_tren_may", info)
    monkeypatch.setattr(k, "AdbClient", lambda: None)
    return tpl


@pytest.mark.parametrize("dieu_kien, co_loi", [
    ([], "chưa có điều kiện `testvsl`"),
    ([{"name": "khac", "expression": "x"}, {"name": "testvsl", "expression": "app.version == '1.6.0'"}], "thứ 1"),
    ([{"name": "testvsl", "expression": "app.version == '1.5.0'"}], "không nhắc version 1.6.0"),
    ([{"name": "testvsl", "expression": "app.version == '1.6.0'"}], None),
])
def test_kiem_testvsl_chi_doc(firebase, dieu_kien, co_loi):
    firebase["conditions"] = dieu_kien
    loi = asyncio.run(k.THAT("S1", "pkg.a"))
    assert (loi is None) if co_loi is None else (co_loi in loi)


def test_chua_firebase_login_thi_bao_dang_nhap_truoc_khi_chay(monkeypatch):
    """02/11/2026 AIP886 tren Ubuntu: chua firebase login -> Claude chay roi dung o "xin ban debuggable". Bao truoc."""
    monkeypatch.setattr(rc_firebase, "da_dang_nhap", lambda: False)
    loi = asyncio.run(k.THAT("S1", "pkg.a"))
    t = k.tin_nhac({"ma": "AIP886", "version": "2.7.0 (20)", "nguoi_duyet": 7}, loi, set())
    assert "firebase login" in t and "testvsl" not in t and "debuggable" not in t


def test_chi_kiem_ban_release_nhanh_bo_tc():
    assert k.doi_rc_firebase({"loai_ban": "release"}, False)
    assert not k.doi_rc_firebase({"loai_ban": "release"}, True)
    assert not k.doi_rc_firebase({"loai_ban": "release", "drive": "https://d"}, False)
    assert not k.doi_rc_firebase({"loai_ban": "debug"}, False)


def test_tin_nhac_tag_nguoi_bam_va_noi_ro_khong_tu_sua():
    t = k.tin_nhac({"ma": "AIP920", "version": "1.6.0 (7)", "nguoi_duyet": 42}, "chưa có điều kiện", {1, 2})
    assert t.count("<@") == 1 and "<@42>" in t and "thứ 1" in t and "không tự tạo hay sửa" in t
    assert "<@1>" in k.tin_nhac({"ma": "A", "version": "1"}, "x", {1})       # luot verify tu xep: tag QA duyet


def test_thieu_testvsl_thi_khong_chay_claude_va_nhac_qa(tmp_path, monkeypatch):
    from rcr import bot_hang_doi as h
    from rcr import discord_bot as d

    async def thieu(serial, package):
        return "Remote Config chưa có điều kiện `testvsl`"
    monkeypatch.setattr(k, "loi_testvsl", thieu)
    monkeypatch.setattr(d.bot_cong_viec, "cai", lambda *a: {"ok": True})
    monkeypatch.setattr(d.bot_chay_claude, "chay", lambda *a: pytest.fail("không được chạy Claude"))
    bot = object.__new__(d.BuildBot)
    bot.q, bot.ban, bot.duyet = h.HangDoi(tmp_path / "q.json"), {}, {7}
    msg = SimpleNamespace(id=5, edits=[], replies=[])

    async def edit(**kw):
        msg.edits.append(kw)

    async def reply(chu, **kw):
        msg.replies.append(chu)
    msg.edit, msg.reply = edit, reply
    job = {"msg_id": 5, "ma": "AIP920", "ten": "", "version": "1.6.0 (7)", "package": "pkg.a",
           "loai_ban": "release", "nguoi_duyet": 42}
    assert asyncio.run(bot._cai_va_chay(job, msg, "S1", "Pixel")) is False
    assert "<@42>" in msg.replies[-1] and "kq" not in job
    assert [b.custom_id for b in msg.edits[-1]["view"].children] == ["rcr:check:5", "rcr:bo:5"]


def test_dang_nhap_het_han_thi_khong_nho_tao_testvsl():
    """02/11/2026: invalid_rapt -> tin cu bao QA tao / sua testvsl, sai: chi can dang nhap lai tren may bot."""
    loi = f"{k.rc_firebase.HET_HAN} (HTTP 400): chạy lại `firebase login --reauth`"
    t = k.tin_nhac({"ma": "AIP936", "version": "1.9.0 (11)", "nguoi_duyet": 42}, loi, set())
    assert "firebase login --reauth" in t and "Chạy lại" in t and "testvsl" not in t and "<@42>" in t
