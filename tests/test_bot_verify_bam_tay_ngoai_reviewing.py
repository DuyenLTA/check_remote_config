"""QA bam Verify tay: bug bot log nhung dev chua keo Reviewing (Backlog / To Do) van duoc tim + chay lai."""

from __future__ import annotations

import asyncio
from pathlib import Path

from rcr import bot_job_verify as bj
from rcr import bot_jira_rest as jira
from test_bot_job_verify import BUILD, _Kenh, _bot, _jira

# AIP920-13 Reviewing, AIP920-14 Backlog, AIP920-15 (checklist) Backlog
TT = {"AIP920-13": {"ten": "Reviewing", "xong": False}, "AIP920-14": {"ten": "Backlog", "xong": False},
      "AIP920-15": {"ten": "Backlog", "xong": False}}


def _tt(monkeypatch, tt):
    monkeypatch.setattr(jira, "tim_auto_qa", lambda u, t, project, chua_xong=False: [])
    monkeypatch.setattr(jira, "trang_thai", lambda u, t, keys: {k: tt[k] for k in keys if k in tt})


def test_tu_dong_khi_co_build_moi_van_chi_reviewing(tmp_path, monkeypatch):
    _jira(monkeypatch, {"AIP920-13"})
    _tt(monkeypatch, TT)
    bot = _bot(tmp_path)
    asyncio.run(bj.xep(bot, BUILD, _Kenh()))
    assert [u["key"] for u in bot.q.jobs[0]["verify"]] == ["AIP920-13"]


def test_bam_tay_lay_ca_bug_backlog_bo_bug_done(tmp_path, monkeypatch):
    _jira(monkeypatch, set())
    _tt(monkeypatch, {**TT, "AIP920-13": {"ten": "Closed", "xong": True}})
    bot, kenh = _bot(tmp_path), _Kenh()
    tom = asyncio.run(bj.xep(bot, BUILD, kenh, bam_tay=True))
    j = bot.q.jobs[0]
    assert [(u["key"], u["status"]) for u in j["verify"]] == [("AIP920-14", "Backlog")]
    assert "ngoài Reviewing: AIP920-14" in tom and "đang Backlog" in kenh.sent[0]


def test_bam_tay_khong_co_bug_chua_done(tmp_path, monkeypatch):
    _jira(monkeypatch, set())
    _tt(monkeypatch, {k: {"ten": "Closed", "xong": True} for k in TT})
    assert "chưa Done" in asyncio.run(bj.xep(_bot(tmp_path), BUILD, _Kenh(), bam_tay=True))


def _chay(tmp_path, monkeypatch, kq, tt_sau=TT):
    goi = _jira(monkeypatch, {"AIP920-13"})
    _tt(monkeypatch, TT)
    bot = _bot(tmp_path)
    asyncio.run(bj.xep(bot, BUILD, _Kenh(), bam_tay=True))
    job = bot.q.jobs[0]
    monkeypatch.setattr(bj.bot_cong_viec, "cai", lambda *a: {"ok": True})
    monkeypatch.setattr(bj.bot_chay_claude, "chay", lambda *a: kq)
    monkeypatch.setattr(bj.bot_cong_viec, "file_report", lambda kq, out: None)
    monkeypatch.setattr(jira, "trang_thai", lambda u, t, keys: {k: tt_sau[k] for k in keys if k in tt_sau})
    asyncio.run(bj.chay(bot, job, "S1", "Pixel", Path("."), tmp_path))
    return goi, bot.msg


def test_backlog_pass_thi_done_fail_thi_chi_comment_giu_trang_thai(tmp_path, monkeypatch):
    kq = {"trang_thai": "XONG", "cases": [{"case": "3.6.1#1", "verdict": "FAIL"}, {"case": "3.6.1#2", "verdict": "PASS"}]}
    goi, msg = _chay(tmp_path, monkeypatch, kq)
    assert [(g[0], g[1]) for g in goi] == [("comment", "AIP920-13"), ("chuyen", "AIP920-13"),
                                           ("comment", "AIP920-14"), ("chuyen", "AIP920-14")]
    assert ("chuyen", "AIP920-13", jira.DICH_FAIL) in goi and ("chuyen", "AIP920-14", jira.DICH_PASS) in goi
    kq2 = {"trang_thai": "XONG", "cases": [{"case": "3.6.1#1", "verdict": "PASS"}, {"case": "3.6.1#2", "verdict": "FAIL"}]}
    goi, msg = _chay(tmp_path / "b", monkeypatch, kq2)
    assert ("chuyen", "AIP920-14", jira.DICH_FAIL) not in goi       # Backlog FAIL: khong keo To Do
    cm = next(g[2] for g in goi if g[:2] == ("comment", "AIP920-14"))
    assert "Vẫn lỗi, giữ Backlog" in cm
    noi = [k for k in msg.edits if "content" in k][-1]["content"]
    assert "❌ Vẫn lỗi" in noi and "Nhờ dev" not in (msg.embed("Tin cho dev") or "")


def test_backlog_bi_keo_trong_luc_chay_thi_bo(tmp_path, monkeypatch):
    kq = {"trang_thai": "XONG", "cases": [{"case": "3.6.1#2", "verdict": "PASS"}]}
    goi, msg = _chay(tmp_path, monkeypatch, kq, {**TT, "AIP920-14": {"ten": "In Progress", "xong": False}})
    assert all(g[1] != "AIP920-14" for g in goi)


def test_luot_dung_giu_dung_trang_thai_backlog(tmp_path, monkeypatch):
    goi, msg = _chay(tmp_path, monkeypatch, {"trang_thai": "DUNG", "tom_tat": "x", "cases": []})
    noi = msg.edits[-1]["content"]
    assert goi == [] and "Giữ Backlog" in noi and "Giữ Reviewing" in noi
