"""Test boc key/value tu cot Test Data.

So do lay tu file TC that (`TC_IIP032_Moment_Explore_v7.5.0.xlsx`, 59 case):
12 case chay duoc, 3 runtime toggle, 1 case sua field JSON.

Diem phai gac:
  - whitelist loai param analytics (source, category, style, click_area,
    feature_name, template_id) - khong can tester khai gi
  - key khong co underscore (`AppSettings`) van boc duoc: whitelist moi la bo loc
  - runtime toggle (mui) -> NEEDS_HUMAN, KHONG parse thanh gia tri cuoi
  - `restore.enable = false` -> NEEDS_HUMAN, khong doan key goc
  - gia tri con la cho trong `<...>` -> NEEDS_HUMAN, khong ghi chuoi mo ta vao config
  - `[]` va chuoi rong `""` phai duoc GIU, khong bi coi la "khong co gia tri"
  - dau phay TRONG nhay khong tach cap
"""

from __future__ import annotations

import pytest

from rcr.models import Case
from rcr.rc_extract import extract

WL = frozenset({
    "enable_feature_aialbum", "enable_feature_aivoice", "enable_feature_explore",
    "aialbum_moments_title_tap_enabled", "moment_spotlight_banners",
    "sort_features_moments", "show_explore_231_paywall", "AppSettings",
    "banner_fail_time", "template_id",
})


def case(test_data: str, precondition: str = "") -> Case:
    return Case(n="1", feature="", description="", sub_scenario="",
                precondition=precondition, test_data=test_data)


def ex(test_data: str, wl=WL):
    return extract(case(test_data), wl)


# ---- bat binh thuong ------------------------------------------------------


def test_bool_don():
    d = ex("enable_feature_aialbum = false")
    assert d.runnable
    assert d.overrides == {"enable_feature_aialbum": "false"}


def test_chuan_hoa_hoa_thuong_cua_bool():
    assert ex("enable_feature_aialbum = FALSE").overrides == {"enable_feature_aialbum": "false"}
    assert ex("enable_feature_aialbum: True").overrides == {"enable_feature_aialbum": "true"}


def test_dau_hai_cham_cung_duoc():
    assert ex("enable_feature_aialbum: false").overrides == {"enable_feature_aialbum": "false"}


def test_so():
    assert ex("banner_fail_time = 7").overrides == {"banner_fail_time": "7"}


def test_chuoi_co_nhay_thi_bo_nhay():
    d = ex('sort_features_moments = "ai_video,ai_album,ai_voice"')
    assert d.overrides == {"sort_features_moments": "ai_video,ai_album,ai_voice"}


def test_dau_phay_trong_nhay_khong_tach_cap():
    """Case #16 that: gia tri co dau phay ben trong nhay."""
    assert len(ex('sort_features_moments = "ai_video,ai_album"').overrides) == 1


def test_json_giu_nguyen_van():
    """Case #12 that: moment_spotlight_banners = []"""
    assert ex("moment_spotlight_banners = []").overrides == {"moment_spotlight_banners": "[]"}
    assert ex('AppSettings = {"a":1}').overrides == {"AppSettings": '{"a":1}'}


def test_chuoi_rong_duoc_giu_khong_bi_bo_qua():
    """Case #15 that: sort_features_moments = "" - chuoi rong LA gia tri."""
    d = ex('sort_features_moments = ""')
    assert d.runnable
    assert d.overrides == {"sort_features_moments": ""}


def test_combo_nhieu_key_mot_dong():
    """Case #17 that."""
    d = ex("enable_feature_aialbum = false, enable_feature_aivoice = false")
    assert d.overrides == {"enable_feature_aialbum": "false", "enable_feature_aivoice": "false"}


def test_bo_chu_thich_trong_ngoac_don_o_cuoi():
    assert ex("show_explore_231_paywall = true (default)").overrides == {
        "show_explore_231_paywall": "true"}


def test_key_khong_co_underscore_van_boc_duoc():
    """Config that co key `AppSettings` - doi underscore la bo sot key hop le."""
    assert ex('AppSettings = {"x":1}').overrides == {"AppSettings": '{"x":1}'}


# ---- whitelist loc param analytics ---------------------------------------


@pytest.mark.parametrize("data,key", [
    ("source = navigation", "source"),
    ('category = "Anime"', "category"),
    ('style = "90s Vintage"', "style"),
    ("click_area = cta_button", "click_area"),
    ('feature_name = "AI Video"', "feature_name"),
])
def test_param_analytics_bi_loai(data, key):
    d = ex(data)
    assert not d.runnable
    assert d.overrides == {}
    assert key in d.ignored
    assert "khong co key nao thuoc remote config" in d.needs_human


def test_loc_giu_key_rc_bo_key_analytics_trong_cung_dong():
    d = ex("enable_feature_aialbum = false, click_area = cta_button")
    assert d.overrides == {"enable_feature_aialbum": "false"}
    assert d.ignored == ("click_area",)
    assert d.runnable


# ---- ba dang phai danh NEEDS_HUMAN ---------------------------------------


@pytest.mark.parametrize("arrow", ["→", "->", "=>"])
def test_runtime_toggle_bi_chan(arrow):
    """Case #7/#9/#29 that. KHONG duoc parse thanh gia tri cuoi cua chuoi."""
    d = ex(f"enable_feature_aialbum: true {arrow} false {arrow} true (doi khi app dang chay)")
    assert not d.runnable
    assert d.overrides == {}
    assert "runtime toggle" in d.needs_human


def test_sua_field_trong_json_bi_chan():
    """Case #14 that: `restore.enable = false` - khong neu key goc."""
    d = ex("restore.enable = false")
    assert not d.runnable
    assert "JSON" in d.needs_human


def test_gia_tri_con_la_cho_trong_bi_chan():
    """Case #49/#54 that. Patch vao la ghi nguyen chuoi mo ta vao config."""
    d = ex("template_id = <id template dang test>")
    assert not d.runnable
    assert "cho trong" in d.needs_human
    assert "template_id" in d.needs_human


def test_test_data_rong():
    for raw in ("", "   ", "N/A", "n/a", "-"):
        d = extract(case(raw), WL)
        assert not d.runnable
        assert "trong" in d.needs_human


def test_khong_boc_duoc_cap_nao():
    d = ex("session_id (request) != session_id (response)")
    assert not d.runnable
    assert "khong boc duoc" in d.needs_human


def test_khong_tu_boc_key_tu_precondition():
    """Chi doc Test Data. Precondition la van xuoi -> de boc sai."""
    c = Case(n="1", feature="", description="", sub_scenario="",
             precondition="1. enable_feature_aialbum = false.", test_data="")
    d = extract(c, WL)
    assert d.overrides == {}
    assert not d.runnable


def test_summary_co_du_thong_tin_cho_report():
    d = ex("enable_feature_aialbum = false, click_area = cta_button")
    s = d.summary
    assert s["overrides"] == {"enable_feature_aialbum": "false"}
    assert s["ignored"] == ["click_area"]
    assert s["runnable"] is True
    assert s["needs_human"] == ""
