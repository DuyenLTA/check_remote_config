"""Test dua app ve trang thai case doi. Khong can may that.

Diem phai gac:
  - Precondition khong doi state sach -> CHI force-stop, khong dong vao du lieu
  - Co co onboarding -> lat co (giu login/ngon ngu), KHONG `pm clear`
  - Khong co co -> moi `pm clear`, va phai cho file config sinh lai truoc khi patch
  - `pm clear` xong thi baseline cu het gia tri -> bao baseline_stale
"""

from __future__ import annotations

import asyncio

import pytest
from conftest import (
    ACTIVATE,
    ACTIVATE_JSON,
    MIRROR_BILLING,
    MIRROR_FIRST_OPEN,
    PKG,
    SERIAL,
    SETTINGS,
    SETTINGS_XML,
    WIDGET_LOCAL,
    FakeAdb,
)

from rcr import device_reset, mirror_xml, rc_baseline
from rcr.adb_parsers import AdbError
from rcr.models import RcError

PREFS = "shared_prefs/vsl_template4_prefs.xml"
COMPONENT = f"{PKG}/.MainActivity"
UI = {
    "resolve-activity": (f"priority=0\n  {COMPONENT}\n", "", 0),
    "dumpsys window": (f"  mCurrentFocus=Window{{4a2 u0 {COMPONENT}}}\n", "", 0),
}
# State noi bo KHONG co co onboarding -> buoc phai pm clear
NO_FLAG = """<?xml version='1.0' encoding='utf-8' standalone='yes' ?>
<map>
    <string name="ARG_KEY_SELECTED_LANGUAGE">vi</string>
</map>
"""


def fake(files=None, fails=None):
    return FakeAdb(files=files, fails={**UI, **(fails or {})})


def files_with(prefs_xml):
    return {
        f"files/{ACTIVATE}": ACTIVATE_JSON,
        f"shared_prefs/{SETTINGS}": SETTINGS_XML,
        "shared_prefs/vsl_template4_remote_first_open.xml": MIRROR_FIRST_OPEN,
        "shared_prefs/vsl_billing_remote_config.xml": MIRROR_BILLING,
        PREFS: prefs_xml,
        "shared_prefs/vsl_widget_local_prefs.xml": WIDGET_LOCAL,
    }


def baseline_of(adb):
    return asyncio.run(rc_baseline.read(adb, SERIAL, PKG))


# --- doc luat ----------------------------------------------------------------

@pytest.mark.parametrize("text", [
    "User chưa từng mở app",
    "App vừa mới cài, lần đầu mở",
    "Fresh install, chưa đăng nhập",
    "New user",
])
def test_nhan_ra_case_doi_state_sach(text):
    assert device_reset.needs_clean(text)


@pytest.mark.parametrize("text", [
    "App đã mở nhiều lần, đã qua onb",   # 'onb' khong phai 'onboarding'
    "User đã đăng nhập",
    "",
])
def test_case_thuong_khong_bi_coi_la_doi_state_sach(text):
    assert device_reset.needs_clean(text) == ""


# --- ba muc do ---------------------------------------------------------------

def test_case_thuong_chi_force_stop_khong_dong_vao_du_lieu():
    adb = fake()
    out = asyncio.run(device_reset.prepare(adb, baseline_of(adb), "App đã đăng nhập"))
    assert out == {"mode": "force-stop", "matched": "", "baseline_stale": False}
    assert adb.cmds_with("force-stop") and not adb.cmds_with("push")
    assert not adb.cmds_with("pm clear")


def test_co_co_onboarding_thi_lat_co_chu_khong_pm_clear():
    """Lat co giu nguyen login/ngon ngu - re hon pm clear rat nhieu."""
    adb = fake()
    out = asyncio.run(device_reset.prepare(adb, baseline_of(adb), "User chưa từng mở app"))
    assert out["mode"] == "soft"
    assert out["file"] == "vsl_template4_prefs.xml"
    assert out["baseline_stale"] is False
    assert not adb.cmds_with("pm clear")
    node = mirror_xml.parse_nodes(adb.files[PREFS])["ARG_KEY_SHOW_ONBOARDING"]
    assert node.value == "true"
    # ngon ngu khong bi dong vao
    assert 'ARG_KEY_SELECTED_LANGUAGE">vi' in adb.files[PREFS]


def test_khong_co_co_thi_pm_clear_va_bao_baseline_het_gia_tri():
    adb = fake(files=files_with(NO_FLAG), fails={"pm clear": ("Success\n", "", 0)})
    out = asyncio.run(device_reset.prepare(adb, baseline_of(adb), "Fresh install"))
    assert out["mode"] == "clear"
    # file config bi sinh lai -> ban baseline cu tro toi noi dung khong con nua
    assert out["baseline_stale"] is True
    assert adb.cmds_with("pm clear") and adb.cmds_with("am start")


def test_pm_clear_that_bai_thi_dung_lai():
    adb = fake(files=files_with(NO_FLAG), fails={"pm clear": ("", "Failed", 1)})
    with pytest.raises(AdbError, match="pm clear"):
        asyncio.run(device_reset.prepare(adb, baseline_of(adb), "Fresh install"))


def test_app_chua_sinh_lai_file_config_thi_khong_patch_bua(monkeypatch):
    """Ghi bang redirect can file dich ton tai san - chua co thi phai dung."""
    adb = fake(files=files_with(NO_FLAG), fails={
        "pm clear": ("Success\n", "", 0),
        "ls files": ("PersistedInstallation.W0RFRkFVTFRd.json\ngeneratefid.lock\n", "", 0),
    })
    bl = baseline_of(FakeAdb(files=files_with(NO_FLAG), fails=dict(UI)))
    monkeypatch.setattr(device_reset, "WAIT_FRC", 0.02)
    monkeypatch.setattr(device_reset, "POLL_INTERVAL", 0.01)
    with pytest.raises(RcError, match="chua sinh lai file remote config"):
        asyncio.run(device_reset.prepare(adb, bl, "Fresh install"))
