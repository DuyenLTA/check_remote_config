"""Test dat/tra config. Khong can device.

Diem phai gac:
  - PHAI ghi ca 2 chO: activate.json VA settings.xml (thieu 1 la app fetch de mat patch)
  - THU TU: mirror -> settings -> activate SAU CUNG
  - file trong non_mirror_files KHONG BAO GIO bi ghi (state noi bo app)
  - mirror giu dung kieu XML; key khong co trong mirror -> khong them node moi
  - file tam /data/local/tmp LUON bi xoa, ke ca khi chang 2 that bai
  - ten key/gia tri cua tester khong di vao duong dan tren may
  - restore dung moc fetch CU (de app tu lay lai config that)
"""

from __future__ import annotations

import asyncio
import json

import pytest
from conftest import ACTIVATE, APP_ID, PKG, SERIAL, FakeAdb

from rcr import rc_baseline, rc_patch
from rcr.mirror_xml import parse_nodes, read_long
from rcr.models import RcError

SETTINGS_REL = f"shared_prefs/frc_{APP_ID}_firebase_settings.xml"
ACTIVATE_REL = f"files/{ACTIVATE}"
MIRROR_FO = "shared_prefs/vsl_template4_remote_first_open.xml"
NOW = 1788519653885


def base(adb):
    return asyncio.run(rc_baseline.read(adb, SERIAL, PKG))


def do_patch(adb, overrides, now=NOW):
    return asyncio.run(rc_patch.patch(adb, base(adb), overrides, now_ms=now))


# ---- build_writes: thuan ham, gac cac luat -------------------------------


def test_ghi_ca_activate_va_settings(adb):
    """Thieu settings.xml la app fetch de mat patch - da do thuc te ca 2 chieu."""
    w = rc_patch.build_writes(base(adb), {"ad_load_timeout": "99"}, NOW)
    dests = [d for d, _ in w]
    assert ACTIVATE_REL in dests
    assert SETTINGS_REL in dests


def test_thu_tu_activate_ghi_sau_cung(adb):
    """Mirror loi giua duong thi config chinh chua doi -> trang thai con nhat quan."""
    w = rc_patch.build_writes(base(adb), {"enable_onb3_screen": "false"}, NOW)
    dests = [d for d, _ in w]
    assert dests[-1] == ACTIVATE_REL
    assert dests.index(MIRROR_FO) < dests.index(SETTINGS_REL) < dests.index(ACTIVATE_REL)


def test_dat_ca_hai_moc_thoi_gian(adb):
    w = dict(rc_patch.build_writes(base(adb), {"ad_load_timeout": "99"}, NOW))
    assert json.loads(w[ACTIVATE_REL])["fetch_time_key"] == NOW
    assert read_long(w[SETTINGS_REL], "last_fetch_time_in_millis") == NOW


def test_settings_chi_doi_moc_khong_doi_etag(adb):
    w = dict(rc_patch.build_writes(base(adb), {"ad_load_timeout": "99"}, NOW))
    assert "etag-310944273102-firebase-fetch-781665809" in w[SETTINGS_REL]
    assert read_long(w[SETTINGS_REL], "last_template_version") == 232


def test_key_bi_mirror_thi_ghi_ca_2_cho(adb):
    w = dict(rc_patch.build_writes(base(adb), {"enable_onb3_screen": "false"}, NOW))
    assert json.loads(w[ACTIVATE_REL])["configs_key"]["enable_onb3_screen"] == "false"
    assert parse_nodes(w[MIRROR_FO])["enable_onb3_screen"].value == "false"


def test_key_khong_bi_mirror_thi_khong_cham_file_mirror(adb):
    """ad_load_timeout khong co trong mirror -> khong duoc ghi mirror."""
    w = rc_patch.build_writes(base(adb), {"ad_load_timeout": "99"}, NOW)
    assert MIRROR_FO not in [d for d, _ in w]


def test_mirror_giu_nguyen_kieu_xml(adb):
    w = dict(rc_patch.build_writes(base(adb), {"banner_fail_time": "7"}, NOW))
    assert '<int name="banner_fail_time" value="7" />' in w[MIRROR_FO]
    # activate van luu string
    assert json.loads(w[ACTIVATE_REL])["configs_key"]["banner_fail_time"] == "7"


def test_mirror_string_co_escape(adb):
    payload = '{"cta":"Buy & Save"}'
    w = dict(rc_patch.build_writes(base(adb), {"paywall_config": payload}, NOW))
    mir = w["shared_prefs/vsl_billing_remote_config.xml"]
    assert parse_nodes(mir)["paywall_config"].value == payload
    assert "&amp;" in mir


def test_combo_nhieu_key_mot_luot(adb):
    """Case #17 trong file TC that: 2-3 key doi cung luc."""
    ov = {"enable_onb3_screen": "false", "splash_banner_change": "false", "ad_load_timeout": "5"}
    w = dict(rc_patch.build_writes(base(adb), ov, NOW))
    cfg = json.loads(w[ACTIVATE_REL])["configs_key"]
    assert {k: cfg[k] for k in ov} == ov
    nodes = parse_nodes(w[MIRROR_FO])
    assert nodes["enable_onb3_screen"].value == "false"
    assert nodes["splash_banner_change"].value == "false"


def test_cac_key_khac_khong_bi_doi(adb):
    bl = base(adb)
    w = dict(rc_patch.build_writes(bl, {"ad_load_timeout": "99"}, NOW))
    cfg = json.loads(w[ACTIVATE_REL])["configs_key"]
    for k, v in bl.configs.items():
        if k != "ad_load_timeout":
            assert cfg[k] == v


def test_key_la_thi_bao_loi_ro(adb):
    with pytest.raises(RcError, match="khong co trong remote config"):
        rc_patch.build_writes(base(adb), {"key_bay_dau": "true"}, NOW)


def test_sai_kieu_thi_bao_loi_chu_khong_ghi_bua(adb):
    """enable_onb3_screen la boolean o mirror - dat '3' phai fail RO."""
    with pytest.raises(RcError, match="khong dat duoc"):
        rc_patch.build_writes(base(adb), {"enable_onb3_screen": "3"}, NOW)


def test_overrides_rong_thi_bao_loi(adb):
    with pytest.raises(RcError, match="Khong co key nao"):
        do_patch(adb, {})


# ---- guard: khong ghi vao state noi bo app --------------------------------


def test_khong_bao_gio_ghi_file_state_noi_bo(adb):
    bl = base(adb)
    assert "vsl_template4_prefs.xml" in bl.non_mirror_files
    with pytest.raises(RcError, match="state noi bo"):
        rc_patch._assert_writable(bl, "shared_prefs/vsl_template4_prefs.xml")


def test_khong_ghi_file_ngoai_danh_sach(adb):
    with pytest.raises(RcError, match="khong nam trong danh sach"):
        rc_patch._assert_writable(base(adb), "shared_prefs/com.facebook.sdk.xml")


def _write_cmds(adb):
    """Chi lenh GHI. rc_baseline PHAI doc file state noi bo de phan loai no -
    cam la cam GHI, khong phai cam doc."""
    return [c for c in adb.calls if " push " in c or ">" in c]


def test_patch_khong_he_GHI_vao_file_state_noi_bo(adb):
    do_patch(adb, {"enable_onb3_screen": "false"})
    for c in _write_cmds(adb):
        assert "vsl_template4_prefs.xml" not in c, c
        assert "vsl_widget_local_prefs.xml" not in c, c


# ---- duong ghi that: file tam, thu tu lenh --------------------------------


def test_file_tam_luon_bi_xoa(adb):
    do_patch(adb, {"ad_load_timeout": "99"})
    pushes = [c for c in adb.calls if " push " in c]
    rms = [c for c in adb.calls if " rm -f /data/local/tmp/rcr_" in c]
    # ad_load_timeout khong bi mirror -> chi ghi settings + activate = 2 file
    assert len(pushes) == 2
    assert len(rms) == len(pushes), "moi file push phai co mot lenh rm"


def test_file_tam_bi_xoa_ca_khi_ghi_that_bai(adb):
    """Loi thuc su khong duoc bi che, nhung tmp van phai sach."""
    adb.fails = {"cat /data/local/tmp/rcr_": ("", "Permission denied", 1)}
    with pytest.raises(RcError):
        do_patch(adb, {"ad_load_timeout": "99"})
    assert [c for c in adb.calls if " rm -f /data/local/tmp/rcr_" in c]


def test_ten_key_va_gia_tri_khong_di_vao_duong_dan(adb):
    """Gia tri tester dua chay qua `sh` tren device -> phai nam trong file, khong o dong lenh."""
    do_patch(adb, {"ad_load_timeout": "1; rm -rf /sdcard"})
    for c in adb.calls:
        assert "rm -rf /sdcard" not in c, c


def test_duong_stdin_du_phong_khi_app_khong_doc_duoc_file_shell(adb):
    """SELinux chan app doc file cua shell -> phai tu chuyen duong, khong bao loi oan."""
    calls = {"n": 0}
    orig = adb._dispatch

    def dispatch(cmd):
        # chi duong 1 (`run-as ... sh -c cat tmp > dest`) that bai
        if "run-as" in cmd and "sh -c" in cmd and "| run-as" not in cmd:
            calls["n"] += 1
            adb.calls.append(cmd)
            return "", "Permission denied", 1
        return orig(cmd)

    adb._dispatch = dispatch
    res = do_patch(adb, {"ad_load_timeout": "99"})
    assert calls["n"] > 0, "duong 1 chua he duoc thu"
    assert any("| run-as" in c for c in adb.calls), "chua di duong stdin"
    assert res.applied == {"ad_load_timeout": "99"}


def test_may_root_thi_ghi_qua_su(adb):
    adb.debuggable = False
    adb.rooted = True
    res = do_patch(adb, {"ad_load_timeout": "99"})
    assert res.written
    assert any("su -c" in c and "cat /data/local/tmp/rcr_" in c for c in adb.calls)
    assert not any(" run-as " in c and "cat" in c for c in adb.calls)


# ---- restore -------------------------------------------------------------


def test_restore_tra_nguyen_van_va_moc_fetch_cu(adb):
    bl = base(adb)
    res = asyncio.run(rc_patch.restore(adb, bl))
    assert res.restored
    # moc CU, khong phai now: app se tu fetch lai config that o lan mo sau
    assert res.fetch_time_ms == 1781492084614
    assert f"files/{ACTIVATE}" in res.written


def test_restore_ghi_lai_moi_file_mirror(adb):
    bl = base(adb)
    res = asyncio.run(rc_patch.restore(adb, bl))
    for name in bl.mirrors:
        assert f"shared_prefs/{name}" in res.written


def test_restore_khong_GHI_vao_file_state_noi_bo(adb):
    asyncio.run(rc_patch.restore(adb, base(adb)))
    for c in _write_cmds(adb):
        assert "vsl_template4_prefs.xml" not in c, c
        assert "vsl_widget_local_prefs.xml" not in c, c


def test_patch_tra_ve_dung_danh_sach_file_da_ghi(adb):
    res = do_patch(adb, {"enable_onb3_screen": "false"})
    assert res.written == (MIRROR_FO, SETTINGS_REL, ACTIVATE_REL)
    assert res.fetch_time_ms == NOW


def test_summary_khong_lo_noi_dung_file(adb):
    s = do_patch(adb, {"ad_load_timeout": "99"}).summary
    assert s["applied"] == {"ad_load_timeout": "99"}
    assert "configs_key" not in repr(s)


def _redirect_cmds(adb):
    return [c for c in adb.calls if "sh -c" in c and ">" in c]


def test_duong_1_khong_de_shell_ngoai_an_dau_redirect(adb):
    """Regression: `adb shell run-as pkg sh -c "cat tmp > dest"` KHONG chay dung.

    adb noi argv thanh MOT dong roi cho `sh` NGOAI tren device chay -> dau `>`
    bi shell ngoai an, no tao file theo cwd cua chinh no (`/`) va bao
    "No such file or directory". Da gap that tren Pixel 4: MOI file deu roi
    xuong duong stdin du phong, ton 2 vong adb thay vi 1.

    Nen dau `>` PHAI nam trong cap nhay cua `sh -c`.
    """
    do_patch(adb, {"ad_load_timeout": "99"})
    cmds = _redirect_cmds(adb)
    assert cmds, "khong thay lenh redirect nao"
    for c in cmds:
        i = c.index("sh -c")
        q = c.index("'", i)          # nhay mo cua cau lenh trong
        assert q < c.index(">"), f"dau > nam ngoai nhay -> shell ngoai se an: {c}"


def test_duong_1_thanh_cong_thi_khong_dung_fallback(adb):
    """Fallback chi la duong du phong - khong duoc thanh duong chinh."""
    do_patch(adb, {"ad_load_timeout": "99"})
    assert not [c for c in adb.calls if "| run-as" in c], "da roi xuong fallback khong can thiet"
