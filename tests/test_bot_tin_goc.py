"""Moi job MOT tin goc: sua tin do thay vi gui tin moi (user chot 09/11/2026)."""
from __future__ import annotations

import json
from types import SimpleNamespace

from rcr import bot_tin_goc as tg
from rcr import discord_notify, discord_tin_goc


def test_thay_embed_cung_ten_giu_embed_khac():
    tin = SimpleNamespace(embeds=[tg.embed(tg.KET_QUA, "41 PASS"), tg.embed(tg.BUG, "cu")])
    ra = tg.thay(tin, tg.embed(tg.BUG, "moi"))
    assert [(e.title, e.description) for e in ra] == [(tg.KET_QUA, "41 PASS"), (tg.BUG, "moi")]
    assert [e.title for e in tg.thay(SimpleNamespace(), tg.embed(tg.TIN_DEV, "x"))] == [tg.TIN_DEV]


def test_embed_va_content_cat_ve_gioi_han_discord():
    assert len(tg.embed("x", "a" * 5000).description) == tg.MAX_EMBED
    assert len(tg.noi("b" * 1990, "c" * 50)) == tg.MAX_CONTENT


def test_view_gop_menu_bug_va_nut_verify():
    from rcr.bot_giao_dien import XAM, nut, view_bug
    bugs = [{"case": "1", "tieu_de": "t", "expected": "e", "thuc_te": "a", "muc_do": "High"}]
    v = tg.view_gop(view_bug(bugs, [], 5), nut(("verify", "Verify bug Jira", XAM), msg_id=5))
    ids = [x.custom_id for x in v.children]
    assert ids[0] == "rcr:chon:5" and ids[-1] == "rcr:verify:5"


def test_luot_chay_tay_tim_tin_goc_moi_nhat_cung_package(tmp_path):
    f = tmp_path / "q.json"
    f.write_text(json.dumps({"tin": {"10": {"package": "a"}, "30": {"package": "a"}, "20": {"package": "b"}}}))
    assert discord_tin_goc.msg_id_goc("a", f) == "30" and discord_tin_goc.msg_id_goc("c", f) == ""


def test_them_dong_vao_tin_goc(tmp_path, monkeypatch):
    f = tmp_path / "q.json"
    f.write_text(json.dumps({"tin": {"30": {"package": "a"}}}))
    monkeypatch.setattr(discord_tin_goc.cau_hinh_bot, "env",
                        lambda k: {"DISCORD_BOT_TOKEN": "tok", "DISCORD_QA_CHANNEL_ID": "99"}.get(k, ""))
    goi = []

    def _goi(method, url, token, payload=None):
        goi.append((method, url, payload))
        return {"content": "**ADA895** `3.3.0`\nĐang chạy /rc-check…"}
    monkeypatch.setattr(discord_tin_goc, "_goi", _goi)
    assert discord_tin_goc.them_dong("a", "✅ Report đã publish", f)
    assert goi[0][:2] == ("GET", "https://discord.com/api/v10/channels/99/messages/30")
    assert goi[1][0] == "PATCH" and goi[1][2]["content"].endswith("Đang chạy /rc-check…\n✅ Report đã publish")
    assert not discord_tin_goc.them_dong("khong-co", "x", f)


def test_notify_co_tin_goc_thi_khong_gui_tin_moi(monkeypatch):
    monkeypatch.setenv("DISCORD_NOTIFY", "1")
    monkeypatch.setattr(discord_notify, "_qua_bot", lambda: ("https://discord.com/api/v10/channels/99/messages", {}))
    them, post = [], []
    monkeypatch.setattr(discord_notify.discord_tin_goc, "them_dong", lambda pkg, dong: them.append(pkg) or True)
    monkeypatch.setattr(discord_notify, "_post", lambda *a, **k: post.append(1) or True)
    assert discord_notify.send("done", "Report đã publish · AIP872", [], link="https://claude.ai/x", package="pkg.a")
    assert them == ["pkg.a"] and post == []
    monkeypatch.setattr(discord_notify.discord_tin_goc, "them_dong", lambda pkg, dong: False)
    assert discord_notify.send("done", "Report đã publish", [], package="pkg.b") and post == [1]


def test_ping_xong_tra_loi_tin_goc_tag_qa_duyet():
    import asyncio
    goi = {}

    class Tin:
        async def reply(self, chu, **kw):
            goi.update(chu=chu, **kw)

    asyncio.run(tg.ping_xong(SimpleNamespace(duyet={42}), Tin(), "🔔 AIP916 xong"))
    assert goi["chu"] == "<@42> 🔔 AIP916 xong"
    assert goi["mention_author"] is False
    assert [u.id for u in goi["allowed_mentions"].users] == [42]
