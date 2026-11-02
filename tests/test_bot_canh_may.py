"""May test dang chay luot mat ket noi adb qua han -> bot tu Dung luot (nhu QA bam Dung)."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

from rcr import bot_canh_may as cm

H = cm.HAN_MAT_MAY


def test_vang_qua_han_moi_dung_va_chi_dung_mot_lan():
    c = cm.CanhMay()
    ban = {"S1": 7, "S2": 8}
    assert c.qua_han(ban, {"S2"}, 1000) == []                 # S1 vua mat
    assert c.qua_han(ban, {"S2"}, 1000 + H - 1) == []
    assert c.qua_han(ban, {"S2"}, 1000 + H) == [("S1", 7, H // 60)]
    assert c.qua_han(ban, {"S2"}, 1000 + H + 60) == []        # da dung roi, khong giet lap lai


def test_cam_lai_kip_thi_dem_lai_tu_dau():
    c = cm.CanhMay()
    ban = {"S1": 7}
    c.qua_han(ban, set(), 1000)
    c.qua_han(ban, {"S1"}, 1000 + H - 10)                      # cam lai / bam cho phep USB debugging
    assert c.qua_han(ban, set(), 1000 + H + 5) == []           # mat lai: tinh lai tu luc nay
    assert c.qua_han(ban, set(), 1000 + 2 * H) == []
    assert c.qua_han(ban, set(), 1000 + 2 * H + 5) == [("S1", 7, H // 60)]


def test_job_moi_tren_may_cu_duoc_canh_lai_tu_dau():
    c = cm.CanhMay()
    c.qua_han({"S1": 7}, set(), 1000)
    assert c.qua_han({"S1": 7}, set(), 1000 + H)               # luot 7 bi dung
    c.qua_han({}, set(), 1000 + H + 1)                         # luot 7 tra may
    assert c.qua_han({"S1": 9}, set(), 1000 + H + 2) == []     # luot 9 tren S1: chua qua han
    assert c.qua_han({"S1": 9}, set(), 1000 + 2 * H + 2) == [("S1", 9, H // 60)]


def test_serial_rong_luot_dang_gui_lai_ket_qua_khong_canh():
    assert cm.CanhMay().qua_han({"": 7}, set(), 1000 + 10 * H) == []


def test_kiem_goi_dung_dung_luot_cua_job(monkeypatch):
    goi = []
    monkeypatch.setattr(cm.bot_tien_trinh, "dung", lambda serial, ly_do, chu: goi.append((serial, chu, ly_do)))
    bot = SimpleNamespace(ban={"S1": 7})
    monkeypatch.setattr(cm.time, "time", lambda: 1000)
    asyncio.run(cm.kiem(bot, set()))
    monkeypatch.setattr(cm.time, "time", lambda: 1000 + H)
    asyncio.run(cm.kiem(bot, set()))
    assert len(goi) == 1 and goi[0][:2] == ("S1", 7) and "mất kết nối adb" in goi[0][2]
