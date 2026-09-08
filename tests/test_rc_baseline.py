"""Test doc baseline. Khong can device.

Diem phai gac:
  - nhan dung file activate cua namespace `firebase`, bo namespace khac
  - phan loai mirror bang GIAO TEN KEY, khong theo ten file
  - file vsl_* co 0 key giao -> non_mirror_files, khong bao gio ghi vao
  - app khong debuggable + may khong root -> loi RO, kem huong dan
  - ten file frc_* (co dau ':') phai duoc boc nhay khi qua sh
"""

from __future__ import annotations

import asyncio

import pytest
from conftest import ACTIVATE, APP_ID, PKG, SERIAL, FakeAdb

from rcr import rc_baseline
from rcr.models import RcError


def read(adb, package=PKG, serial=SERIAL):
    return asyncio.run(rc_baseline.read(adb, serial, package))


def test_doc_duoc_app_id_va_key(adb):
    bl = read(adb)
    assert bl.app_id == APP_ID
    assert bl.activate_name == ACTIVATE
    assert bl.settings_name == f"frc_{APP_ID}_firebase_settings.xml"
    assert bl.template_version == "232"
    assert bl.fetch_time_ms == 1781492084614
    assert bl.write_mode == "run-as"


def test_moi_value_la_string(adb):
    """RC luu moi thu duoi dang string - tang sau khong phai doan kieu."""
    bl = read(adb)
    assert all(isinstance(v, str) for v in bl.configs.values())
    assert bl.configs["ad_load_timeout"] == "20"
    assert bl.configs["ad_positions_high_rank"] == '["LFO1","LFO2"]'


def test_bo_qua_namespace_khac_va_file_defaults(adb):
    """files/ co ca _fireperf_activate.json va _firebase_defaults.json."""
    bl = read(adb)
    assert "firebase_activate" in bl.activate_name
    assert "fireperf" not in bl.activate_name
    assert "defaults" not in bl.activate_name


def test_phan_loai_mirror_bang_giao_ten_key(adb):
    """Day la luat cot loi: ten file KHONG dang tin, chi giao ten key moi dang."""
    bl = read(adb)
    assert set(bl.mirrors) == {
        "vsl_template4_remote_first_open.xml",
        "vsl_billing_remote_config.xml",
    }
    # vsl_template4_prefs.xml (ARG_KEY_*) va vsl_widget_local_prefs.xml
    # (widget_fetch_successful) co 0 key giao -> state noi bo app.
    assert bl.non_mirror_files == (
        "vsl_template4_prefs.xml",
        "vsl_widget_local_prefs.xml",
    )


def test_mirror_chi_giu_key_giao_voi_rc(adb):
    """layout_onb2_screen co trong prefs nhung khong co trong RC -> phai bi loai."""
    bl = read(adb)
    fo = bl.mirrors["vsl_template4_remote_first_open.xml"]
    assert set(fo) == {"enable_onb3_screen", "splash_banner_change", "banner_fail_time"}
    assert "layout_onb2_screen" not in fo


def test_mirror_giu_dung_kieu_xml(adb):
    """RC luu string, mirror co kieu. Ghi lai phai giu kieu -> phai doc duoc kieu."""
    bl = read(adb)
    fo = bl.mirrors["vsl_template4_remote_first_open.xml"]
    assert fo["enable_onb3_screen"].kind == "boolean"
    assert fo["banner_fail_time"].kind == "int"
    billing = bl.mirrors["vsl_billing_remote_config.xml"]
    assert billing["paywall_config"].kind == "string"
    assert billing["paywall_config"].value == '{"a":1}'  # da unescape &quot;


def test_mirrored_keys_dung_so(adb):
    bl = read(adb)
    assert bl.mirrored_keys == {
        "enable_onb3_screen",
        "splash_banner_change",
        "banner_fail_time",
        "paywall_config",
    }


def test_ten_file_frc_duoc_boc_nhay_khi_qua_sh(adb):
    """Ten file chua dau ':' -> khong boc nhay la sh cat sai duong dan."""
    read(adb)
    cat_cmds = adb.cmds_with(" cat ")
    assert cat_cmds, "khong co lenh cat nao"
    for c in cat_cmds:
        path = c.rsplit(" cat ", 1)[1].strip()
        assert path.startswith("'") and path.endswith("'"), c


def test_app_khong_debuggable_va_may_khong_root_thi_loi_ro(adb):
    adb.debuggable = False
    adb.rooted = False
    with pytest.raises(RcError) as ei:
        read(adb)
    msg = str(ei.value)
    assert "not debuggable" in msg
    assert "may khong root" in msg
    assert "application-debuggable" in msg  # co kem cach tu kiem APK


def test_may_root_thi_dung_duong_su(adb):
    """App release + may root -> van patch duoc, khong phu thuoc dev."""
    adb.debuggable = False
    adb.rooted = True
    bl = read(adb)
    assert bl.write_mode == "su"
    assert bl.app_id == APP_ID
    assert any("su -c" in c for c in adb.calls)


def test_khong_co_file_frc_thi_loi_huong_dan_mo_app():
    adb = FakeAdb(files={})
    adb.files = {}  # cat luon that bai
    with pytest.raises(RcError) as ei:
        read(adb)
    assert "Khong doc duoc" in str(ei.value) or "khong co file remote config" in str(ei.value)


def test_thieu_moc_throttle_thi_bao_loi(adb):
    """Thieu last_fetch_time_in_millis -> khong chan duoc fetch -> phai fail som."""
    adb.files[f"shared_prefs/frc_{APP_ID}_firebase_settings.xml"] = (
        "<?xml version='1.0'?>\n<map>\n<int name=\"num_failed_fetches\" value=\"0\" />\n</map>\n"
    )
    with pytest.raises(RcError) as ei:
        read(adb)
    assert "last_fetch_time_in_millis" in str(ei.value)


def test_activate_khong_dung_schema_thi_bao_loi(adb):
    adb.files[f"files/{ACTIVATE}"] = '{"khong_phai_configs_key": {}}'
    with pytest.raises(RcError) as ei:
        read(adb)
    assert "configs_key" in str(ei.value)


def test_activate_khong_phai_json_thi_bao_loi(adb):
    adb.files[f"files/{ACTIVATE}"] = "khong phai json"
    with pytest.raises(RcError) as ei:
        read(adb)
    assert "JSON" in str(ei.value)


def test_summary_khong_keo_theo_noi_dung_file(adb):
    """Summary tra ve UI -> khong duoc chua nguyen van file (co credential)."""
    s = read(adb).summary
    assert s["keys"] == 6
    assert s["mirrored_keys"] == 4
    assert s["write_mode"] == "run-as"
    assert len(s["non_mirror_files"]) == 2
    blob = repr(s)
    assert "configs_key" not in blob
    assert "last_fetch_etag" not in blob


def test_package_ky_tu_la_bi_chan_truoc_khi_goi_adb(adb):
    for bad in ("x; am start -n com.x/.Main", "com.x && id", "com.x|sh", "com.x`id`"):
        with pytest.raises(Exception):
            read(adb, package=bad)
