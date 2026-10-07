"""Luat "ad vi tri X show / KHONG show tai man Y" va che do qua LFO nhanh.

Event va dump lay tu Pixel 4, AI Video Generator 1.6.0 (2026-10-07).
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from rcr import act_resolver, assert_ad_screen as ads, fo_flow, fo_screens, ui_dump

UNITS = [{"unit": "*****129", "rc_keys": ["id_202_lfo2_n_native_high2"]},
         {"unit": "*****982", "rc_keys": ["id_301_onb1_n_native_high2"]}]


def ev(*names):
    out = []
    for n in names:
        if n.startswith("show:"):
            out.append({"name": "ad_show", "params": {"ad_unit_id": "ca-app-pub-1/54857" + n[5:]}})
        else:
            out.append({"name": n, "params": {}})
    return out


def test_202_show_o_ob2_la_fail_du_request_o_lfo2():
    e = ev("lfo1_view", "lfo2_view", "ob2_view", "show:129")
    r = ads.cham("Logcat không có log show 202 tại OB2.", e, UNITS)
    assert r["verdict"] == "FAIL" and "…129" in r["reason"]


def test_202_show_o_lfo2_khong_tinh_cho_ob1():
    """Request/show 202 o LFO2 la dung cho - truoc day bi tinh thanh FAIL oan."""
    # thu tu that: ad LFO2 log ad_show TRUOC lfo2_view, roi request/load xen giua
    e = ev("lfo1_view", "show:129", "lfo2_view", "ad_load", "ob1_view", "show:982")
    assert ads.cham("OB1 KHÔNG hiển thị 202 (không có log show 202 tại OB1).", e, UNITS)["verdict"] == "PASS"
    assert ads.cham("OB1 hiển thị native ad của unit 202 (log show 202 tại OB1).", e, UNITS)["verdict"] == "FAIL"


def test_cau_ve_man_nha_va_cau_load_de_luat_cu():
    e = ev("lfo2_view", "show:129")
    assert ads.cham("LFO2 show 202 bình thường (log show 202 tại LFO2).", e, UNITS) is None
    assert ads.cham("Không có log loadAd 301 (301 OFF) — ad ở OB1 chắc chắn là 202.", e, UNITS) is None
    assert ads.cham("OB2 không lấy 202 làm fallback khi 302 no-fill.", e, UNITS) is None


def test_khong_vao_man_thi_chua_ket_luan():
    r = ads.cham("OB4 KHÔNG hiển thị 202.", ev("lfo2_view", "ob1_view"), UNITS)
    assert r["verdict"] == "NEEDS_HUMAN"


def test_cau_di_qua_lfo_nhanh_dich_thanh_goto_va_bat_che_do_nhanh():
    a = act_resolver.resolve("Đi qua LFO2 nhanh → vào OB2.", [])
    assert isinstance(a, act_resolver.GoTo) and a.target == "OnboardingActivity#2"
    assert fo_screens.can_qua_lfo_nhanh("202 đã load nhưng chưa kịp show ở LFO2")
    assert not fo_screens.can_qua_lfo_nhanh("Vào LFO2, chờ 202 hiển thị.")


class TapAdb:
    def __init__(self):
        self.taps = []


def test_qua_lfo_nhanh_bam_hang_bien_the_va_next_tu_mot_dump(monkeypatch):
    xml = (Path(__file__).parent / "fixtures" / "uidump_lfo1_collapsed.xml").read_text()
    nodes = ui_dump.app_nodes(ui_dump.parse_dump(xml))
    taps = []

    async def tap(client, serial, x, y):
        taps.append((x, y))

    async def ngu(_s):
        return None

    monkeypatch.setattr(fo_flow.device_app, "tap", tap)
    monkeypatch.setattr(fo_flow.asyncio, "sleep", ngu)
    rule = {"steps": [{"language": "English"}, {"tap": {"resource_id": "buttonLanguageNext"}},
                      {"tap": {"resource_id": "imageButtonLanguageNext"}}]}
    did = asyncio.run(fo_flow._qua_lfo_nhanh(None, "S", nodes, rule))
    assert did
    # English (563-658), bien the bung ngay duoi cach 1 hang (191px), roi nut Next (878-1022, 139-283)
    assert taps == [(592, 610), (592, 801), (950, 211)]


def test_cau_tu_man_x_vuot_sang_man_ke():
    a = act_resolver.resolve("Từ OB1 vuốt sang OB2.", [])
    assert isinstance(a, act_resolver.Swipe) and a.direction == "left"


def test_ad_show_sat_truoc_view_thuoc_man_moi():
    e = ev("lfo1_view", "track_ad_request", "show:129", "lfo2_view", "ad_load")
    assert ads.ad_man_nha_da_show(e, UNITS, "lfo2") == ["…129"]
    assert ads.ad_man_nha_da_show(ev("lfo1_view", "lfo2_view", "ob1_view", "show:129", "ad_load"),
                                  UNITS, "lfo2") == []
