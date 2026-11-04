"""Nut Next man ngon ngu: dump that AIP936 1.9.0 (11) 03/11/2026 (LFO1 truoc khi chon, LFO2 sau khi chon)."""

from __future__ import annotations

from pathlib import Path

from rcr import assert_check, assert_nut_lfo

FX = Path(__file__).parent / "fixtures"
LFO1 = (FX / "uidump_lfo1_next_tat_ban_tay.xml").read_text(encoding="utf-8")
LFO2 = (FX / "uidump_lfo2_next_bat.xml").read_text(encoding="utf-8")
DRIVE = {"steps": [{"activity": "x.language.language1.VslTemplate4Language14Activity", "dump": LFO1},
                   {"activity": "x.language.language2.VslTemplate4Language24Activity", "dump": LFO2}]}
DONG = "Button Next disable + có icon hướng dẫn cho đến khi chọn ngôn ngữ."


def test_rg01_04_nut_tat_co_ban_tay_chon_xong_thi_bat():
    r = assert_nut_lfo.cham(DONG, DRIVE)
    assert r["verdict"] == "PASS"
    assert "enabled=false" in r["reason"] and "có trên LFO1" in r["reason"] and "enabled=true" in r["reason"]


def test_nut_bat_san_ma_ky_vong_tat_la_fail():
    bat = {"steps": [{"activity": "x.Language14Activity", "dump": LFO2}]}
    assert assert_nut_lfo.cham("Button Next disable.", bat)["verdict"] == "FAIL"


def test_khong_dung_cho_nut_next_onboarding_hay_dong_focus():
    assert assert_nut_lfo.cham("Button Next enable sẵn, focus ngôn ngữ đầu tiên.", DRIVE) is None
    assert assert_nut_lfo.cham(DONG, {"steps": []}) is None


def test_check_all_khong_con_bao_khong_thay_nut_next():
    kq = assert_check.check_all([DONG], {"units": {}}, DRIVE, {})
    assert kq["lines"][0]["verdict"] == "PASS"
