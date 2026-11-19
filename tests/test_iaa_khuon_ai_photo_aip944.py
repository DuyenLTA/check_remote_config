"""Khuon IAA `ai_photo` nhan dung Home AIP944 (AI Studio, the "Text to Image"/"Image to Image", hang "Trending Now")
va cho xong buoc xem ads khi man loading gen ngam chi hien "Taking you to Home in Ns" (khong co chu "%")."""

import re

from rcr import iaa_khuon, rating_cong_thuc
from rcr.ui_dump import parse_dump

HOME_AIP944 = """<?xml version='1.0' encoding='UTF-8' standalone='yes' ?><hierarchy rotation="0">
<node index="0" text="" resource-id="" class="android.widget.FrameLayout" package="p" content-desc="" clickable="false" enabled="true" bounds="[0,0][1080,2400]">
<node index="0" text="AI Studio" resource-id="" class="android.widget.TextView" package="p" content-desc="" clickable="false" enabled="true" bounds="[171,170][467,257]" />
<node index="1" text="Text to Image" resource-id="" class="android.widget.TextView" package="p" content-desc="" clickable="false" enabled="true" bounds="[681,538][922,585]" />
<node index="2" text="Image to Image" resource-id="" class="android.widget.TextView" package="p" content-desc="" clickable="false" enabled="true" bounds="[83,987][451,1050]" />
<node index="3" text="Trending Now" resource-id="" class="android.widget.TextView" package="p" content-desc="" clickable="false" enabled="true" bounds="[44,1199][429,1274]" />
<node index="4" text="" resource-id="" class="android.view.View" package="p" content-desc="Cobalt Sweater" clickable="false" enabled="true" bounds="[44,1307][429,1992]" />
<node index="5" text="AI STUDIO" resource-id="" class="android.widget.TextView" package="p" content-desc="" clickable="false" enabled="true" bounds="[144,2108][308,2178]" />
</node></hierarchy>"""


def _khuon_ai_photo() -> dict:
    return iaa_khuon.cac_khuon()["ai_photo"]


def test_home_aip944_khop_khuon_ai_photo():
    nodes = parse_dump(HOME_AIP944)
    ten, doan = iaa_khuon.khuon_khop(nodes)
    assert ten == "khuôn ai_photo" and doan


def test_style_o_home_bam_the_duoi_trending_now():
    nodes = parse_dump(HOME_AIP944)
    buoc = next(b for d in _khuon_ai_photo()["doan"] if d["ten"].startswith("Style ở Home") for b in d["buoc"]
                if "tap_duoi" in b)
    the = rating_cong_thuc.tim_duoi(nodes, buoc["tap_duoi"])
    assert the is not None and the.content_desc == "Cobalt Sweater"


def test_xem_ads_xong_khi_loading_gen_ngam_khong_co_phan_tram():
    toi = [b["toi_chu"] for d in _khuon_ai_photo()["doan"] for b in d["buoc"] if "toi_chu" in b]
    assert toi
    for mau in toi:
        assert re.search(mau, "Taking you to Home in 1s")
        assert re.search(mau, "27%")
        assert not re.search(mau, "Watch Ads (0/5)")
