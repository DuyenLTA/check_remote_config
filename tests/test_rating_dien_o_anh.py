"""Buoc `dien_o_anh` cua cong thuc rating: template nhieu o anh (AIP927 Pictifaze can >= 3 anh moi bat Generate)."""

from io import BytesIO

from PIL import Image

from rcr import rating_cong_thuc, ui_dump


def _png(o_sang: tuple[int, int] | None, icon: bool = False) -> bytes:
    """Man 1080x2408 nen toi (18); `o_sang` = (trai, phai) o da co anh (sang ca o); `icon` = icon anh xam giua o trong."""
    im = Image.new("RGB", (1080, 2408), (18, 18, 18))
    if o_sang:
        for x in range(*o_sang):
            for y in range(938, 1613, 3):
                im.putpixel((x, y), (200, 160, 120))
    if icon:
        for x in range(60, 820):
            for y in range(1240, 1310):
                im.putpixel((x, y), (110, 110, 110))
    buf = BytesIO()
    im.save(buf, "PNG")
    return buf.getvalue()


def _xml(nut_enabled: bool) -> str:
    return f"""<hierarchy><node index="0" text="" resource-id="" class="android.widget.FrameLayout" package="p"
 content-desc="" clickable="false" enabled="true" bounds="[0,0][1080,2408]">
<node index="0" text="Change" resource-id="" class="android.widget.TextView" package="p" content-desc=""
 clickable="false" enabled="true" bounds="[778,320][990,455]"/>
<node index="1" text="" resource-id="" class="android.view.View" package="p" content-desc="" clickable="true"
 enabled="true" bounds="[45,938][833,1613]"/>
<node index="2" text="" resource-id="" class="android.view.View" package="p" content-desc="" clickable="true"
 enabled="{str(nut_enabled).lower()}" bounds="[112,2183][968,2329]">
<node index="0" text="Generate with Ads" resource-id="" class="android.widget.TextView" package="p" content-desc=""
 clickable="false" enabled="true" bounds="[341,2228][739,2285]"/></node></node></hierarchy>"""


def test_o_trong_nhan_o_net_dut_va_o_da_co_anh():
    """O trong co icon anh xam o GIUA (y ~1275) -> khong duoc doc hang giua (17/11/2026: dien 4/5 o roi ket)."""
    o = next(n for n in ui_dump.parse_dump(_xml(False)) if n.clickable and n.bounds.top == 938)
    assert rating_cong_thuc.o_trong(_png(None, icon=True), o.bounds)
    assert not rating_cong_thuc.o_trong(_png((45, 833)), o.bounds)


def test_nut_bat_doc_enabled_o_node_cha_bam_duoc():
    """Compose de enabled=false o node cha bam duoc, node chu 'Generate with Ads' van enabled=true."""
    assert not rating_cong_thuc.nut_bat(ui_dump.parse_dump(_xml(False)), "^Generate with Ads$")
    assert rating_cong_thuc.nut_bat(ui_dump.parse_dump(_xml(True)), "^Generate with Ads$")


def test_cong_thuc_pictifaze_chi_co_video_va_ep_cho_dai():
    pkg = "photoslideshow.videoslideshow.addimage.photogen"
    assert rating_cong_thuc.cong_thuc(pkg, "anh") is None
    video = rating_cong_thuc.cong_thuc(pkg, "video")
    assert any("dien_o_anh" in b for b in video)
    assert int(rating_cong_thuc.ep_cau_hinh(pkg)["generating_wait_video_seconds"]) >= 300
