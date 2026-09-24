"""spec_sync: loc trang spec + doi storage HTML sang text. Khong goi mang."""

from __future__ import annotations

from rcr import spec_sync


def test_chi_nhan_visionlab_tu_301_va_bo_ban_copy():
    assert spec_sync.is_spec_title("SDK TUTORIAL visionlab:tutorial:3.0.1")
    assert spec_sync.is_spec_title("SDK TUTORIAL visionlab:tutorial:3.10.0")
    assert not spec_sync.is_spec_title("SDK TUTORIAL visionlab:tutorial:3.0.0")
    assert not spec_sync.is_spec_title("SDK Tutorial - Version visionlab:tutorial:2.7.0")
    assert not spec_sync.is_spec_title("Copy of SDK TUTORIAL visionlab:tutorial:3.0.2")


def test_ten_file_ngan_on_dinh():
    assert spec_sync.slug("SDK TUTORIAL visionlab:tutorial:3.5.3") == "tutorial-3.5.3"
    assert spec_sync.slug("SDK Tutorial - Ver 6.4.0 - 020725") == "sdk-tutorial-ver-6.4.0-020725"


def test_storage_html_sang_text_giu_bang_heading_bo_placeholder():
    html = ('<h2>Keys</h2><table><tr><th>Key</th><th>Default</th></tr>'
            '<tr><td>timer_button_x</td><td>5</td></tr></table>'
            '<p><ac:placeholder>goi y</ac:placeholder>ok&nbsp;x</p><ul><li></li></ul>')
    t = spec_sync.to_text(html)
    assert "## Keys" in t and "| timer_button_x | 5" in t
    assert "goi y" not in t and "ok x" in t
