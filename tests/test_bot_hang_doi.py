"""Hang doi bot: FIFO, khong chay trung, luu/khoi phuc, khoa may."""

from __future__ import annotations

import subprocess
import sys

import pytest

from rcr import bot_hang_doi as h


def job(msg_id, package="pkg.a", version="1.0.0 (1)"):
    return {"msg_id": msg_id, "package": package, "version": version, "loai_ban": "debug"}


def test_fifo_va_khong_chay_trung(tmp_path):
    q = h.HangDoi(tmp_path / "q.json")
    assert q.them(job(1)) == 1
    assert q.them(job(2, "pkg.b")) == 2
    assert q.them(job(3)) is None                 # cung package + version da trong hang
    a = q.lay()
    assert a["msg_id"] == 1
    b = q.lay()                                   # may thu hai ranh -> lay job tiep, khong lay lai job 1
    assert b["msg_id"] == 2 and q.lay() is None
    q.xong(a)
    q.them(job(4, "pkg.d"))
    assert q.lay()["msg_id"] == 4 and q.vi_tri(2) == 1


def test_khoi_dong_lai_van_con_job_va_nho_tin(tmp_path):
    p = tmp_path / "q.json"
    q = h.HangDoi(p)
    q.them(job(1))
    q.lay()                                       # bot chet giua luot
    q.nho_tin(job(9, "pkg.c"))
    q2 = h.HangDoi(p)
    assert q2.lay()["msg_id"] == 1                # chay lai tu dau
    assert q2.tin_cua(9)["package"] == "pkg.c"


def test_khoa_may_giua_hai_process(tmp_path):
    lock = h.khoa_may(tmp_path, "SERIAL_A")
    assert not h.may_ban(lock)
    code = ("import sys,time; from pathlib import Path; from rcr import bot_hang_doi as h\n"
            "with h.giu_may(Path(sys.argv[1])):\n print('giu', flush=True); time.sleep(30)")
    p = subprocess.Popen([sys.executable, "-c", code, str(lock)], stdout=subprocess.PIPE, text=True)
    try:
        assert p.stdout.readline().strip() == "giu"
        assert h.may_ban(lock)
        assert not h.may_ban(h.khoa_may(tmp_path, "SERIAL_B"))   # may khac van ranh
        with pytest.raises(BlockingIOError):
            with h.giu_may(lock):
                pass
    finally:
        p.kill()
        p.wait()
    assert not h.may_ban(lock)                    # process chet -> khoa tu nha


def test_verify_va_check_cung_build_khong_chan_nhau(tmp_path):
    q = h.HangDoi(tmp_path / "q.json")
    assert q.them(job(1)) == 1                    # job cu khong co loai_job -> la "check"
    assert q.them({**job(2), "loai_job": "verify"}) == 2
    assert q.trung({**job(3), "loai_job": "verify"}) and q.them({**job(3), "loai_job": "verify"}) is None
    assert q.them({**job(4), "loai_job": "check"}) is None


def test_huy_chi_bo_job_dang_cho(tmp_path):
    q = h.HangDoi(tmp_path / "q.json")
    for i in (1, 2, 3, 4):
        q.them({"msg_id": i, "package": f"p{i}", "version": "1"})
    q.lay()                                              # job 1 dang chay tren may
    q.jobs[2]["dang_o"] = "ubuntu:S9"                    # job 3 dang chay o may phu
    q.cap_nhat(q.jobs[3], kq={"trang_thai": "XONG"})     # job 4 chay xong, cho gui ket qua
    assert [q.huy(i) for i in (1, 3, 4)] == ["dang_chay"] * 3
    assert q.huy(2) == "da_huy" and q.huy(2) == "khong_co"
    assert [j["msg_id"] for j in h.HangDoi(tmp_path / "q.json").jobs] == [1, 3, 4]


def test_bam_huy_tra_lai_nut_check(tmp_path):
    import asyncio
    from types import SimpleNamespace
    from rcr import discord_bot as d
    bot = object.__new__(d.BuildBot)
    bot.q = h.HangDoi(tmp_path / "q.json")
    c = {"msg_id": 5, "ma": "AIP920", "ten": "Lingix", "version": "1.0 (1)", "package": "pkg.a"}
    bot.q.them(dict(c))
    goi = []

    async def edit_message(**k):
        goi.append(k)
    it = SimpleNamespace(user=SimpleNamespace(mention="@qa"), response=SimpleNamespace(edit_message=edit_message))
    asyncio.run(bot._huy(it, c))
    assert bot.q.jobs == [] and "Đã huỷ" in goi[0]["content"]
    assert [b.custom_id for b in goi[0]["view"].children][0] == "rcr:check:5"
