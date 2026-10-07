"""Doc cay view tu `dumpsys activity top` (fixture lay tu Pixel 4, 2026-10-07)."""

from __future__ import annotations

from pathlib import Path

from rcr import quan_sat, view_hierarchy_fast as vhf

PKG = "com.ai.aiimage.aivideogenerator"
RAW = (Path(__file__).parent / "fixtures" / "dumpsys_activity_top_ob3.txt").read_text()


def _x(views):
    return [v for v in views if quan_sat.la_id_x(v.rid)]


def test_chi_lay_view_cua_app_dang_test():
    views = vhf.parse(RAW, PKG)
    assert any(v.rid == "viewPagerOnboarding" for v in views)
    chrome = vhf.parse(RAW, "com.android.chrome")
    assert chrome and not any(v.rid == "viewPagerOnboarding" for v in chrome)


def test_nut_x_dang_gone_thi_khong_hien():
    assert [v.visible for v in _x(vhf.parse(RAW, PKG))] == [False]


def test_nut_x_hien_va_toa_do_quy_ve_man():
    raw = RAW.replace("GFED..C.. ......I. 930,180-1051,301", "VFED..C.. ......I. 930,180-1051,301")
    (x,) = _x(vhf.parse(raw, PKG))
    assert x.visible and x.rid == "btnSkip"
    # trang OB3 nam o x=2160 trong ViewPager -> toa do tren man = left % rong man
    assert x.left % 1080 == 930 and x.top == 180


def test_cha_an_thi_con_cung_an():
    raw = RAW.replace("GFED..C.. ......I. 930,180-1051,301", "VFED..C.. ......I. 930,180-1051,301")
    # an trang chua nut X (ConstraintLayout cua trang thu 3, x=2160)
    raw = raw.replace("ConstraintLayout{c9aac4c V.E", "ConstraintLayout{c9aac4c G.E")
    assert [v.visible for v in _x(vhf.parse(raw, PKG))] == [False]


def test_vai_tro_nut_x_khong_gan_id_cua_mot_app():
    assert quan_sat.la_id_x("btnSkip") and quan_sat.la_id_x("iv_close_ad")
    assert quan_sat.la_id_x("imgDismiss")
    assert quan_sat.la_id_dem("btnTimeoutSkip") and not quan_sat.la_id_x("btnTimeoutSkip")
    assert quan_sat.la_id_dem("tv_countdown") and not quan_sat.la_id_x("btnNextOnboarding")
