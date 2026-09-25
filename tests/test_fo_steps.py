"""Test cac thao tac tren man First Open. Thuan du lieu, khong can may.

Diem phai gac:
  - node duy nhat 'clickable' tren man Language la nut cua QUANG CAO -> tru vung
    quang cao theo hinh hoc truoc khi xep hang bat cu thu gi
  - `exo_ad_overlay` la lop phu ExoPlayer, KHONG phai quang cao
  - hang English la hang BUNG RA: bam lan dau chi mo bien the, chua chon duoc
"""

from __future__ import annotations

from rcr import fo_steps, ui_dump

ONBOARDING = """<?xml version='1.0' encoding='UTF-8'?>
<hierarchy rotation="0">
  <node index="0" class="android.view.ViewGroup" package="com.ai.app" resource-id="com.ai.app:id/viewPagerOnboarding"
        text="" content-desc="" bounds="[0,0][1080,2400]" clickable="false" enabled="true">
    <node index="0" class="android.view.View" package="com.ai.app" resource-id="com.ai.app:id/exo_ad_overlay"
          text="" content-desc="" bounds="[0,0][1080,1440]" clickable="false" enabled="true" />
    <node index="1" class="android.widget.Button" package="com.ai.app" resource-id="com.ai.app:id/btnNextOnboarding"
          text="Next" content-desc="" bounds="[727,1244][898,1354]" clickable="true" enabled="true" />
    <node index="2" class="android.widget.FrameLayout" package="com.ai.app" resource-id="com.ai.app:id/nativeAdView"
          text="" content-desc="" bounds="[0,1700][1080,2300]" clickable="false" enabled="true">
      <node index="0" class="android.widget.Button" package="com.ai.app" resource-id="com.ai.app:id/ad_call_to_action"
            text="INSTALL" content-desc="" bounds="[100,2150][980,2280]" clickable="true" enabled="true" />
    </node>
  </node>
</hierarchy>
"""

LANGUAGE = """<?xml version='1.0' encoding='UTF-8'?>
<hierarchy rotation="0">
  <node index="0" class="android.view.ViewGroup" package="com.ai.app" resource-id="com.ai.app:id/root"
        text="" content-desc="" bounds="[0,0][1080,2400]" clickable="false" enabled="true">
    <node index="0" class="android.widget.TextView" package="com.ai.app" resource-id="com.ai.app:id/titleLanguageItem"
          text="English" content-desc="" bounds="[200,600][900,680]" clickable="false" enabled="true" />
    <node index="1" class="android.widget.ImageView" package="com.ai.app" resource-id="com.ai.app:id/iconExpandLanguageItem"
          text="" content-desc="" bounds="[900,600][980,680]" clickable="false" enabled="true" />
    <node index="2" class="android.widget.TextView" package="com.ai.app" resource-id="com.ai.app:id/titleLanguageItem"
          text="हिन्दी" content-desc="" bounds="[200,800][900,880]" clickable="false" enabled="true" />
    <node index="3" class="android.widget.CheckBox" package="com.ai.app" resource-id="com.ai.app:id/checkboxLanguageItem"
          text="" content-desc="" bounds="[900,800][980,880]" clickable="false" enabled="true" />
  </node>
</hierarchy>
"""

EXPANDED = LANGUAGE.replace(
    '''text="हिन्दी" content-desc="" bounds="[200,800][900,880]"''',
    '''text="English (US)" content-desc="" bounds="[260,800][900,880]"''',
)


def nodes(xml):
    return ui_dump.app_nodes(ui_dump.parse_dump(xml))


def test_khong_bao_gio_bam_vao_nut_cua_quang_cao():
    """Tren man that, node clickable duy nhat lai la CTA cua native ad."""
    safe = fo_steps.outside_ads(nodes(ONBOARDING))
    assert not any(n.resource_id == "ad_call_to_action" for n in safe)
    assert any(n.resource_id == "btnNextOnboarding" for n in safe)


def test_lop_phu_ExoPlayer_khong_phai_quang_cao():
    """`exo_ad_overlay` phu nua man - coi la ads thi nuot luon nut Next."""
    found = fo_steps.find_node(nodes(ONBOARDING), resource_id="btnNextOnboarding")
    assert found is not None and found.text == "Next"


def test_nut_tiep_tuc_khong_lay_nut_cua_quang_cao():
    node = fo_steps.find_continue(nodes(ONBOARDING), (1080, 2400))
    assert node.resource_id == "btnNextOnboarding"


def test_hang_ngon_ngu_bung_ra_thi_phai_lam_hai_nhip():
    first = fo_steps.language_targets(nodes(LANGUAGE), "English")
    assert len(first) == 2 and first[0].text == "English"   # moi bung, chua chon
    after = fo_steps.language_targets(nodes(EXPANDED), "English")
    assert len(after) == 1 and after[0].text == "English (US)"


# --- case nay noi ve man nao --------------------------------------------------

def test_doc_ra_man_can_lai_toi_tu_nhan_case():
    from rcr import fo_flow

    assert fo_flow.target_for("#20 Ads OFF + swipe_onb2 → icon SWIPE") == "OnboardingActivity"
    assert fo_flow.target_for("Popup Rating tại màn Home") == "MainActivity"
    # case ve splash thi app tu dung san o do, khong phai lai di dau
    assert fo_flow.target_for("#1 splash_banner_change=false, RC bật cả 2") == ""
