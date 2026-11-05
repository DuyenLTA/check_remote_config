"""Quy unit trong log ve vi tri khi RC khai `id_*` ma app khong dung (ID cung trong app = ID sheet)."""

from __future__ import annotations

import asyncio

from rcr import ad_units, case_evidence
from rcr.ad_positions import _khop_vi_tri
from rcr.models import RcBaseline


def test_rc_id_cu_khong_de_mat_id_sheet(monkeypatch):
    pkg = "com.example.app"
    monkeypatch.setattr(ad_units, "_SHEET", {pkg: {"id_201_lfo1_n_native_high": "ca-app-pub-1/623879039"}})
    monkeypatch.setattr(ad_units, "bang", lambda path=None: {})

    async def pid(*_a):
        return "123"

    async def doc(*_a):
        return ""

    monkeypatch.setattr(case_evidence.sdk_probe, "pid_of", pid)
    monkeypatch.setattr(case_evidence.ad_log, "read", doc)
    monkeypatch.setattr(case_evidence.ad_log, "parse", lambda _t: {"banner_states": []})
    monkeypatch.setattr(case_evidence.ad_log, "summary", lambda _p: {
        "a": {"unit": "*****039", "type": "native", "requested": 1, "loaded": 1, "shown": 1}})
    base = RcBaseline(package=pkg, serial="S", app_id="", activate_name="", settings_name="", activate_raw="", settings_raw="", configs={"id_201_lfo1_n_native_high": "ca-app-pub-1/6664063653"})
    ads = asyncio.run(case_evidence._read_ads(None, base))
    unit = ads["units"]["a"]
    assert _khop_vi_tri(unit, "201_lfo1_n_native_high")
    assert ads["positions"].count("201_lfo1_n_native_high") == 1


def test_key_splash_inter_quy_ve_102(monkeypatch):
    pkg = "com.example.app"
    monkeypatch.setattr(ad_units, "_SHEET", {})
    monkeypatch.setattr(ad_units, "bang", lambda path=None: {})

    async def pid(*_a):
        return "123"

    async def doc(*_a):
        return ""

    monkeypatch.setattr(case_evidence.sdk_probe, "pid_of", pid)
    monkeypatch.setattr(case_evidence.ad_log, "read", doc)
    monkeypatch.setattr(case_evidence.ad_log, "parse", lambda _t: {"banner_states": []})
    monkeypatch.setattr(case_evidence.ad_log, "summary", lambda _p: {
        "a": {"unit": "*****794", "type": "interstitial", "requested": 1, "loaded": 0, "shown": 0}})
    base = RcBaseline(package=pkg, serial="S", app_id="", activate_name="", settings_name="", activate_raw="",
                      settings_raw="", configs={"splash_inter_high_n_id": "ca-app-pub-1/4712346794"})
    unit = asyncio.run(case_evidence._read_ads(None, base))["units"]["a"]
    assert _khop_vi_tri(unit, "102_spl_n_inter_high")
