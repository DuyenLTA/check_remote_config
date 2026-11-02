"""Dong quang cao toan man trong luc lai FO: ad test khong co node nut dong thi BACK sau khi cho du."""

from __future__ import annotations

import asyncio
from pathlib import Path

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


# Trang native full OB3 (ob3_show_button_skip=true) chan vuot: buoc vuot phai bam X `btnSkip` (AIP886 2.7.0).
OB3_SKIP = (Path(__file__).parent / "fixtures" / "uidump_ob3_native_full_nut_skip.xml").read_text(encoding="utf-8")
DOT_ACTIVE = ('<node index="9" text="" resource-id="x:id/dot" class="android.view.View" package="x" content-desc="" '
              'clickable="false" enabled="true" bounds="[147,1297][200,1318]" />'
              '<node index="10" text="" resource-id="x:id/dot" class="android.view.View" package="x" content-desc="" '
              'clickable="false" enabled="true" bounds="[220,1297][241,1318]" />')


def _buoc_vuot(monkeypatch, xml):
    taps, swipes = [], []

    async def tap(client, serial, x, y):
        taps.append((x, y))

    async def swipe(client, serial, direction, screen=None, ms=0):
        swipes.append(direction)

    monkeypatch.setattr(fo_flow.device_app, "tap", tap)
    monkeypatch.setattr(fo_flow.device_app, "swipe", swipe)
    did, advance = asyncio.run(fo_flow.do_step(None, "S", {"swipe": "left"}, nodes(xml), (1080, 2400)))
    return did, advance, taps, swipes


def test_native_full_co_nut_skip_thi_bam_x_khong_vuot(monkeypatch):
    did, advance, taps, swipes = _buoc_vuot(monkeypatch, OB3_SKIP)
    assert taps == [(1003, 228)] and swipes == [] and advance
    assert "native full" in did


def test_native_full_dang_dem_nguoc_thi_van_vuot(monkeypatch):
    dem = OB3_SKIP.replace('id/btnSkip"', 'id/btnTimeoutSkip"').replace(
        'content-desc="Next" checkable="false" checked="false" clickable="true"',
        'content-desc="Next" checkable="false" checked="false" clickable="false"')
    _did, _adv, taps, swipes = _buoc_vuot(monkeypatch, dem)
    assert taps == [] and swipes == ["left"]


def test_trang_ob_co_cham_chi_trang_khong_bam_btnskip(monkeypatch):
    # Trang OB thuong co nut Skip trung id: bam vao la nhay coc het onboarding -> van vuot.
    xml = OB3_SKIP.replace("</hierarchy>", f"{DOT_ACTIVE}</hierarchy>")
    assert fo_flow.fo_steps.onboarding_page(nodes(xml)) == 1
    _did, _adv, taps, swipes = _buoc_vuot(monkeypatch, xml)
    assert taps == [] and swipes == ["left"]
