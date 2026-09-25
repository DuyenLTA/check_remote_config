"""Test noi ten goi cua TC voi node tren cay UI. Khong can may.

Diem phai gac:
  - cau phu dinh ("KHONG hien thi icon SWIPE") phai dao ky vong
  - chua lai toi man thi khong duoc ket luan thieu/du
  - khop id theo dang `:id/<ten>` chu khong phai chuoi bat ky trong XML
"""

from __future__ import annotations

from rcr import assert_check as a
from rcr import ui_names

DUMP_CO_SWIPE = '<node resource-id="com.ai.app:id/ob2Bb2SwipeLottie" text="" />'
DUMP_KHONG = '<node resource-id="com.ai.app:id/btnNextOnboarding" text="Next" />'
DA_TOI = {"walked": True, "steps": [{"n": 0, "action": {"kind": "walk"},
                                     "activity": "OnboardingActivity", "dump": DUMP_CO_SWIPE}]}
DA_TOI_KHONG_CO = {"walked": True, "steps": [{"n": 0, "action": {"kind": "walk"},
                                              "activity": "OnboardingActivity", "dump": DUMP_KHONG}]}
CHUA_TOI = {"steps": [{"n": 1, "action": {"kind": "noop"}, "activity": "SplashActivity", "dump": ""}]}
NO_ADS = {"units": {}}
OK = {"crashed": False, "lines": []}


def test_nhan_ra_ten_goi_cua_TC():
    el = ui_names.find_in("Vùng ad hiển thị icon SWIPE (animated)")
    assert el["name"] == "icon swipe"


def test_thay_icon_swipe_thi_PASS():
    out = a.check("Vùng ad hiển thị icon SWIPE (animated)", NO_ADS, DA_TOI, OK)
    assert out["verdict"] == a.PASS and "ob2Bb2SwipeLottie" in out["actual"]


def test_cau_phu_dinh_thi_dao_ky_vong():
    assert a.check("KHÔNG hiển thị icon SWIPE.", NO_ADS, DA_TOI_KHONG_CO, OK)["verdict"] == a.PASS
    assert a.check("KHÔNG hiển thị icon SWIPE.", NO_ADS, DA_TOI, OK)["verdict"] == a.FAIL


def test_chua_lai_toi_man_thi_khong_ket_luan():
    out = a.check("Vùng ad hiển thị icon SWIPE", NO_ADS, CHUA_TOI, OK)
    assert out["verdict"] == a.NEEDS_HUMAN


def test_khop_id_dung_dang_khong_an_nham_chuoi_bat_ky():
    el = ui_names.find_in("icon SWIPE")
    assert ui_names.seen_in(el, ['<node text="ob2Bb2SwipeLottie" />']) == ""
    assert ui_names.seen_in(el, [DUMP_CO_SWIPE]) == "ob2Bb2SwipeLottie"
