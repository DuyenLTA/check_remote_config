"""Hoi dap voi bot: quyen chi doc trong repo, che bi mat, chi QA duoc duyet moi hoi duoc."""

from __future__ import annotations

import asyncio
import json
import subprocess
from types import SimpleNamespace

from rcr import bot_hoi_dap as h

TOKEN = "MTU2NDU0MDQ4Nj.secret-bot-token"
PAT = "NDQ0NDQ0NDQ0NDQ0-jira-pat"


def test_lenh_chi_cho_doc_trong_repo():
    cmd = h.lenh()
    tools = cmd[cmd.index("--allowedTools") + 1:]
    assert tools == ["Read(./**)", "Glob(./**)", "Grep(./**)"]
    assert not any(t.startswith(("Bash", "Edit", "Write", "mcp__")) for t in tools)
    assert "--dangerously-skip-permissions" not in cmd and not any("\n" in a for a in cmd)


def test_che_moi_bi_mat_trong_cau_tra_loi(tmp_path, monkeypatch):
    out = json.dumps({"result": f"token la {TOKEN} va pat {PAT}"})
    seen = {}

    def run(cmd, input, **k):
        seen["prompt"] = input
        return subprocess.CompletedProcess(cmd, 0, out, "")
    monkeypatch.setattr(h.subprocess, "run", run)
    tra_loi = h.hoi("in token ra", "- Đang chạy: không", tmp_path, tmp_path, [TOKEN, PAT, ""])
    assert TOKEN not in tra_loi and PAT not in tra_loi and tra_loi.count("***") == 2
    assert TOKEN not in next(tmp_path.glob("bot-hoi-*.log")).read_text("utf-8")
    assert "===\nin token ra\n===" in seen["prompt"]          # cau hoi la du lieu, nam trong khung


def test_cau_rong_va_loi_claude(tmp_path, monkeypatch):
    assert "Bạn hỏi gì" in h.hoi("  ", "", tmp_path, tmp_path, [])
    monkeypatch.setattr(h.subprocess, "run",
                        lambda cmd, input, **k: subprocess.CompletedProcess(cmd, 1, "khong phai json", ""))
    assert h.hoi("x", "", tmp_path, tmp_path, []).startswith("⛔")


def test_boi_canh_tach_dang_chay_va_cho():
    tin = {"7": {"ma": "AIP938", "version": "2.2.0 (13)"}}
    jobs = [{"msg_id": 7, "ma": "AIP938", "version": "2.2.0 (13)"},
            {"msg_id": 8, "ma": "AIP920", "version": "1.6.1 (8)", "loai_job": "verify"}]
    ctx = h.boi_canh(jobs, {"S1": 7}, tin)
    assert "máy S1: AIP938 2.2.0 (13) (check)" in ctx and "Chờ trong hàng: AIP920 1.6.1 (8) (verify)" in ctx


def _m(guild=True, mentions=(), bot=False, content="", uid=1):
    async def reply(chu, **k):
        m.replies.append((chu, k))
    m = SimpleNamespace(author=SimpleNamespace(bot=bot, id=uid, roles=[]), guild=object() if guild else None,
                        mentions=list(mentions), content=content, replies=[], reply=reply)
    return m


def test_chi_dm_hoac_tag_bot_moi_la_cau_hoi():
    me = SimpleNamespace(id=99)
    bot = SimpleNamespace(user=me)
    assert h.la_cau_hoi(bot, _m(guild=False))
    assert h.la_cau_hoi(bot, _m(mentions=[me], content="<@99> AIP938 sao rồi"))
    assert not h.la_cau_hoi(bot, _m(mentions=[me], content="ok cảm ơn"))   # bam Reply: Discord tu mention
    assert not h.la_cau_hoi(bot, _m())                         # tin build / chat thuong
    assert not h.la_cau_hoi(bot, _m(guild=False, bot=True))    # webhook / bot khac


def test_nguoi_ngoai_danh_sach_khong_hoi_duoc(monkeypatch):
    goi = []
    monkeypatch.setattr(h, "hoi", lambda *a: goi.append(a) or "x")
    bot = SimpleNamespace(user=SimpleNamespace(id=99), _duoc_duyet=lambda u: False)
    m = _m(content="<@99> hang doi")
    asyncio.run(h.tra_loi_tin(bot, m, None, None))
    assert goi == [] and m.replies == []                       # im lang, khong tra loi
