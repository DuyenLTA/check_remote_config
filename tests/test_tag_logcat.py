"""Buoc "Xem logcat tag ..." va dong "Nhan = gia tri" (TC 3.6.1 R01-01)."""

from __future__ import annotations

import asyncio

from rcr import act_resolver as r
from rcr import assert_check as a
from rcr import tag_logcat

LOG = {"VslTemplate4FirstOpenSDK": ["Using version 3.6.1"],
       "FOR_TESTER_CONFIG": ["Version Lib Ads: 1.2.10", "Target SDK: 36", "Facebook App ID: 1675893203858744"]}


def _check(line, tag_log=LOG):
    return a.check(line, {"units": {}}, {"steps": [{"n": 1, "dump": ""}], "tag_log": tag_log}, {"crashed": False})


def test_doc_cau_xem_tag():
    assert tag_logcat.tags_cua("Xem logcat tag VslTemplate4FirstOpenSDK và FOR_TESTER_CONFIG.") == [
        "VslTemplate4FirstOpenSDK", "FOR_TESTER_CONFIG"]
    ra = r.resolve("Xem logcat tag VslTemplate4FirstOpenSDK và FOR_TESTER_CONFIG.", [])
    assert ra.summary["kind"] == "xem_tag" and "tester mode" in ra.summary["reason"]
    assert tag_logcat.tags_cua("Quan sát Splash.") == []


def test_cham_theo_nhan_ra_gia_tri_that():
    assert _check("Version Lib Ads = 1.2.10")["verdict"] == a.PASS
    sai = _check("Version Lib Ads = 1.2.9")
    assert sai["verdict"] == a.FAIL and "1.2.10" in sai["reason"]


def test_sdk_tutorial_so_voi_using_version():
    assert _check("SDK = visionlab:tutorial 3.6.1.")["verdict"] == a.PASS
    assert _check("SDK = visionlab:tutorial 3.7.0.")["verdict"] == a.FAIL


def test_khong_thay_nhan_thi_khong_doan():
    ket = _check("Version Lib Ads = 1.2.10", {"FOR_TESTER_CONFIG": [], "VslTemplate4FirstOpenSDK": []})
    assert ket["verdict"] == a.NEEDS_HUMAN and "tester mode" in ket["reason"]


def test_dong_hai_cham_khac_khong_bi_cham_tag_gianh():
    ket = _check("OB2: 'FR - OB2 title'")
    assert "tag" not in ket["reason"]


class _Adb:
    def __init__(self):
        self.lenh = []

    async def shell(self, serial, *args, timeout=None):
        self.lenh.append(args)
        if args[:2] == ("logcat", "-d"):
            return ("1793421556.666 28285 28285 I FOR_TESTER_CONFIG: Version Lib Ads: 1.2.10\n"
                    "1793421556.666 999 999 I FOR_TESTER_CONFIG: Version Lib Ads: 9.9.9\n"
                    "1793421498.450 28285 28285 I VslTemplate4FirstOpenSDK: Using version 3.6.1\n", "", 0)
        if args[0] == "pidof":
            return ("28285\n", "", 0)
        return ("", "", 0)


def test_doc_chi_lay_dong_cua_pid_app():
    ra = asyncio.run(tag_logcat.doc(_Adb(), "S", "com.a", ["FOR_TESTER_CONFIG", "VslTemplate4FirstOpenSDK"]))
    assert ra == {"FOR_TESTER_CONFIG": ["Version Lib Ads: 1.2.10"], "VslTemplate4FirstOpenSDK": ["Using version 3.6.1"]}
