"""QA bam Dung luot dang chay: giet ca cay tien trinh, don RC testvsl khi can, tra nut chay lai."""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import threading
import time
from types import SimpleNamespace

import pytest

from rcr import bot_dung_luot as bd
from rcr import bot_hang_doi as h
from rcr import bot_may_phu as mp
from rcr import bot_tien_trinh as tt

# Tien trinh cha sinh mot tien trinh chau ngu lau, ghi pid chau ra file roi cung ngu.
CHA = ("import subprocess,sys,time;"
       "c=subprocess.Popen([sys.executable,'-c','import time;time.sleep(120)']);"
       "open(sys.argv[1],'w').write(str(c.pid));time.sleep(120)")


def _con_song(pid: int) -> bool:
    if os.name == "nt":
        out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"], capture_output=True, text=True).stdout
        return str(pid) in out
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _cho_file(f, giay=20):
    han = time.time() + giay
    while time.time() < han:
        if f.exists() and f.read_text().strip():
            return int(f.read_text())
        time.sleep(0.1)
    pytest.fail("tien trinh chau khong khoi dong")


def test_dung_giet_ca_cay_va_nem_bi_dung(tmp_path):
    f = tmp_path / "pid"
    tt.bat_dau("S1")
    loi = {}

    def chay():
        try:
            tt.chay([sys.executable, "-c", CHA, str(f)], "S1", 300)
        except tt.BiDung as exc:
            loi["dung"] = str(exc)
    t = threading.Thread(target=chay)
    t.start()
    chau = _cho_file(f)
    bat_dau = time.time()
    assert tt.dung("S1", "@qa bấm Dừng")
    t.join(60)
    assert not t.is_alive() and loi["dung"] == "@qa bấm Dừng" and time.time() - bat_dau < 30
    time.sleep(0.5)
    assert not _con_song(chau)                    # chau cung chet, khong mo coi giu khoa may
    with pytest.raises(tt.BiDung):                # lenh sau cung luot khong chay nua
        tt.chay([sys.executable, "-c", "print(1)"], "S1", 30)
    tt.bat_dau("S1")                              # luot moi tren may nay: chay binh thuong
    assert tt.chay([sys.executable, "-c", "print(1)"], "S1", 30).stdout.strip() == "1"


def test_het_gio_giet_ca_cay(tmp_path):
    f = tmp_path / "pid"
    tt.bat_dau("S2")
    with pytest.raises(subprocess.TimeoutExpired):
        tt.chay([sys.executable, "-c", CHA, str(f)], "S2", 3)
    time.sleep(0.5)
    assert not _con_song(_cho_file(f, 1))


def test_chi_don_rc_khi_ban_release_nhanh_bo_tc():
    for job, checklist, can in (({"loai_ban": "release"}, False, True), ({"loai_ban": "release"}, True, False),
                                ({"loai_ban": "debug"}, False, False),
                                ({"loai_ban": "release", "drive": "https://drive"}, False, False)):
        bd.danh_dau_pha_rc(job, checklist)
        assert (job.get("pha") == bd.PHA_RC) == can, job


class _Msg:
    id = 9

    def __init__(self):
        self.edits = []

    async def edit(self, **k):
        self.edits.append(k)


def _bot(tmp_path):
    msg = _Msg()

    async def tin_qa(msg_id):
        return msg
    return SimpleNamespace(_tin_qa=tin_qa, msg=msg, q=h.HangDoi(tmp_path / "q.json"), ban={})


@pytest.mark.parametrize("pha, don", [(bd.PHA_RC, True), (None, False)])
def test_sau_khi_dung_don_testvsl_khi_can_va_tra_nut(tmp_path, monkeypatch, pha, don):
    goi = []

    async def don_testvsl(client, serial, package):
        goi.append((serial, package))
        return "proj-x"
    monkeypatch.setattr(bd.rc_firebase_app, "don_testvsl", don_testvsl)
    monkeypatch.setattr(bd, "AdbClient", lambda: None)
    bot = _bot(tmp_path)
    job = {"msg_id": 9, "ma": "AIP920", "ten": "Lingix", "version": "1.0 (1)", "package": "pkg.a", "pha": pha}
    asyncio.run(bd.sau_khi_dung(bot, job, "S1", "Pixel", "@qa bấm Dừng"))
    cuoi = bot.msg.edits[-1]
    assert "Đã dừng" in cuoi["content"] and ("proj-x" in cuoi["content"]) == don
    assert goi == ([("S1", "pkg.a")] if don else [])
    assert [b.custom_id for b in cuoi["view"].children] == ["rcr:check:9", "rcr:bo:9"]


def test_don_testvsl_loi_thi_bao_qa_kiem_tay(tmp_path, monkeypatch):
    async def hong(*a):
        raise RuntimeError("máy chưa cài pkg.a")
    monkeypatch.setattr(bd.rc_firebase_app, "don_testvsl", hong)
    monkeypatch.setattr(bd, "AdbClient", lambda: None)
    bot = _bot(tmp_path)
    job = {"msg_id": 9, "ma": "AIP920", "ten": "", "version": "1", "package": "pkg.a", "pha": bd.PHA_RC,
           "loai_job": "verify", "verify": []}
    asyncio.run(bd.sau_khi_dung(bot, job, "S1", "Pixel", "x"))
    assert "kiểm tra điều kiện `testvsl`" in bot.msg.edits[-1]["content"]
    assert [b.custom_id for b in bot.msg.edits[-1]["view"].children] == ["rcr:verify:9"]


class _It:
    def __init__(self):
        self.user = SimpleNamespace(mention="@qa")
        self.tra = []

        async def defer(**k):
            pass

        async def send(chu, **k):
            self.tra.append(chu)
        self.response = SimpleNamespace(defer=defer, send_message=send)
        self.followup = SimpleNamespace(send=send)


def test_bam_dung_luot_tren_may_cua_bot_chinh(tmp_path, monkeypatch):
    goi = []
    monkeypatch.setattr(bd.bot_tien_trinh, "dung", lambda serial, ly_do, chu: goi.append((serial, ly_do, chu)) or True)
    bot = _bot(tmp_path)
    bot.q.them({"msg_id": 9, "package": "a", "version": "1"})
    it = _It()
    asyncio.run(bd.bam_dung(bot, it, {"msg_id": 9}))          # chua chay tren may nao
    assert "Huỷ" in it.tra[-1] and not goi
    bot.ban["S1"] = 9
    asyncio.run(bd.bam_dung(bot, it, {"msg_id": 9}))
    assert goi == [("S1", "@qa bấm Dừng", 9)] and "Đang dừng" in it.tra[-1]


def test_bam_dung_luot_o_may_phu_chuyen_lenh_qua_kenh_dieu_phoi(tmp_path, monkeypatch):
    gui = []

    async def gui_dp(kenh, loai, d):
        gui.append((loai, d))
    monkeypatch.setattr(bd.bot_may_phu, "gui", gui_dp)
    bot = _bot(tmp_path)

    async def kenh_dp():
        return None
    bot._kenh_dieu_phoi = kenh_dp
    bot.q.cap_nhat(bot.q.jobs[bot.q.them({"msg_id": 9, "package": "a", "version": "1"}) - 1], dang_o="ubuntu:S8")
    asyncio.run(bd.bam_dung(bot, _It(), {"msg_id": 9}))
    assert gui == [("dung", {"may": "ubuntu", "serial": "S8", "msg_id": 9, "ly_do": "@qa bấm Dừng"})]


def test_may_phu_nhan_lenh_dung_chi_giet_dung_luot(tmp_path, monkeypatch):
    goi = []
    monkeypatch.setattr(mp.bot_tien_trinh, "dung", lambda serial, ly_do, chu: goi.append((serial, chu)))
    bot = SimpleNamespace(ten_may="ubuntu", ban={"S8": 9})
    for d in ({"may": "khac", "serial": "S8", "msg_id": 9}, {"may": "ubuntu", "serial": "S8", "msg_id": 7},
              {"may": "ubuntu", "serial": "S8", "msg_id": 9}):
        asyncio.run(mp.nhan_o_may_phu(bot, "dung", d, None))
    assert goi == [("S8", 9)]


def test_luot_bi_dung_thi_bot_bao_va_bo_job(tmp_path, monkeypatch):
    from rcr import discord_bot as d
    bot = object.__new__(d.BuildBot)
    bot.q, bot.ban, bot.vai_tro = h.HangDoi(tmp_path / "q.json"), {}, "chinh"
    bot.q.them({"msg_id": 9, "ma": "AIP920", "ten": "", "version": "1", "package": "pkg.a", "loai_ban": "release"})
    job = bot.q.lay()
    bot.ban["S1"] = 9

    async def chay(job, serial, ten):
        raise tt.BiDung("@qa bấm Dừng")
    bot._chay = chay
    goi = []

    async def sau(bot_, job_, serial, ten, ly_do):
        goi.append((serial, ly_do))
    monkeypatch.setattr(d.bot_dung_luot, "sau_khi_dung", sau)
    asyncio.run(bot._chay_tren(job, "S1", "Pixel"))
    assert goi == [("S1", "@qa bấm Dừng")] and bot.q.jobs == [] and bot.ban == {}


def test_chay_kem_prompt_lau_hon_mot_nhip(monkeypatch):
    """Luot Claude nhan prompt qua stdin va chay hang chuc phut: goi lai communicate kem input -> ValueError."""
    monkeypatch.setattr(tt, "NHIP", 0.3)
    tt.bat_dau("S3")
    cmd = [sys.executable, "-c", "import sys,time;d=sys.stdin.read();time.sleep(1.5);print(d.upper())"]
    assert tt.chay(cmd, "S3", 30, input="prompt").stdout.strip() == "PROMPT"


def test_bam_dung_muon_khong_giet_job_sau_tren_cung_may():
    tt.bat_dau("S4", 1)
    tt.bat_dau("S4", 2)                     # job 1 xong, job 2 vua nhan may
    assert not tt.dung("S4", "x", 1) and tt.bi_dung("S4") is None
    assert tt.dung("S4", "x", 2) and tt.bi_dung("S4") == "x"
    tt.bat_dau("S4", 3)


def test_khong_don_testvsl_khi_luot_khac_cung_app_dang_chay(tmp_path, monkeypatch):
    async def don_testvsl(*a):
        pytest.fail("không được gỡ testvsl của lượt đang chạy")
    monkeypatch.setattr(bd.rc_firebase_app, "don_testvsl", don_testvsl)
    bot = _bot(tmp_path)
    bot.q.them({"msg_id": 9, "package": "pkg.a", "version": "1"})
    bot.q.them({"msg_id": 10, "package": "pkg.a", "version": "1", "loai_job": "verify"})
    bot.q.lay()
    bot.q.lay()                              # ca hai dang chay tren hai may
    job = {**bot.q.jobs[0], "ma": "AIP920", "ten": "", "pha": bd.PHA_RC}
    asyncio.run(bd.sau_khi_dung(bot, job, "S1", "Pixel", "x"))
    assert "lượt khác của cùng app" in bot.msg.edits[-1]["content"]
