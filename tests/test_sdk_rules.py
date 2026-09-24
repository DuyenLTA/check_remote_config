"""Soat TC theo luat SDK. Thuan du lieu, khong can device."""

from __future__ import annotations

from rcr import sdk_rules
from rcr.models import Case, RcCaseData

BASE = {"show_105_spl_n_native": "false", "show_105_spl_n_native_high": "true",
        "layout_native_ads_splash": "layout1"}


def case(expects=("Native ad hiển thị đúng Design layout2",)):
    return Case(n="6", feature="", description="", sub_scenario="", precondition="",
                test_data="", expects=tuple(expects))


def test_chi_bat_high_ma_key_thuong_mac_dinh_tat_thi_canh_bao():
    d = RcCaseData(overrides={"show_105_spl_n_native_high": "true", "layout_native_ads_splash": "layout2"})
    w = sdk_rules.lint(case(), d, BASE)
    assert len(w) == 1
    assert "show_105_spl_n_native=false (mac dinh cua app)" in w[0]


def test_bat_ca_hai_thi_khong_canh_bao():
    d = RcCaseData(overrides={"show_105_spl_n_native_high": "true", "show_105_spl_n_native": "true"})
    assert sdk_rules.lint(case(), d, BASE) == []


def test_case_co_y_test_tat_thi_khong_canh_bao():
    d = RcCaseData(overrides={"show_105_spl_n_native_high": "true", "show_105_spl_n_native": "false"})
    assert sdk_rules.lint(case(["Không load bất kỳ native nào", "Không crash"]), d, BASE) == []


def test_high1_cung_ap_luat():
    base = {"show_102_spl_n_inter": "false", "show_102_spl_n_inter_high1": "false"}
    d = RcCaseData(overrides={"show_102_spl_n_inter_high1": "true"})
    assert "show_102_spl_n_inter=false" in sdk_rules.lint(case(["Inter hiển thị"]), d, base)[0]


def test_luat_co_ghi_nguon_va_do_that():
    r = {x["id"]: x for x in sdk_rules.rules()}["key-thuong-la-cong-tac-tong"]
    assert r["nguon"] and r["do_that"]


def test_vi_tri_202_bat_tat_tung_tier_khong_canh_bao():
    # Do that: 202 high=T thuong=F van request high -> TC "chi preload 202-high" la dung
    base = {"show_202_lfo2_n_native": "true", "show_202_lfo2_n_native_high": "true"}
    d = RcCaseData(overrides={"show_202_lfo2_n_native_high": "true", "show_202_lfo2_n_native": "false"})
    assert sdk_rules.lint(case(["Chỉ preload 202-high", "202-high show nếu loaded"]), d, base) == []


def test_key_splash_timeout_sai_thi_canh_bao():
    d = RcCaseData(overrides={"splash_timeout": "9"})
    w = sdk_rules.lint(case(["Bỏ qua inter sau 9s"]), d, {})
    assert len(w) == 1 and "splash_ui_config.timeout" in w[0]


def test_moi_luat_deu_co_nguon():
    assert all(r.get("nguon") for r in sdk_rules.rules())
