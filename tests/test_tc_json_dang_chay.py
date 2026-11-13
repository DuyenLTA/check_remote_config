"""Test Data "key=JSON dang chay tren Firebase, sua: ..." (tab TC SDK daily checkin 13/11/2026)."""

import json

from rcr import rc_extract, tc_json_dang_chay
from rcr.models import Case

TD = ("show_checkin_screen=true\n"
      "checkin_gen_limit_per_day=1\n"
      "checkin_sdk_config=JSON đang chạy trên Firebase, sửa: checkin.title=\"QA - Today's Check-In\", "
      "checkin.banner=\"QA - Banner check-in\"\n"
      "checkin_sdk_design_system=JSON đang chạy trên Firebase, sửa: title_text_color=#FF0000, "
      "description_text_color=#00FF00, banner_text_color=#0000FF")
DANG_CHAY = {
    "checkin_sdk_config": json.dumps({"checkin": {"title": "Today", "banner": "B", "cta": "Check-in"},
                                      "unlock": {"title": "Unlocked"}}),
    "checkin_sdk_design_system": json.dumps({"checkin": {"title_text_color": "#111111",
                                                         "description_text_color": "#222222",
                                                         "banner_text_color": "#333333", "bg": "#FFFFFF"}}),
}


def _case(td):
    return Case(n="CHECKIN-R01-01", feature="", description="", sub_scenario="", precondition="1. Clear data.",
                test_data=td, actions=("Mở app",), expects=("Hiện",), user_state="free_user")


def test_sua_dung_field_giu_phan_con_lai():
    (_, c), = tc_json_dang_chay.thay([("daily checkin", _case(TD))], DANG_CHAY)
    wl = frozenset(DANG_CHAY) | {"show_checkin_screen", "checkin_gen_limit_per_day"}
    d = rc_extract.extract(c, wl)
    assert d.runnable, d.needs_human
    cfg = json.loads(d.overrides["checkin_sdk_config"])
    assert cfg["checkin"] == {"title": "QA - Today's Check-In", "banner": "QA - Banner check-in", "cta": "Check-in"}
    assert cfg["unlock"] == {"title": "Unlocked"}
    ds = json.loads(d.overrides["checkin_sdk_design_system"])["checkin"]
    assert ds == {"title_text_color": "#FF0000", "description_text_color": "#00FF00",
                  "banner_text_color": "#0000FF", "bg": "#FFFFFF"}
    assert d.overrides["show_checkin_screen"] == "true"


def test_field_khong_co_hoac_trung_thi_khong_doan():
    assert tc_json_dang_chay.ap_dung('{"a":{"x":1}}', [("a.y", "2", False)])[0] is None
    assert tc_json_dang_chay.ap_dung('{"a":{"c":1},"b":{"c":2}}', [("c", "3", False)])[0] is None
    # Key chua co gia tri dang chay -> giu dong goc, rc_extract dung case kem ly do
    (_, c), = tc_json_dang_chay.thay([("t", _case(TD))], {})
    assert not rc_extract.extract(c, frozenset(DANG_CHAY) | {"show_checkin_screen"}).runnable


def test_key_chua_khai_tren_server_dung_field_tc_ghi():
    wl = frozenset({"checkin_sdk_config", "checkin_sdk_design_system", "show_checkin_screen", "checkin_gen_limit_per_day"})
    (_, c), = tc_json_dang_chay.thay([("t", _case(TD))], {}, wl)
    d = rc_extract.extract(c, wl)
    assert d.runnable, d.needs_human
    assert json.loads(d.overrides["checkin_sdk_config"]) == {
        "checkin": {"title": "QA - Today's Check-In", "banner": "QA - Banner check-in"}}
    assert json.loads(d.overrides["checkin_sdk_design_system"]) == {
        "title_text_color": "#FF0000", "description_text_color": "#00FF00", "banner_text_color": "#0000FF"}
