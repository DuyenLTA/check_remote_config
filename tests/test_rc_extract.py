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


def test_boc_key_tu_precondition_khi_test_data_trong():
    """Bo TC chung ghi key bat buoc o Precondition. Dau cham cuoi cau bi bo."""
    d = extract(case("", precondition="1. enable_feature_aialbum = false."), WL)
    assert d.overrides == {"enable_feature_aialbum": "false"}
    assert d.from_precondition == ("enable_feature_aialbum",)
    assert d.runnable


def test_gop_precondition_va_test_data_test_data_thang():
    d = extract(case(
        "enable_feature_aialbum = true\n sort_features_moments = x",
        precondition="1. enable_feature_aialbum=false\n 2. enable_feature_aivoice=true\n 3. App first open",
    ), WL)
    assert d.overrides == {"enable_feature_aialbum": "true", "enable_feature_aivoice": "true",
                           "sort_features_moments": "x"}
    assert d.from_precondition == ("enable_feature_aivoice",)


def test_dong_precondition_co_mui_ten_bi_bo():
    # `-> load fail` la mo ta trang thai, khong phai gia tri de dat
    d = extract(case("", precondition="1. enable_feature_aialbum=true ->  load fail\n"
                                      " 2. enable_feature_aivoice=true"), WL)
    assert d.overrides == {"enable_feature_aivoice": "true"}


def test_precondition_khong_co_key_va_test_data_trong():
    d = extract(case("", precondition="1. App first open\n 2. Internet on dinh"), WL)
    assert not d.runnable
    assert "Precondition khong co key" in d.needs_human


@pytest.mark.parametrize("data", [
    "105-spl-n-native-high: fail\n 105-spl-n-native: loaded",
    "101-spl-a-banner-high: FAIL",
])
def test_ep_trang_thai_ad_thi_can_nguoi(data):
    d = extract(case(data, precondition="1. enable_feature_aialbum=true"), WL)
    assert not d.runnable
    assert "ep trang thai load ad" in d.needs_human


def test_summary_co_du_thong_tin_cho_report():
    d = ex("enable_feature_aialbum = false, click_area = cta_button")
    s = d.summary
    assert s["overrides"] == {"enable_feature_aialbum": "false"}
    assert s["ignored"] == ["click_area"]
    assert s["from_precondition"] == []
    assert s["runnable"] is True
    assert s["needs_human"] == ""


def test_moi_key_mot_dong_thi_tach_dung_tung_cap():
    # Dang sheet dung chung: xuong dong kem dau cach, khong co dau phay
    wl = {"splash_banner_change", "layout_native_ads_splash", "show_105_spl_n_native"}
    c = Case(n="5", feature="", description="", sub_scenario="", precondition="",
             test_data="splash_banner_change=true\n layout_native_ads_splash=layout1\n"
                       "show_105_spl_n_native = false",
             actions=(), expects=())
    d = extract(c, wl)
    assert d.overrides == {"splash_banner_change": "true",
                           "layout_native_ads_splash": "layout1",
                           "show_105_spl_n_native": "false"}


def test_dong_mo_ta_sau_gia_tri_khong_dinh_vao_gia_tri():
    wl = {"splash_inter_change", "banners"}
    c = Case(n="11", feature="", description="", sub_scenario="", precondition="",
             test_data="splash_inter_change=true\n New user", actions=(), expects=())
    assert extract(c, wl).overrides == {"splash_inter_change": "true"}
    c2 = Case(n="12", feature="", description="", sub_scenario="", precondition="",
              test_data='banners = [\n {"id": 1}\n]', actions=(), expects=())
    assert extract(c2, wl).overrides == {"banners": '[\n {"id": 1}\n]'}


def test_ngoac_dong_thua_cua_cau_bao_quanh_bi_bo():
    d = extract(case("", precondition="1. Old user (da xong, enable_feature_aialbum=true)"), WL)
    assert d.overrides == {"enable_feature_aialbum": "true"}
    # ngoac can bang thi giu (chu thich cuoi van bo nhu cu)
    assert ex('sort_features_moments = "a(b)"').overrides == {"sort_features_moments": "a(b)"}


@pytest.mark.parametrize("val, want", [
    ("layout1/2/3", ["layout1", "layout2", "layout3"]),
    ("layout1/layout2", ["layout1", "layout2"]),
    ("layout1 / layout2 / layout3", ["layout1", "layout2", "layout3"]),
])
def test_gia_tri_lua_chon_nhan_ra_moi_gia_tri_mot_luot(val, want):
    d = ex(f"enable_feature_aialbum = true\n sort_features_moments = {val}")
    assert d.runnable
    assert d.overrides == {"enable_feature_aialbum": "true"}
    assert [r["sort_features_moments"] for r in d.runs] == want
    assert all(r["enable_feature_aialbum"] == "true" for r in d.runs)


def test_hai_key_lua_chon_thi_nhan_to_hop():
    d = ex("sort_features_moments = layout1/2/3\n AppSettings = layout1/layout2")
    assert len(d.runs) == 6
    assert {"sort_features_moments": "layout3", "AppSettings": "layout2"} in d.runs


def test_qua_nhieu_to_hop_thi_can_nguoi():
    d = ex("sort_features_moments = a/b/c/d/e\n AppSettings = a/b/c/d")
    assert not d.runnable
    assert "to hop" in d.needs_human


def test_case_thuong_chay_mot_luot():
    assert ex("enable_feature_aialbum = false").runs == ({"enable_feature_aialbum": "false"},)


def test_url_khong_bi_coi_la_lua_chon():
    d = ex('sort_features_moments = "https://static.apero.vn/a/b.webp"')
    assert d.overrides == {"sort_features_moments": "https://static.apero.vn/a/b.webp"}


def test_id_admob_khong_bi_coi_la_lua_chon():
    d = ex("sort_features_moments = ca-app-pub-3940256099942544/1033173712")
    assert d.runs == ({"sort_features_moments": "ca-app-pub-3940256099942544/1033173712"},)
