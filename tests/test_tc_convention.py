"""Test quy uoc Test Data cua bo TC 3.5.0 (sheet "Automation Convention").

Diem phai gac:
  - `key=<absent>` xoa key ca o activate.json lan file mirror, verify thay key vang
  - `v1 | v2` -> moi gia tri mot luot
  - runtime `a → b → c` -> chuoi luot CO THU TU, khong con bi chan
  - runtime ghi "(doi khi app dang chay)" van chan: tool chi tat-roi-mo-lai duoc
  - luot i chi lai buoc va cham dong Expected "Lan i" cua no
  - report hien DU moi luot, khong chi luot dau
"""

from __future__ import annotations

import asyncio
import json

from conftest import ACTIVATE, PKG, SERIAL
from test_rc_extract import case

from rcr import rc_baseline, rc_patch, rc_variants, rc_verify, report_data, runtime_steps
from rcr.mirror_xml import parse_nodes
from rcr.rc_extract import extract

ABSENT = rc_variants.ABSENT
WL = frozenset({"swipe_onb2", "enable_onb2_screen", "auto_swipe_onb3", "enable_onb3_screen"})
ACT = f"files/{ACTIVATE}"
MIR = "shared_prefs/vsl_template4_remote_first_open.xml"


def base(adb):
    return asyncio.run(rc_baseline.read(adb, SERIAL, PKG))


# ---- boc Test Data -----------------------------------------------------------

def test_absent_khong_bi_coi_la_cho_trong():
    d = extract(case("enable_onb2_screen=true\nswipe_onb2=<absent>"), WL)
    assert d.runnable and d.overrides == {"enable_onb2_screen": "true", "swipe_onb2": ABSENT}


def test_pipe_moi_gia_tri_mot_luot():
    d = extract(case("enable_onb3_screen=true\nauto_swipe_onb3=null | <absent>"), WL)
    assert [r["auto_swipe_onb3"] for r in d.runs] == ["null", ABSENT]
    assert all(r["enable_onb3_screen"] == "true" for r in d.runs) and not d.runtime


def test_runtime_thanh_chuoi_luot_co_thu_tu():
    d = extract(case("enable_onb2_screen=true\nswipe_onb2=true → false → true"), WL)
    assert d.runnable and d.runtime
    assert [r["swipe_onb2"] for r in d.runs] == ["true", "false", "true"]


def test_runtime_doi_khi_app_dang_chay_van_chan():
    d = extract(case("swipe_onb2: true → false (doi khi app dang chay)"), WL)
    assert not d.runnable and "runtime toggle" in d.needs_human


def test_runtime_hai_key_khac_so_buoc_thi_chan():
    d = extract(case("swipe_onb2=true → false\nauto_swipe_onb3=true → false → true"), WL)
    assert not d.runnable and "so buoc" in d.needs_human


# ---- patch / verify <absent> -------------------------------------------------

def test_absent_xoa_key_o_ca_activate_va_mirror(adb):
    w = dict(rc_patch.build_writes(base(adb), {"enable_onb3_screen": ABSENT}, 1))
    assert "enable_onb3_screen" not in json.loads(w[ACT])["configs_key"]
    assert "enable_onb3_screen" not in parse_nodes(w[MIR])
    assert "splash_banner_change" in parse_nodes(w[MIR])      # node khac giu nguyen


def test_absent_cho_key_app_khong_co_thi_khong_loi(adb):
    w = dict(rc_patch.build_writes(base(adb), {"key_khong_co": ABSENT}, 1))
    assert "key_khong_co" not in json.loads(w[ACT])["configs_key"]


def test_verify_absent_ok_khi_key_vang_va_lech_khi_sdk_ghi_lai(adb):
    bl = base(adb)
    asyncio.run(rc_patch.patch(adb, bl, {"enable_onb3_screen": ABSENT}, now_ms=1))
    assert asyncio.run(rc_verify.verify(adb, bl, {"enable_onb3_screen": ABSENT})).ok
    # SDK ghi lai node vao mirror -> app doc gia tri do, khong phai "khong co key"
    adb.files[MIR] = bl.mirror_raw["vsl_template4_remote_first_open.xml"]
    assert not asyncio.run(rc_verify.verify(adb, bl, {"enable_onb3_screen": ABSENT})).ok


# ---- chia buoc / Expected theo luot runtime ----------------------------------

BUOC_14 = (
    "Chạy luồng FO lần 1 đến OB3 (show_x = false).",
    "Đổi show_x = true trên Firebase, Publish; kill app, mở lại để fetch RC mới.",
    "Chạy luồng FO lần 2 đến OB3.",
    "Đổi show_x = false, Publish; kill app, chạy lần 3 đến OB3.",
)


def test_chia_buoc_bo_buoc_doi_config_lay_ve_sau_kill_app():
    assert runtime_steps.chia_buoc(BUOC_14, 3) == [
        ("Chạy luồng FO lần 1 đến OB3 (show_x = false).",),
        ("Chạy luồng FO lần 2 đến OB3.",),
        ("chạy lần 3 đến OB3",),
    ]


def test_luot_khong_co_buoc_rieng_thi_lap_buoc_luot_1():
    buoc = ("Vào OB2 lần 1, quan sát icon.", "Đổi swipe_onb2 = false, Publish; kill app, fetch RC.")
    assert runtime_steps.chia_buoc(buoc, 2)[1] == ("Vào OB2 lần 1, quan sát icon.",)


def test_chia_expected_theo_lan_va_giu_dong_chung():
    exp = ("Lần 1: icon hiển thị.", "Lần 2: icon KHÔNG hiển thị.", "Không crash.")
    assert runtime_steps.chia_expected(exp, 2) == [
        ("icon hiển thị.", "Không crash."), ("icon KHÔNG hiển thị.", "Không crash.")]


# ---- report hien du moi luot -------------------------------------------------

def _run(v, verdict):
    return {"overrides": {"swipe_onb2": v, "enable_onb2_screen": "true"},
            "assert": {"lines": [{"verdict": verdict, "expected": "icon", "reason": "r"}]},
            "drive": {"steps": [{"n": 1, "step": "Vào OB2", "action": {"kind": "goto"}}]}}


def test_report_hien_moi_luot_kem_nhan():
    rec = report_data.case_record("27", {}, {"verdict": "FAIL",
                                             "runs": [_run("true", "PASS"), _run("false", "FAIL")]})
    assert [l["e"] for l in rec["lines"]] == ["Lượt 1 (swipe_onb2=true): icon",
                                              "Lượt 2 (swipe_onb2=false): icon"]
    assert rec["overrides"]["swipe_onb2"] == "true → false"
    assert rec["overrides"]["enable_onb2_screen"] == "true"
    assert len(rec["steps"]) == 2


def test_report_mot_luot_khong_gan_nhan():
    rec = report_data.case_record("1", {}, {"verdict": "PASS", "runs": [_run("true", "PASS")]})
    assert rec["lines"][0]["e"] == "icon"


def test_phu_dinh_voi_log_trong_tron_khong_duoc_PASS():
    """Log khong co request ads nao: "khong load unit X" dung mot cach rong."""
    from rcr import assert_ads
    ket = assert_ads.ad_line("Logcat: KHÔNG có log loadAd cho unit 106-spl-o-native-high1",
                             "native", {"units": {}}, {})
    assert ket["verdict"] != "PASS"
    co_ads = {"units": {"x": {"unit": "x", "type": "interstitial", "requested": 1,
                              "loaded": 0, "shown": 0, "rc_keys": []}}}
    assert assert_ads.ad_line("KHÔNG có log loadAd native nào", "native", co_ads, {})["verdict"] == "PASS"


def test_tc_nhan_link_sheet_va_duong_dan_file():
    from rcr import tc_source
    link = ("https://docs.google.com/spreadsheets/d/"
            "1sNFXM7oGzx_addpimZL7RYk2rXpRs_We6YUHpdtWSqU/edit?gid=1012602089#gid=1012602089")
    assert tc_source.la_link(link)
    assert not tc_source.la_link("/home/u/Downloads/tc.xlsx")
    assert tc_source.tai_ve("/home/u/Downloads/tc.xlsx", ".") == "/home/u/Downloads/tc.xlsx"
