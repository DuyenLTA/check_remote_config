"""Test parse cay UI. Thuan du lieu - fixture theo dung dang `uiautomator dump`.

Diem phai gac:
  - resource-id KHONG unique -> phai giu index_in_parent de phan biet
  - node thieu bounds van phai giu lai (khong thi index lech), nhung invisible
  - node cua SystemUI/launcher khong phai UI app
"""

from __future__ import annotations

import pytest

from rcr import ui_dump
from rcr.adb_parsers import AdbError

PKG = "com.ai.app"

DUMP_XML = f"""<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>
<hierarchy rotation="0">
  <node index="0" class="android.widget.FrameLayout" package="{PKG}" resource-id="android:id/content"
        text="" content-desc="" bounds="[0,0][1080,2400]" clickable="false" enabled="true">
    <node index="0" class="android.widget.LinearLayout" package="{PKG}" resource-id="{PKG}:id/rowAiAlbum"
          text="" content-desc="" bounds="[0,300][1080,700]" clickable="false" enabled="true">
      <node index="0" class="android.widget.TextView" package="{PKG}" resource-id="{PKG}:id/tvTitle"
            text="AI Album" content-desc="" bounds="[40,320][400,380]" clickable="false" enabled="true" />
      <node index="1" class="android.widget.Button" package="{PKG}" resource-id="{PKG}:id/btnSeeAll"
            text="See All" content-desc="" bounds="[880,320][1040,380]" clickable="true" enabled="true" />
    </node>
    <node index="1" class="android.widget.LinearLayout" package="{PKG}" resource-id="{PKG}:id/rowAiVideo"
          text="" content-desc="" bounds="[0,700][1080,1100]" clickable="false" enabled="true">
      <node index="0" class="android.widget.Button" package="{PKG}" resource-id="{PKG}:id/btnSeeAll"
            text="See All" content-desc="" bounds="[880,720][1040,780]" clickable="true" enabled="true" />
      <node index="1" class="android.widget.ImageView" package="{PKG}" resource-id="{PKG}:id/card"
            text="" content-desc="style card" bounds="[40,800][300,1060]" clickable="true" enabled="true" />
    </node>
    <node index="2" class="android.widget.LinearLayout" package="{PKG}" resource-id="{PKG}:id/navBar"
          text="" content-desc="" bounds="[0,2200][1080,2400]" clickable="false" enabled="true">
      <node index="0" class="android.widget.TextView" package="{PKG}" resource-id="{PKG}:id/tabHome"
            text="Home" content-desc="" bounds="[0,2200][360,2400]" clickable="true" enabled="true" />
      <node index="1" class="android.widget.TextView" package="{PKG}" resource-id="{PKG}:id/tabMoment"
            text="Moment" content-desc="" bounds="[360,2200][720,2400]" clickable="true" enabled="true" />
      <node index="2" class="android.widget.TextView" package="{PKG}" resource-id="{PKG}:id/tabDisabled"
            text="Soon" content-desc="" bounds="[720,2200][1080,2400]" clickable="true" enabled="false" />
    </node>
    <node index="3" class="android.view.View" package="{PKG}" resource-id="{PKG}:id/ghost"
          text="Moment" content-desc="" bounds="" clickable="true" enabled="true" />
  </node>
  <node index="1" class="android.widget.FrameLayout" package="com.android.systemui"
        resource-id="com.android.systemui:id/status_bar" text="" content-desc=""
        bounds="[0,0][1080,100]" clickable="false" enabled="true" />
</hierarchy>
"""


def nodes():
    return ui_dump.parse_dump(DUMP_XML)


def test_giu_cay_va_index_trong_cha():
    see_all = [n for n in nodes() if n.text == "See All"]
    assert len(see_all) == 2
    # cung resource-id, khac cha -> phan biet bang parent_id/index
    assert {n.resource_id for n in see_all} == {"btnSeeAll"}
    assert [n.index_in_parent for n in see_all] == [1, 0]
    assert {n.parent_id for n in see_all} == {"0.0", "0.1"}


def test_bounds_ra_toa_do_tam():
    tab = next(n for n in nodes() if n.text == "Moment" and n.resource_id == "tabMoment")
    assert tab.bounds.center == (540, 2300)


def test_node_thieu_bounds_van_giu_nhung_invisible():
    ghost = next(n for n in nodes() if n.resource_id == "ghost")
    assert ghost.visible is False and ghost.bounds.empty


def test_bo_node_he_thong():
    app = ui_dump.app_nodes(nodes(), PKG)
    assert all(n.package == PKG for n in app)
    assert not any(n.resource_id == "status_bar" for n in app)
    assert not any(n.resource_id == "content" for n in app)  # id cua Framework


def test_xml_hong_thi_bao_ro():
    with pytest.raises(AdbError, match="khong phai XML"):
        ui_dump.parse_dump("<hierarchy><node")
