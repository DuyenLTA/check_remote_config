"""Dong quang cao toan man trong luc lai FO: ad test khong co node nut dong thi BACK sau khi cho du."""

from __future__ import annotations

from rcr import fo_flow, ui_dump

from test_fo_steps import AD_TEST_KHONG_NUT


def nodes(xml):
    return ui_dump.app_nodes(ui_dump.parse_dump(xml))


def test_ad_test_khong_nut_dong_chi_back_sau_khi_cho_du():
    fo_flow._AD.clear()
    ns = nodes(AD_TEST_KHONG_NUT)
    assert fo_flow.nut_dong_ad("S", ns, bay_gio=100.0) is None
    assert not fo_flow.nen_back_ad_test("S", ns, bay_gio=100.0)
    assert fo_flow.nut_dong_ad("S", ns, bay_gio=105.0) is None
    assert not fo_flow.nen_back_ad_test("S", ns, bay_gio=105.0)
    assert fo_flow.nut_dong_ad("S", ns, bay_gio=110.0) is None
    assert fo_flow.nen_back_ad_test("S", ns, bay_gio=110.0)
    assert "S" not in fo_flow._AD


def test_ad_that_khong_nut_dong_khong_bao_gio_back():
    fo_flow._AD.clear()
    ns = nodes(AD_TEST_KHONG_NUT.replace("Quảng cáo thử nghiệm", "Sponsored"))
    for t in (100.0, 110.0, 130.0):
        assert fo_flow.nut_dong_ad("S", ns, bay_gio=t) is None
        assert not fo_flow.nen_back_ad_test("S", ns, bay_gio=t)
