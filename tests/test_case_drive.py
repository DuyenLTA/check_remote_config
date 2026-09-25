"""Test lai app qua cac buoc Action. Khong can may that.

Diem phai gac:
  - quang cao che man hinh -> DUNG, tuyet doi khong tu tim nut dong
  - buoc khong dich duoc -> dung ngay, khong lam tiep cac buoc sau
  - buoc dich duoc -> tap dung toa do tam node
"""

from __future__ import annotations

import asyncio

from conftest import PKG, FakeAdb
from test_ui_dump import DUMP_XML

from rcr import case_drive

APP_XML = DUMP_XML.replace("com.ai.app", PKG)
COMPONENT = f"{PKG}/.MainActivity"
AD_COMPONENT = f"{PKG}/com.google.android.gms.ads.AdActivity"


def fake(activity=COMPONENT):
    return FakeAdb(fails={
        "dumpsys window": (f"  mCurrentFocus=Window{{4a2 u0 {activity}}}\n", "", 0),
        "uiautomator dump": ("UI hierchary dumped to: /data/local/tmp/rcr_uidump.xml\n", "", 0),
        "rcr_uidump.xml": (APP_XML, "", 0),
    })


def drive(adb, steps):
    return asyncio.run(case_drive.drive(adb, "29301FDH2006K7", PKG, steps))


def test_quang_cao_che_man_hinh_thi_dung_va_khong_tap():
    adb = fake(AD_COMPONENT)
    out = drive(adb, ["Mở tab Moment"])
    assert out["status"] == "NEEDS_HUMAN" and out["stopped_at"] == 1
    assert "quang cao" in out["steps"][0]["action"]["reason"]
    assert not adb.cmds_with("input tap")


def test_app_khac_bung_len_thi_dung():
    adb = fake("com.other.app/.Main")
    out = drive(adb, ["Mở tab Moment"])
    assert out["status"] == "NEEDS_HUMAN"
    assert "khong phai" in out["steps"][0]["action"]["reason"]


def test_lai_duoc_thi_tap_dung_tam_node():
    adb = fake()
    out = drive(adb, ["Mở tab Moment", "Quan sát màn hình"])
    assert out["status"] == "DONE"
    assert adb.cmds_with("input tap 540 2300")
    assert [s["action"]["kind"] for s in out["steps"]] == ["tap", "noop"]
    # dump giu lai de phase 5 cham, khong phai chup lai
    assert "<hierarchy" in out["steps"][0]["dump"]


def test_buoc_khong_dich_duoc_thi_dung_ngay_khong_lam_tiep():
    adb = fake()
    out = drive(adb, ['Nhấn nút "See All"', "Mở tab Moment"])
    assert out["status"] == "NEEDS_HUMAN" and out["stopped_at"] == 1
    assert len(out["steps"]) == 1
    assert not adb.cmds_with("input tap")


def test_quang_cao_che_man_hinh_van_cho_buoc_QUAN_SAT_di_tiep():
    """Case ads cham bang log - inter de len truoc khi kip nhin banner la binh thuong."""
    adb = fake(AD_COMPONENT)
    out = drive(adb, ["Chờ Splash load", "Quan sát bottom banner"])
    assert out["status"] == "DONE"
    assert out["blocked_steps"] == [1, 2]
    # danh dau de phase 5 biet dump nay khong phai UI app
    assert all("screen_blocked" in s for s in out["steps"])
    assert not adb.cmds_with("input tap")


def test_quang_cao_van_chan_buoc_phai_bam():
    adb = fake(AD_COMPONENT)
    out = drive(adb, ["Quan sát màn hình", "Mở tab Moment"])
    assert out["status"] == "NEEDS_HUMAN" and out["stopped_at"] == 2
    assert "quang cao" in out["steps"][1]["action"]["reason"]
    assert not adb.cmds_with("input tap")
