"""Lenh slash cua bot chinh: /hang-doi, /check, /check-bug."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import discord
from discord import app_commands

from rcr import bot_hang_doi, bot_jira_rest, bot_lenh_slash as s, bot_nhan_build, bot_nut_bam
from rcr.adb_parsers import Device


def _bot(tmp_path, tin=None, jobs=()):
    q = bot_hang_doi.HangDoi(tmp_path / "q.json")
    q.tin = dict(tin or {})
    q.jobs = list(jobs)
    return SimpleNamespace(q=q, ban={}, out=tmp_path, xin_cho={}, jira_url="https://jira.x", jira_token="t",
                           duyet={1}, role=0, _duoc_duyet=lambda u: u.id == 1)


class _Kenh:
    def __init__(self):
        self.sent = []

    async def send(self, chu, **k):
        kenh = self

        class Tin:
            id = 900 + len(kenh.sent)
            jump_url = f"https://discord.com/channels/9/1/{900 + len(kenh.sent)}"
            noi_dung = chu

            async def edit(self, **k):
                kenh.sent[-1] = k.get("content", kenh.sent[-1])
        self.sent.append(chu)
        return Tin()


def test_dang_ky_du_ba_lenh():
    async def chay():
        client = discord.Client(intents=discord.Intents.none())
        bot = SimpleNamespace(tree=app_commands.CommandTree(client))
        s.dang_ky(bot)
        return sorted(c.name for c in bot.tree.get_commands())
    assert asyncio.run(chay()) == ["check", "check-bug", "hang-doi"]


def test_doc_lenh_check():
    tin, loi = s.doc_lenh_check("aip922", "3.7.0 (30)", None)
    assert tin == {"ma": "AIP922", "version": "3.7.0 (30)"} and loi == ""
    tin, _ = s.doc_lenh_check("AIP922", "v3.6.1(12)", "3.6.1")
    assert tin["sdk"] and tin["tutorial"] == "3.6.1" and tin["version"] == "3.6.1 (12)"
    tin, _ = s.doc_lenh_check("AIP922", "3.7.0 (30)", "next-gen")
    assert tin["next_gen"] is True and tin["sdk"]
    assert s.doc_lenh_check("AIP9", "3.7.0 (30)", None)[0] is None
    assert s.doc_lenh_check("AIP922", "3.7.0", None)[0] is None          # thieu code
    assert s.doc_lenh_check("AIP922", "3.7.0 (30)", "moi nhat")[0] is None


def test_check_build_da_thay_tao_tin_hoi_moi_giu_thong_tin_cu(tmp_path):
    cu = {"ma": "AIP922", "ten": "X", "version": "3.7.0 (30)", "package": "p.x", "tutorial": "3.6.1",
          "sdk": True, "next_gen": None, "loai_ban": "release", "msg_id": 5}
    bot = _bot(tmp_path, {"5": cu})
    kenh = _Kenh()

    async def kenh_qa():
        return kenh
    bot._kenh_qa = kenh_qa
    tin, _ = s.doc_lenh_check("AIP922", "3.7.0 (30)", "3.7.0")       # go them SDK khac -> doi nhanh
    kq = asyncio.run(s._check(bot, tin))
    assert "Đã gửi tin hỏi Check mới" in kq
    moi = bot.q.tin["900"]
    assert moi["package"] == "p.x" and moi["tutorial"] == "3.7.0" and "next-gen" in kenh.sent[-1]


def test_check_build_dang_cho_thi_khong_tao_trung(tmp_path):
    cu = {"ma": "AIP922", "ten": "", "version": "3.7.0 (30)", "package": "p.x", "msg_id": 5}
    bot = _bot(tmp_path, {"5": cu}, [dict(cu)])
    bot._kenh_qa = lambda: asyncio.sleep(0, _Kenh())
    kq = asyncio.run(s._check(bot, {"ma": "AIP922", "version": "3.7.0 (30)"}))
    assert "đang chờ / đang chạy" in kq


def test_check_build_chua_thay_can_sdk(tmp_path, monkeypatch):
    bot = _bot(tmp_path)
    bot._kenh_qa = lambda: asyncio.sleep(0, _Kenh())
    assert "gõ thêm `sdk`" in asyncio.run(s._check(bot, {"ma": "AIP922", "version": "3.7.0 (30)"}))
    goi = []

    async def hoi_build_moi(b, tin, link, kenh, out):
        goi.append(tin)
        return "ok"
    monkeypatch.setattr(bot_nhan_build, "hoi_build_moi", hoi_build_moi)
    tin, _ = s.doc_lenh_check("AIP922", "3.7.0 (30)", "3.6.2")
    assert asyncio.run(s._check(bot, tin)) == "ok" and goi[0]["tutorial"] == "3.6.2"


def test_check_chi_qa_duoc_duyet(tmp_path):
    bot = _bot(tmp_path)
    tra = []

    async def send_message(chu, **k):
        tra.append(chu)
    it = SimpleNamespace(user=SimpleNamespace(id=2), response=SimpleNamespace(send_message=send_message))
    asyncio.run(s.lenh_check(bot, it, "AIP922", "3.7.0 (30)", None))
    assert "Chỉ QA" in tra[0]


def test_hang_doi_liet_ke_luot_va_may(tmp_path):
    chay = {"ma": "AIP922", "version": "3.7.0 (30)", "package": "a", "msg_id": 11}
    phu = {"ma": "AIP936", "version": "1.9.0 (11)", "package": "b", "msg_id": 12, "dang_o": "ubuntu:X1"}
    cho = {"ma": "AIP886", "version": "2.7.0 (20)", "package": "c", "msg_id": 13, "loai_job": "verify",
           "verify": [{}, {}]}
    bot = _bot(tmp_path, jobs=[chay, phu, cho])
    bot.q.dang_chay.add(11)
    bot.ban = {"S1": 11}
    may = [Device("S1", "device", "Pixel_4"), Device("S2", "device", "OPPO"), Device("S3", "unauthorized")]

    async def chay_():
        return s.tin_hang_doi(bot, may, "https://discord.com/channels/9/1")
    chu, view = asyncio.run(chay_())
    dang_chay, dang_cho = chu.split("**⏳ Đang chờ**")
    assert "AIP922" in dang_chay and "Pixel_4 (S1)" in dang_chay and "máy phụ `ubuntu:X1`" in dang_chay
    assert "verify 2 bug — **AIP886**" in dang_cho and "/9/1/13" in dang_cho
    assert "OPPO (S2): rảnh" in chu and "chưa sẵn sàng (`unauthorized`)" in chu
    ids = [b.custom_id for b in view.children]
    assert ids == ["rcr:dung:11", "rcr:dung:12", "rcr:huyhd:13"]


def test_hang_doi_may_bi_khoa_ngoai_bot(tmp_path, monkeypatch):
    bot = _bot(tmp_path)
    monkeypatch.setattr(bot_hang_doi, "may_ban", lambda p: True)

    async def chay_():
        return s.tin_hang_doi(bot, [Device("S2", "device", "OPPO")], "u")
    chu, view = asyncio.run(chay_())
    assert "Hàng đợi trống" in chu and "bị khoá bởi lượt chạy ngoài bot" in chu and not view.children


def test_huy_tu_hang_doi_bo_khoi_hang_va_sua_tin_luot(tmp_path):
    job = {"ma": "AIP886", "ten": "", "version": "2.7.0 (20)", "package": "c", "msg_id": 13}
    bot = _bot(tmp_path, {"13": job}, [dict(job)])
    sua, tra = [], []

    async def tin_qa(i):
        async def edit(**k):
            sua.append(k["content"])
        return SimpleNamespace(edit=edit)
    bot._tin_qa = tin_qa

    async def send_message(chu, **k):
        tra.append(chu)
    it = SimpleNamespace(user=SimpleNamespace(id=1, mention="@qa"), response=SimpleNamespace(send_message=send_message))

    async def chay_():
        await bot_nut_bam.huy_tu_hang_doi(bot, it, job)
    asyncio.run(chay_())
    assert bot.q.jobs == [] and "Đã huỷ" in tra[0] and "Đã huỷ khỏi hàng đợi — @qa" in sua[0]


def test_check_bug_co_reviewing_thi_co_nut_verify_build_gan_nhat(tmp_path):
    bot = _bot(tmp_path, {"5": {"ma": "AIP922", "version": "3.6.0 (29)", "package": "p", "msg_id": 5},
                          "8": {"ma": "AIP922", "version": "3.7.0 (30)", "package": "p", "msg_id": 8},
                          "9": {"ma": "AIP111", "version": "1.0.0 (1)", "package": "q", "msg_id": 9}})
    bugs = [{"key": "AIP922-1", "link": "l1", "summary": "Inter splash sai", "status": "Reviewing"},
            {"key": "AIP922-2", "link": "l2", "summary": "Native", "status": "Closed"}]

    async def chay_():
        return s.tin_check_bug("AIP922", bugs, s.build_gan_nhat(bot, "AIP922"))
    chu, view = asyncio.run(chay_())
    assert "2 bug bot đã log, 1 đang Reviewing" in chu and "⏳ [AIP922-1](l1)" in chu and "✅ [AIP922-2]" in chu
    assert "`3.7.0 (30)`" in chu and [b.custom_id for b in view.children] == ["rcr:verify:8"]
    chu, view = s.tin_check_bug("AIP922", bugs, None)
    assert view is None and "chưa thấy build" in chu


def test_bug_cua_app_gop_label_va_key_cu(monkeypatch):
    goi = []

    def _goi(url, token, method, path, body=None):
        goi.append(path)
        return {"issues": [{"key": "AIP922-1", "fields": {"summary": "x", "status": {"name": "Reviewing"}}}]}
    monkeypatch.setattr(bot_jira_rest, "_goi", _goi)
    kq = bot_jira_rest.bug_cua_app("https://jira.x", "t", "AIP922", ["AIP922-7", "xau; drop"])
    assert kq == [{"key": "AIP922-1", "link": "https://jira.x/browse/AIP922-1", "summary": "x", "status": "Reviewing"}]
    from urllib.parse import parse_qs, urlparse
    jql = parse_qs(urlparse(goi[0]).query)["jql"][0]
    assert jql == '(project = AIP922 AND labels = "auto-qa") OR key in (AIP922-7) ORDER BY updated DESC'


def test_goi_y_ma_app_tu_tin_da_thay(tmp_path):
    bot = _bot(tmp_path, {"1": {"ma": "AIP922"}, "2": {"ma": "AIP886"}, "3": {"ma": "AIP922"}})
    assert s.goi_y_ma_app(bot, "") == ["AIP886", "AIP922"] and s.goi_y_ma_app(bot, "92") == ["AIP922"]
