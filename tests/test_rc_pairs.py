"""Boc cap key=value tu van ban TC that (cau lay nguyen tu cac tab TC SDK 3.x)."""

from __future__ import annotations

from rcr.rc_pairs import pairs


def test_cham_phay_tach_cap_va_bo_dau_cham_cuoi():
    got = pairs("1. show_102_spl_n_inter_high1 = true; show_102_spl_n_inter_high = false.")
    assert got == {"show_102_spl_n_inter_high1": "true", "show_102_spl_n_inter_high": "false"}


def test_sau_cham_phay_la_mo_ta_thi_bo():
    assert pairs("1. enable_onb2_screen = true; luồng FO new user đi đến Onboarding 2.") == {
        "enable_onb2_screen": "true"}


def test_chu_thich_default_sau_gia_tri_co_nhay():
    got = pairs('1. show_rating_placement = "result, exit_click, app_shortcut, home" (default).\n'
                " 2. show_rating_button_x = 2 (default).")
    assert got == {"show_rating_placement": "result, exit_click, app_shortcut, home",
                   "show_rating_button_x": "2"}


def test_chu_thich_hoac_sau_gia_tri():
    assert pairs("1. splash_ui_config = false (hoặc chuỗi rỗng).") == {"splash_ui_config": "false"}


def test_json_nhieu_dong_dung_o_ngoac_dong_khong_nuot_dong_sau():
    text = ('1. splash_ui_config =\n {\n "type": "image",\n "title": "Fravix - AI Generator"\n }\n'
            "2. New user: chưa có event complete_lfo (hoặc pass_lfo_criteria = false).")
    got = pairs(text)
    assert got["splash_ui_config"] == '{\n "type": "image",\n "title": "Fravix - AI Generator"\n }'
    assert got["pass_lfo_criteria"] == "false"


def test_json_khong_chuan_co_dau_phay_ben_trong_giu_nguyen():
    text = "1. vsl_widget_design_system = {addWidgetDialog:{dialogBgColor:'#FF0000', title:'x'}}\n 2. a = 1"
    got = pairs(text)
    assert got["vsl_widget_design_system"] == "{addWidgetDialog:{dialogBgColor:'#FF0000', title:'x'}}"
    assert "dialogBgColor" not in got and got["a"] == "1"


def test_mang_rong_roi_dong_mo_ta():
    assert pairs("1. list_language = []\n2. RC fetch thành công")["list_language"] == "[]"


def test_cat_chu_thich_co_ngoac_mo_ma_khong_dong():
    """`ob3_show_button_skip = true (key tu SDK cu` - ngoac bi cat giua chung."""
    from rcr.rc_pairs import clean

    assert clean("true (key từ SDK cũ") == "true"
    assert clean("5 (default") == "5"
    assert clean("true (mặc định)") == "true"
