"""Ep fail/fill tung unit bang ID ad trong RC. Thuan ham, khong can device."""

from __future__ import annotations

from rcr import ad_state
from rcr.models import Case
from rcr.rc_extract import extract

WL = frozenset({"splash_inter_change", "splash_inter_high_n_id", "splash_inter_n_id",
                "id_102_spl_n_inter_high", "show_105_spl_n_native"})


def case(test_data, precondition=""):
    return Case(n="8", feature="", description="", sub_scenario="",
                precondition=precondition, test_data=test_data)


def test_find_chuan_hoa_trang_thai():
    assert ad_state.find("102-spl-n-inter-high: FAIL\n 102-spl-n-inter: loaded") == {
        "102-spl-n-inter-high": "fail", "102-spl-n-inter": "loaded"}
    assert ad_state.find("101-x: failed") == {"101-x": "fail"}


def test_high_fail_thuong_loaded_thanh_id_sai_va_id_test():
    d = extract(case("102-spl-n-inter-high: fail\n 102-spl-n-inter: loaded",
                     precondition="1. splash_inter_change=true"), WL)
    assert d.runnable
    assert d.overrides == {
        "splash_inter_change": "true",
        "splash_inter_high_n_id": ad_state.INVALID_ID,
        "splash_inter_n_id": ad_state.TEST_IDS["inter"],
    }


def test_khong_suy_key_tu_ten_vi_tri():
    # id_102_spl_n_inter_high co trong RC nhung SDK khong doc -> khong duoc dung
    d = extract(case("102-spl-n-inter-high: fail"), WL)
    assert "id_102_spl_n_inter_high" not in d.overrides
    assert d.overrides["splash_inter_high_n_id"] == ad_state.INVALID_ID


def test_vi_tri_chua_co_trong_bang_thi_can_nguoi():
    d = extract(case("105-spl-n-native-high: fail\n 105-spl-n-native: loaded",
                     precondition="1. show_105_spl_n_native=true"), WL)
    assert not d.runnable
    assert "105-spl-n-native-high: fail" in d.needs_human
    assert "ad_id_keys.yaml" in d.needs_human


def test_key_trong_bang_ma_app_khong_co_thi_can_nguoi():
    d = extract(case("102-spl-n-inter-high: fail"), frozenset({"splash_inter_change"}))
    assert not d.runnable


def test_ky_hieu_viet_tat_khong_doc_duoc_thi_can_nguoi():
    d = extract(case("102-n-high/high1: fail\n 102-spl-n-inter: loaded"), WL)
    assert not d.runnable
    assert "khong doc duoc" in d.needs_human
    assert "102-n-high/high1: fail" in d.needs_human


def test_ky_hieu_trong_precondition_cung_duoc_ep():
    d = extract(case("", precondition="1. splash_inter_change=true\n 2. 102-spl-n-inter-high: fail"), WL)
    assert d.overrides["splash_inter_high_n_id"] == ad_state.INVALID_ID
