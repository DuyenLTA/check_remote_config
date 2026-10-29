"""Dong quang cao toan man: chi bam dung nut dong cua ad, khong bam mu.

Dump that: inter test tren Sorapix 1.6.0, Pixel 6, 24/10/2026 - ca man la WebView
cua ad, nut "Đóng" la `dismiss-button`, node "More" de len nua phai cua no.
"""

from __future__ import annotations

from pathlib import Path

from rcr import fo_steps, ui_dump

INTER = (Path(__file__).parent / "fixtures" / "uidump_inter_dismiss_button.xml").read_text("utf-8")


def test_nut_dong_con_dem_nguoc_thi_chua_bam():
    """Dump that: dismiss-button chua "Đóng" + "1" (con 1s dem nguoc) -> bam luc nay la cham vao ad."""
    assert fo_steps.find_close_ad(ui_dump.parse_dump(INTER)) is None
    assert fo_steps.find_close_ad(ui_dump.parse_dump(INTER), cho_dem_nguoc=False).text == "Đóng"   # qua tran


def test_so_ngoai_nut_dong_khong_phai_dem_nguoc():
    xa = INTER.replace('bounds="[339,2034][414,2109]"', 'bounds="[700,400][760,460]"')
    assert fo_steps.find_close_ad(ui_dump.parse_dump(xa)).text == "Đóng"


def test_bam_chu_dong_trong_dismiss_button_khong_bam_more():
    node = fo_steps.find_close_ad(ui_dump.parse_dump(INTER.replace('text="1"', 'text=""')))
    assert node.text == "Đóng"
    assert (node.bounds.left, node.bounds.top, node.bounds.right, node.bounds.bottom) == (162, 2022, 285, 2121)


def test_khong_thay_nut_dong_thi_khong_tra_gi_de_bam():
    khong_nut = INTER.replace('resource-id="dismiss-button"', 'resource-id=""').replace('text="Đóng"', 'text=""')
    assert fo_steps.find_close_ad(ui_dump.parse_dump(khong_nut)) is None


def test_chu_dong_phai_khop_tron_khong_lay_chu_trong_creative():
    assert fo_steps.AD_CLOSE_WORDS.match("Đóng") and fo_steps.AD_CLOSE_WORDS.match("Continue to app")
    assert not fo_steps.AD_CLOSE_WORDS.match("Close your eyes and relax")


def test_nut_dong_phai_on_dinh_hai_lan_doc_moi_bam():
    from rcr import fo_flow
    fo_flow._AD.clear()
    ns = ui_dump.parse_dump(INTER.replace('text="1"', 'text=""'))
    assert fo_flow.nut_dong_ad("S1", ns, 100.0) is None                 # lan dau thay nut: doc lai cho chac
    assert fo_flow.nut_dong_ad("S1", ns, 101.0).text == "Đóng"
    co_dem = ui_dump.parse_dump(INTER)
    # Doc moi giay: con dem nguoc thi khong bam suot 20s; qua tran thi doc them 1 lan cho on dinh roi moi bam.
    assert all(fo_flow.nut_dong_ad("S2", co_dem, float(t)) is None for t in range(0, 21))
    assert fo_flow.nut_dong_ad("S2", co_dem, 21.0).text == "Đóng"


def test_cau_dem_nguoc_o_dau_cung_tinh():
    assert fo_steps.DEM_NGUOC_CAU.search("Đóng sau 3s") and fo_steps.DEM_NGUOC_CAU.search("Skip in 4")
    assert fo_steps.DEM_NGUOC_CAU.search("5 giây") and not fo_steps.DEM_NGUOC_CAU.search("Đóng")
