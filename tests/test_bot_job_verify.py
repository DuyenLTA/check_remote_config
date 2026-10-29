"""Luot verify bug Reviewing: bot / kenh / Jira / may deu gia."""

from __future__ import annotations

import asyncio
from pathlib import Path

from rcr import bot_job_verify as bj
from rcr import bot_hang_doi as h
from rcr import bot_jira_rest as jira


class _Msg:
    def __init__(self, id_=500):
        self.id, self.edits, self.replies = id_, [], []

    async def edit(self, **k):
        self.edits.append(k)

    async def reply(self, chu, **k):
        self.replies.append(chu)


class _Kenh:
    def __init__(self):
        self.sent = []

    async def send(self, chu, **k):
        self.sent.append(chu)
        return _Msg(500 + len(self.sent))


def _tin():
    return {"1": {"ma": "AIP920", "ten": "", "version": "1.6.0 (7)", "package": "pkg.a", "loai_ban": "debug",
                  "msg_id": 1, "bugs": [{"case": "3.6.1#1", "expected": "Hien inter"}],
                  "jira": {"issues": [{"case": "3.6.1#1", "key": "AIP920-13", "link": "u13", "ghi_chu": "tao moi"},
                                      {"case": "3.6.1#2", "key": "AIP920-14", "link": "u14", "ghi_chu": "tao moi"},
                                      {"case": "HT-03", "key": "AIP920-15", "link": "u15", "ghi_chu": "tao moi"}]}}}


def _bot(tmp_path, token="pat"):
    class B:
        jira_url, jira_token = "https://jira.x", token
        dev_ids = ""

        def get_guild(self, gid):                # khong co kenh project -> bao vao tin verify
            return None
        q = h.HangDoi(tmp_path / "q.json")
        msg = _Msg(501)

        async def _tin_qa(self, msg_id):
            return self.msg
    b = B()
    b.q.tin = _tin()
    return b


BUILD = {"ma": "AIP920", "ten": "", "version": "1.6.1 (8)", "package": "pkg.a", "loai_ban": "debug", "link_tin": "l"}


def _jira(monkeypatch, reviewing, loi_chuyen=(), tu_jira=(), da_co=()):
    goi = []
    monkeypatch.setattr(jira, "da_comment", lambda u, t, k, dau: k in da_co)
    monkeypatch.setattr(jira, "tim_auto_qa", lambda u, t, project: list(tu_jira))
    monkeypatch.setattr(jira, "dang_reviewing", lambda u, t, keys: [k for k in keys if k in reviewing])
    monkeypatch.setattr(jira, "comment", lambda u, t, k, chu: goi.append(("comment", k, chu)))

    def chuyen(u, t, k, ten):
        if k in loi_chuyen:
            raise jira.JiraLoi("HTTP 400")
        goi.append(("chuyen", k, ten))
    monkeypatch.setattr(jira, "chuyen", chuyen)
    return goi


def test_jira_tat_thi_khong_gui_gi(tmp_path):
    kenh = _Kenh()
    assert "tắt" in asyncio.run(bj.xep(_bot(tmp_path, token=""), BUILD, kenh)) and not kenh.sent


def test_khong_bug_reviewing_thi_khong_xep(tmp_path, monkeypatch):
    _jira(monkeypatch, set())
    bot, kenh = _bot(tmp_path), _Kenh()
    assert "không có bug" in asyncio.run(bj.xep(bot, BUILD, kenh))
    assert not kenh.sent and not bot.q.jobs


def test_xep_mot_job_cho_cac_bug_reviewing(tmp_path, monkeypatch):
    _jira(monkeypatch, {"AIP920-13", "AIP920-14", "AIP920-15"})
    bot, kenh = _bot(tmp_path), _Kenh()
    asyncio.run(bj.xep(bot, BUILD, kenh))
    assert len(bot.q.jobs) == 1
    j = bot.q.jobs[0]
    assert j["loai_job"] == "verify" and j["msg_id"] == 501 and [u["key"] for u in j["verify"]] == ["AIP920-13", "AIP920-14"]
    assert [u["key"] for u in j["bo_qua"]] == ["AIP920-15"]
    assert "AIP920-13" in kenh.sent[0] and "nhóm case khác" in kenh.sent[0]
    assert "đã trong hàng đợi" in asyncio.run(bj.xep(bot, BUILD, _Kenh()))   # bam Verify lai lan nua


def _chay(tmp_path, monkeypatch, kq, reviewing_sau, cai=None, loi_chuyen=(), da_co=()):
    goi = _jira(monkeypatch, {"AIP920-13", "AIP920-14", "AIP920-15"}, loi_chuyen, da_co=da_co)
    bot = _bot(tmp_path)
    asyncio.run(bj.xep(bot, BUILD, _Kenh()))
    job = bot.q.jobs[0]
    monkeypatch.setattr(bj.bot_cong_viec, "cai", lambda *a: cai or {"ok": True})
    da_chay = []
    monkeypatch.setattr(bj.bot_chay_claude, "chay", lambda *a: da_chay.append(a[-1]) or kq)
    monkeypatch.setattr(bj.bot_cong_viec, "file_report", lambda kq, out: None)
    monkeypatch.setattr(jira, "dang_reviewing", lambda u, t, keys: [k for k in keys if k in reviewing_sau])
    asyncio.run(bj.chay(bot, job, "S1", "Pixel", Path("."), tmp_path))
    return goi, da_chay, bot.msg


def test_pass_thi_comment_roi_done_fail_thi_to_do(tmp_path, monkeypatch):
    kq = {"trang_thai": "XONG", "link": "https://claude.ai/artifact/r", "tom_tat": "1 PASS 1 FAIL", "cases": [
        {"case": "3.6.1#1", "verdict": "PASS", "thuc_te": "inter hien"},
        {"case": "3.6.1#2", "verdict": "FAIL", "thuc_te": "van loi"}]}
    goi, da_chay, msg = _chay(tmp_path, monkeypatch, kq, {"AIP920-13", "AIP920-14"})
    assert da_chay == [["3.6.1#1", "3.6.1#2"]]
    assert [(g[0], g[1]) + ((g[2],) if g[0] == "chuyen" else ()) for g in goi] == [
        ("comment", "AIP920-13"), ("chuyen", "AIP920-13", jira.DICH_PASS),
        ("comment", "AIP920-14"), ("chuyen", "AIP920-14", jira.DICH_FAIL)]
    assert "PASS trên build 1.6.1 (8)" in goi[0][2]
    assert "Bug reopen" in msg.replies[-1] and "AIP920-14" in msg.replies[-1]   # bao dev ca bug van FAIL
    cuoi = msg.edits[-1]["content"]
    assert "✅ Done" in cuoi and "🔁 To Do" in cuoi and "⏭ Bỏ qua" in cuoi


def test_luot_dung_thi_khong_doi_trang_thai(tmp_path, monkeypatch):
    kq = {"trang_thai": "DUNG", "tom_tat": "can nguoi", "cases": [{"case": "3.6.1#1", "verdict": "PASS"}]}
    goi, _, msg = _chay(tmp_path, monkeypatch, kq, {"AIP920-13", "AIP920-14"})
    assert goi == [] and "Giữ Reviewing" in msg.edits[-1]["content"]


def test_issue_doi_trang_thai_luc_chay_va_jira_loi_mot_issue(tmp_path, monkeypatch):
    kq = {"trang_thai": "XONG", "cases": [{"case": "3.6.1#1", "verdict": "PASS"}, {"case": "3.6.1#2", "verdict": "PASS"}]}
    goi, _, msg = _chay(tmp_path, monkeypatch, kq, {"AIP920-14"})
    assert [g[1] for g in goi] == ["AIP920-14", "AIP920-14"]           # AIP920-13 da roi Reviewing -> bo
    kq2 = dict(kq)
    goi, _, msg = _chay(tmp_path / "b", monkeypatch, kq2, {"AIP920-13", "AIP920-14"}, loi_chuyen={"AIP920-13"})
    assert ("chuyen", "AIP920-14", jira.DICH_PASS) in goi and "Jira lỗi" in msg.edits[-1]["content"]


def test_da_co_comment_bot_thi_chi_chuyen_khong_comment_trung(tmp_path, monkeypatch):
    kq = {"trang_thai": "XONG", "cases": [{"case": "3.6.1#1", "verdict": "PASS"}, {"case": "3.6.1#2", "verdict": "FAIL"}]}
    goi, _, _ = _chay(tmp_path, monkeypatch, kq, {"AIP920-13", "AIP920-14"}, da_co={"AIP920-14"})
    assert [(g[0], g[1]) for g in goi] == [("comment", "AIP920-13"), ("chuyen", "AIP920-13"), ("chuyen", "AIP920-14")]


def test_cai_loi_thi_khong_chay_claude_khong_dong_jira(tmp_path, monkeypatch):
    goi, da_chay, msg = _chay(tmp_path, monkeypatch, {}, set(), cai={"loi": "App Tester chưa có bản"})
    assert goi == [] and da_chay == [] and "Cài không được" in msg.edits[-1]["content"]


def test_build_moi_hon_dang_cho_thi_bo_luot_build_cu(tmp_path, monkeypatch):
    goi = _jira(monkeypatch, {"AIP920-13", "AIP920-14"})
    bot = _bot(tmp_path)
    kenh = _Kenh()
    asyncio.run(bj.xep(bot, BUILD, kenh))
    asyncio.run(bj.xep(bot, {**BUILD, "version": "1.6.2 (9)"}, kenh))
    cu = bot.q.jobs[0]
    monkeypatch.setattr(bj.bot_cong_viec, "cai", lambda *a: (_ for _ in ()).throw(AssertionError("khong duoc cai")))
    asyncio.run(bj.chay(bot, cu, "S1", "Pixel", Path("."), tmp_path))
    assert goi == [] and "1.6.2 (9)" in bot.msg.edits[-1]["content"]
