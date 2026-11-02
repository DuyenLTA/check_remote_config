"""Mat mang dung luc gui ket qua: khong mat ket qua, khong chay lai luot, khong gui trung."""

from __future__ import annotations

import asyncio
from pathlib import Path

import aiohttp
import pytest

from rcr import bot_gui_lai as g
from rcr import bot_hang_doi as h
from rcr import bot_job_verify as bj
from rcr import bot_jira_rest as jira

LOI_DNS = aiohttp.ClientConnectionError("Cannot connect to host discord.com:443 [getaddrinfo failed]")


def _chay(mot_luot, job, han=3600):
    tra, ngu = [], []

    async def cho(giay):
        ngu.append(giay)
    asyncio.run(g.chay_toi_khi_gui_duoc(mot_luot, job, lambda: tra.append(1), cho=60, han=han, ngu=cho))
    return tra, ngu


def test_mat_mang_sau_khi_co_kq_thi_tra_may_cho_roi_gui_lai():
    job, lan = {"ma": "AIP920", "version": "1.0 (1)", "kq": {"trang_thai": "XONG"}}, []

    async def mot_luot():
        lan.append(1)
        if len(lan) < 3:
            raise LOI_DNS
    tra, ngu = _chay(mot_luot, job)
    assert len(lan) == 3 and ngu == [60, 60] and tra


def test_mat_mang_khi_chua_co_kq_thi_nem_ra_nhu_cu():
    async def mot_luot():
        raise LOI_DNS
    with pytest.raises(aiohttp.ClientError):
        _chay(mot_luot, {"ma": "AIP920"})


def test_loi_khong_phai_mang_khong_gui_lai():
    async def mot_luot():
        raise ValueError("hong")
    with pytest.raises(ValueError):
        _chay(mot_luot, {"kq": {}})


def test_hang_doi_job_co_kq_chi_gui_lai_khong_can_may(tmp_path):
    q = h.HangDoi(tmp_path / "q.json")
    q.them({"msg_id": 1, "package": "a", "version": "1"})
    q.them({"msg_id": 2, "package": "b", "version": "1"})
    q.cap_nhat(q.jobs[0], kq={"trang_thai": "XONG"}, ten_may="Pixel")
    q2 = h.HangDoi(tmp_path / "q.json")                    # bot khoi dong lai: kq con trong file
    assert q2.lay()["msg_id"] == 2                         # job co kq khong chiem may
    assert [j["msg_id"] for j in q2.lay_cho_gui()] == [1]
    assert q2.lay_cho_gui() == [] and q2.lay() is None     # da lay roi thi khong lay trung


# --- luot verify: lan dau gui loi mang, lan sau chi gui lai -------------------------------------
class _Msg:
    def __init__(self, loi_o=()):
        self.id, self.edits, self.replies, self.loi_o, self.lan = 501, [], [], set(loi_o), 0

    async def edit(self, **k):
        self.edits.append(k)

    async def reply(self, chu, **k):
        self.lan += 1
        if self.lan in self.loi_o:           # reply thu n mat mang
            raise LOI_DNS
        self.replies.append(chu)


def test_verify_gui_loi_thi_lan_sau_khong_chay_lai_khong_doi_jira_lai(tmp_path, monkeypatch):
    class B:
        jira_url, jira_token, dev_ids = "https://jira.x", "pat", ""
        q = h.HangDoi(tmp_path / "q.json")
        msg = _Msg(loi_o={2})        # reply 1: tin da cai; reply 2: tom tat verify -> mat mang

        def get_guild(self, gid):
            return None

        async def _tin_qa(self, msg_id):
            return self.msg
    bot = B()
    job = {"msg_id": 501, "ma": "AIP920", "ten": "", "version": "1.6.1 (8)", "package": "pkg.a",
           "loai_ban": "debug", "loai_job": "verify", "bo_qua": [],
           "verify": [{"key": "AIP920-13", "link": "u13", "case": "3.6.1#1", "bug": {"case": "3.6.1#1", "expected": "e"},
                       "loai_ban_goc": "debug"}]}
    bot.q.them(job)
    job = bot.q.jobs[0]
    chay, chuyen = [], []
    monkeypatch.setattr(bj.bot_cong_viec, "cai", lambda *a: {"ok": True})
    monkeypatch.setattr(bj.bot_cong_viec, "file_report", lambda kq, out: None)
    monkeypatch.setattr(bj.bot_chay_claude, "chay", lambda *a: chay.append(1) or {
        "trang_thai": "XONG", "tom_tat": "1 PASS", "cases": [{"case": "3.6.1#1", "verdict": "PASS"}]})
    monkeypatch.setattr(jira, "dang_reviewing", lambda u, t, keys: list(keys))
    monkeypatch.setattr(jira, "da_comment", lambda *a: False)
    monkeypatch.setattr(jira, "comment", lambda *a: None)
    monkeypatch.setattr(jira, "chuyen", lambda u, t, k, ten: chuyen.append(k))

    async def ngu(giay):
        pass

    async def mot_luot():
        await bj.chay(bot, job, "S1", "Pixel", Path("."), tmp_path)
    asyncio.run(g.chay_toi_khi_gui_duoc(mot_luot, job, lambda: None, ngu=ngu))
    assert chay == [1] and chuyen == ["AIP920-13"]          # chay mot lan, Jira doi mot lan
    assert len(bot.msg.replies) == 2                         # tin da cai + tom tat verify (gui lai lan 2)
    assert job["da_bao"] and h.HangDoi(tmp_path / "q.json").jobs[0]["kq"]["trang_thai"] == "XONG"


def test_check_co_kq_thi_chi_gui_ket_qua_khong_cai_lai(tmp_path, monkeypatch):
    from rcr import discord_bot as d
    bot = object.__new__(d.BuildBot)
    bot.q, bot.ban = h.HangDoi(tmp_path / "q.json"), {}
    msg = _Msg(loi_o={1})                                     # reply ket qua lan dau mat mang

    async def tin_qa(msg_id):
        return msg
    bot._tin_qa = tin_qa
    bot.q.them({"msg_id": 7, "ma": "AIP920", "ten": "Lingix", "version": "1.0 (1)", "package": "pkg.a",
                "kq": {"trang_thai": "XONG"}})              # job moi xep: kq cu (neu co) bi bo
    assert "kq" not in bot.q.jobs[0]
    bot.q.cap_nhat(bot.q.jobs[0], kq={"trang_thai": "XONG", "tom_tat": "ok", "bugs": [BUG]}, ten_may="Pixel", bat_dau=0)
    monkeypatch.setattr(d.bot_cong_viec, "cai", lambda *a: pytest.fail("không được cài lại"))
    monkeypatch.setattr(d.bot_cong_viec, "file_report", lambda kq, out: None)
    monkeypatch.setattr(d.audit_tom_tat, "tim", lambda *a, **k: None)
    monkeypatch.setattr(d.audit_tom_tat, "dong_tin", lambda a: "")
    monkeypatch.setattr(g, "CHO_GUI_LAI", 0)
    job = bot.q.lay_cho_gui()[0]
    bot.ban["S1"] = 99                                        # may S1 dang chay job khac -> khong duoc tra nham
    asyncio.run(bot._chay_tren(job, "", "Pixel"))
    assert len(msg.replies) == 2 and "Lingix" in msg.replies[0] and "bug" in msg.replies[1]
    assert bot.q.jobs == [] and bot.ban == {"S1": 99}


BUG = {"case": "6.4.0#14", "tieu_de": "preload inter", "expected": "e", "thuc_te": "a", "muc_do": "High"}
