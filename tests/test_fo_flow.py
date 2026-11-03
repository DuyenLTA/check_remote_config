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


# Trang native full man chen giua cac trang onboarding (AIP936 1.9.0, Pixel 4, 02/11/2026): vuot khong qua,
# lai "di het luong" vuot trai ~40 lan. Phai cho het dem nguoc roi bam btnSkip, khong bam vao than ad / OPEN.
P = "com.aihomedesign.aihomedecor.designidea.aiinterior:id/"
NATIVE_FULL_OB = f"""<?xml version='1.0' encoding='UTF-8'?>
<hierarchy rotation="0">
  <node index="0" class="android.widget.FrameLayout" package="com.ai.app" resource-id="{P}viewPagerOnboarding"
        text="" content-desc="" bounds="[0,0][1080,2148]" clickable="false" enabled="true">
    <node index="0" class="android.widget.FrameLayout" package="com.ai.app" resource-id="{P}nativeAdView"
          text="" content-desc="" bounds="[0,0][1080,2148]" clickable="false" enabled="true">
      <node index="0" class="android.widget.FrameLayout" package="com.ai.app" resource-id="{P}ad_media"
            text="" content-desc="" bounds="[0,90][1080,2064]" clickable="false" enabled="true" />
      <node index="1" class="android.widget.Button" package="com.ai.app" resource-id="{P}ad_call_to_action"
            text="OPEN" content-desc="" bounds="[48,2076][1032,2148]" clickable="true" enabled="true" />
      <node index="2" class="android.widget.ImageView" package="com.ai.app" resource-id="{P}btnSkip"
            text="" content-desc="" bounds="[930,180][1051,301]" clickable="true" enabled="true" />
    </node>
  </node>
</hierarchy>"""


def test_native_full_trong_onboarding_bam_dung_nut_x():
    from rcr import fo_steps

    ns = nodes(NATIVE_FULL_OB)
    assert fo_steps.la_native_full_co_nut(ns, (1080, 2280))
    nut = fo_steps.find_close_native_full(ns, (1080, 2280))
    assert nut is not None and nut.resource_id == "btnSkip"


def test_native_full_dang_dem_nguoc_thi_cho():
    from rcr import fo_steps

    ns = nodes(NATIVE_FULL_OB.replace('resource-id="' + P + 'ad_media"\n            text=""',
                                      'resource-id="' + P + 'ad_media"\n            text="Skip in 4"'))
    assert fo_steps.la_native_full_co_nut(ns, (1080, 2280))
    assert fo_steps.find_close_native_full(ns, (1080, 2280)) is None


def test_trang_ob_thuong_khong_phai_native_full():
    from rcr import fo_steps

    ns = nodes(NATIVE_FULL_OB.replace("nativeAdView", "ctlContent"))
    assert not fo_steps.la_native_full_co_nut(ns, (1080, 2280))


def test_qua_native_full_bam_x_sau_khi_nut_dung_yen():
    import asyncio

    bam = []

    async def tap(client, serial, node):
        bam.append(node.resource_id)
    fo_flow._AD.clear()
    goc = fo_flow._tap
    fo_flow._tap = tap
    try:
        ns = nodes(NATIVE_FULL_OB)
        lan1 = asyncio.run(fo_flow._qua_native_full(None, "S", ns, (1080, 2280)))
        lan2 = asyncio.run(fo_flow._qua_native_full(None, "S", ns, (1080, 2280)))
    finally:
        fo_flow._tap = goc
    assert lan1 == ("cho native full man het dem nguoc", False)     # nut vua hien: doc lai cho chac
    assert lan2[0].startswith("dong native full man") and bam == ["btnSkip"]
    assert asyncio.run(fo_flow._qua_native_full(None, "S", nodes(NATIVE_FULL_OB.replace("nativeAdView", "x")),
                                                (1080, 2280))) == ("", True)
