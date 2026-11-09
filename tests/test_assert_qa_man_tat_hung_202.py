"""Luat QA 05/11/2026: hung 202 sang man OB dau, man tat van giu logic load ad.

Event / unit lay tu Pixel 6, AIP893 AI Photo Video Slideshow 2.5.0, TC SDK 3.5.4.
"""

from __future__ import annotations

from rcr import assert_qa_man_tat_hung_202 as qa

UNITS = [{"unit": "*****332", "rc_keys": ["id_202_lfo2_n_native_high"], "requested": True},
         {"unit": "*****989", "rc_keys": ["id_301_onb1_n_native_high"], "requested": True},
         {"unit": "*****117", "rc_keys": ["id_301_onb1_o_native_high"], "requested": True},
         {"unit": "*****483", "rc_keys": ["id_301_onb1_o_inter_high"], "requested": False}]


def ev(*names):
    out = []
    for n in names:
        if n.startswith("show:"):
            out.append({"name": "ad_show", "params": {"ad_unit_id": "ca-app-pub-1/3952227" + n[5:]}})
        else:
            out.append({"name": n, "params": {}})
    return out


DONG_R01_06 = "Native 301-onb1-n-native-high hiển thị, không show 202-lfo2-n-native-high."


def test_ob1_show_202_chua_show_la_dung_thiet_ke():
    e = ev("lfo1_view", "lfo2_view", "show:332", "ob1_view", "show:332")
    r = qa.cham(DONG_R01_06, e, UNITS, {})
    assert r["verdict"] == "PASS" and "luật QA" in r["reason"]


def test_202_khong_show_o_ob1_thi_de_luat_cu():
    e = ev("lfo1_view", "lfo2_view", "show:332", "ad_load", "ob1_view")
    assert qa.cham(DONG_R01_06, e, UNITS, {}) is None


def test_ob1_khong_phai_man_ob_dau_thi_khong_ap():
    """Tat OB1: man OB dau la OB2, cau ve 301 o OB1 khong thuoc luat hung."""
    e = ev("lfo2_view", "ob2_view", "show:332")
    assert qa.cham(DONG_R01_06, e, UNITS, {}) is None


DONG_O02 = ("Không có OB Old, không có loadAd 301-onb1-o-native-high, 301-onb1-o-native, "
            "301-onb1-o-inter-high, 301-onb1-o-inter.")


def test_tat_ob_old_van_load_301_o_o_splash_la_dung():
    units = [dict(u) for u in UNITS]
    units[3]["requested"] = True
    r = qa.cham(DONG_O02, [], units, {"enable_ob1_old_screen": "false"})
    assert r["verdict"] == "PASS" and "…" not in r["reason"] and "*****117" in r["reason"]


def test_man_tat_thieu_request_tier_high_phai_doi_chieu():
    r = qa.cham(DONG_O02, [], UNITS, {"enable_ob1_old_screen": "false"})
    assert r["verdict"] == "NEEDS_HUMAN" and "301_onb1_o_inter_high" in r["reason"]


def test_man_dang_bat_thi_de_luat_cu():
    assert qa.cham(DONG_O02, [], UNITS, {"enable_ob1_old_screen": "true"}) is None


def test_question_305_khong_quy_ve_man_onb5():
    assert qa.key_man("305_onb5_n_native_high") is None
    assert qa.key_man("302_onb2_n_native") == "enable_onb2_screen"
