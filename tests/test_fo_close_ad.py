"""Dong quang cao toan man: chi bam dung nut dong cua ad, khong bam mu.

Dump that: inter test tren Sorapix 1.6.0, Pixel 6, 24/10/2026 - ca man la WebView
cua ad, nut "Đóng" la `dismiss-button`, node "More" de len nua phai cua no.
"""

from __future__ import annotations

from pathlib import Path

from rcr import fo_steps, ui_dump

INTER = (Path(__file__).parent / "fixtures" / "uidump_inter_dismiss_button.xml").read_text("utf-8")


def test_bam_chu_dong_trong_dismiss_button_khong_bam_more():
    node = fo_steps.find_close_ad(ui_dump.parse_dump(INTER))
    assert node.text == "Đóng"
    assert (node.bounds.left, node.bounds.top, node.bounds.right, node.bounds.bottom) == (162, 2022, 285, 2121)


def test_khong_thay_nut_dong_thi_khong_tra_gi_de_bam():
    khong_nut = INTER.replace('resource-id="dismiss-button"', 'resource-id=""').replace('text="Đóng"', 'text=""')
    assert fo_steps.find_close_ad(ui_dump.parse_dump(khong_nut)) is None


def test_chu_dong_phai_khop_tron_khong_lay_chu_trong_creative():
    assert fo_steps.AD_CLOSE_WORDS.match("Đóng") and fo_steps.AD_CLOSE_WORDS.match("Continue to app")
    assert not fo_steps.AD_CLOSE_WORDS.match("Close your eyes and relax")
