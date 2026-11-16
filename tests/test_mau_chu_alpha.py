"""Chu co alpha: #FF0000 ve ra (236,0,0) tren nen toi (BeautyGenie checkin Pixel 4 16/11/2026) -> van dem dung mau."""

import io

from PIL import Image, ImageDraw

from rcr import mau_chu
from rcr.ui_dump import Bounds, DeviceNode


def _n(text, b):
    return DeviceNode("0", "", "android.widget.TextView", text, "", Bounds(*b), False, True, True, "p", None, 0)


def test_chu_alpha_lech_20_van_dem_dung_mau_khong_nham_mau_khac():
    im = Image.new("RGB", (400, 300), (16, 19, 34))
    d = ImageDraw.Draw(im)
    d.rectangle((20, 120, 380, 160), fill=(236, 0, 0))          # "chu" do co alpha
    buf = io.BytesIO()
    im.save(buf, "PNG")
    r = mau_chu.do([_n("QA - Title", (20, 120, 380, 160))], buf.getvalue(), ["#FF0000", "#00FF00"])
    dem = r[0]["dem"]
    assert dem["#FF0000"][0] > 1000 and dem["#FF0000"][1] == 0
    assert dem["#00FF00"] == [0, 0]
