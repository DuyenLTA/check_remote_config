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
    assert "máy S1: AIP938 2.2.0 (13) (check)" in ctx and "AIP920 1.6.1 (8) (verify)" in ctx.split("Chờ trong hàng")[1]


def test_boi_canh_tach_job_may_phu_va_job_dang_gui_lai():
    jobs = [{"msg_id": 7, "ma": "AIP938", "version": "1", "dang_o": "ubuntu:S8"},
            {"msg_id": 8, "ma": "AIP920", "version": "2", "kq": {"trang_thai": "XONG"}},
            {"msg_id": 9, "ma": "AIP805", "version": "3"}]
    ctx = h.boi_canh(jobs, {}, {})
    dong = dict(d[2:].split(": ", 1) for d in ctx.splitlines())
    assert "máy phụ ubuntu:S8: AIP938 1 (check)" in dong["Đang chạy"]
    assert dong["Chạy xong, đang gửi lại kết quả (mất mạng)"] == "AIP920 2 (check)"
    assert dong["Chờ trong hàng (cùng app thì chạy lần lượt)"] == "AIP805 3 (check)"


def _m(guild=True, mentions=(), bot=False, content="", uid=1, ref=None, **_):
    async def reply(chu, **k):
        m.replies.append((chu, k))
    m = SimpleNamespace(author=SimpleNamespace(bot=bot, id=uid, roles=[]), guild=object() if guild else None,
                        mentions=list(mentions), content=content, replies=[], reply=reply,
                        reference=SimpleNamespace(resolved=ref) if ref else None)
    return m


def test_chi_dm_hoac_tag_bot_moi_la_cau_hoi():
    me = SimpleNamespace(id=99)
    bot = SimpleNamespace(user=me)
    assert h.la_cau_hoi(bot, _m(guild=False))
    assert h.la_cau_hoi(bot, _m(mentions=[me], content="<@99> AIP938 sao rồi"))
    assert not h.la_cau_hoi(bot, _m(mentions=[me], content="ok cảm ơn"))   # bam Reply: Discord tu mention
    assert not h.la_cau_hoi(bot, _m())                         # tin build / chat thuong
    assert not h.la_cau_hoi(bot, _m(guild=False, bot=True))    # webhook / bot khac


def test_server_hoi_tu_do_khong_can_tag():
    me = SimpleNamespace(id=99)
    bot = SimpleNamespace(user=me, _duoc_duyet=lambda u: u.id == 1)
    g = SimpleNamespace(id=h.GUILD_HOI_TU_DO)

    def m(**k):
        x = _m(**k)
        x.guild = k.get("g", g)
        return x
    tin_bot = SimpleNamespace(author=me)
    assert h.la_cau_hoi(bot, m(content="AIP916 chạy tới đâu rồi"))                 # nhan thuong
    assert h.la_cau_hoi(bot, m(content="ok cảm ơn", ref=tin_bot))                  # Reply tin bot
    assert h.la_cau_hoi(bot, m(content="AIP916 v1.3.0 (5)", ref=tin_bot))          # Reply bot: van la hoi
    assert not h.la_cau_hoi(bot, m(content="AIP916 v1.3.0 (5) sdk 3.7.1"))         # gui lai tin build
    assert not h.la_cau_hoi(bot, m(content=""))                                    # chi anh / sticker
    assert not h.la_cau_hoi(bot, m(content="hỏi gì đó", uid=2))                    # ngoai danh sach duyet
    assert not h.la_cau_hoi(bot, m(content="hỏi gì đó", bot=True))                 # webhook / bot khac
    assert not h.la_cau_hoi(bot, m(content="ok cảm ơn", ref=tin_bot, g=SimpleNamespace(id=5)))  # server khac


def test_nguoi_ngoai_danh_sach_khong_hoi_duoc(monkeypatch):
    goi = []
    monkeypatch.setattr(h, "hoi", lambda *a: goi.append(a) or "x")
    bot = SimpleNamespace(user=SimpleNamespace(id=99), _duoc_duyet=lambda u: False)
    m = _m(content="<@99> hang doi")
    asyncio.run(h.tra_loi_tin(bot, m, None, None))
    assert goi == [] and m.replies == []                       # im lang, khong tra loi
