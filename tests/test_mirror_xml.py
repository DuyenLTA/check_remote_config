"""Test doc/ghi prefs XML. Thuan ham -> test nhieu, khong can device.

Diem phai gac:
  - giu dung kieu XML khi ghi (boolean/string/long/int)
  - escape dung: & phai xu truoc, khong duoc double-escape
  - value la JSON dai (mirror that co) khong bi vo
  - khong tim thay node -> raise, KHONG tu them node moi vao prefs cua app
  - sai kieu (boolean nhan '3') -> raise RO, khong ghi bua
  - moi byte khac trong file giu nguyen
"""

from __future__ import annotations

import pytest
from conftest import MIRROR_BILLING, MIRROR_FIRST_OPEN, SETTINGS_XML

from rcr.mirror_xml import coerce, escape, parse_nodes, read_long, set_long, set_value, unescape


def test_parse_du_kieu():
    n = parse_nodes(MIRROR_FIRST_OPEN)
    assert n["enable_onb3_screen"].kind == "boolean"
    assert n["enable_onb3_screen"].value == "true"
    assert n["banner_fail_time"].kind == "int"
    assert n["banner_fail_time"].value == "3"
    assert n["layout_onb2_screen"].kind == "string"
    assert n["layout_onb2_screen"].value == "layout1"


def test_parse_string_co_escape():
    n = parse_nodes(MIRROR_BILLING)
    assert n["paywall_config"].value == '{"a":1}'


def test_set_boolean_giu_kieu():
    n = parse_nodes(MIRROR_FIRST_OPEN)
    out = set_value(MIRROR_FIRST_OPEN, n["enable_onb3_screen"], "false")
    assert '<boolean name="enable_onb3_screen" value="false" />' in out
    # cac node khac khong doi
    assert '<boolean name="splash_banner_change" value="true" />' in out
    assert '<int name="banner_fail_time" value="3" />' in out


def test_set_string_giu_kieu_va_escape():
    n = parse_nodes(MIRROR_FIRST_OPEN)
    out = set_value(MIRROR_FIRST_OPEN, n["layout_onb2_screen"], 'a&b<c>"d"')
    assert "<string name=\"layout_onb2_screen\">a&amp;b&lt;c&gt;&quot;d&quot;</string>" in out
    assert parse_nodes(out)["layout_onb2_screen"].value == 'a&b<c>"d"'


def test_set_string_value_json_dai():
    """Mirror that co key chua JSON dai - khong duoc vo."""
    n = parse_nodes(MIRROR_BILLING)
    payload = '{"plans":[{"id":"p1","price":9.99},{"id":"p2","price":19.99}],"cta":"Buy & Save"}'
    out = set_value(MIRROR_BILLING, n["paywall_config"], payload)
    assert parse_nodes(out)["paywall_config"].value == payload


def test_int_va_long_parse_so():
    n = parse_nodes(MIRROR_FIRST_OPEN)
    out = set_value(MIRROR_FIRST_OPEN, n["banner_fail_time"], "7")
    assert '<int name="banner_fail_time" value="7" />' in out


def test_sai_kieu_thi_raise_chu_khong_ghi_bua():
    n = parse_nodes(MIRROR_FIRST_OPEN)
    with pytest.raises(ValueError, match="boolean"):
        set_value(MIRROR_FIRST_OPEN, n["enable_onb3_screen"], "3")
    with pytest.raises(ValueError, match="int"):
        set_value(MIRROR_FIRST_OPEN, n["banner_fail_time"], "khong phai so")


def test_khong_tim_thay_node_thi_raise():
    """Khong tu them node moi vao prefs cua app - them node la la doan."""
    from rcr.models import MirrorNode

    ghost = MirrorNode("key_khong_ton_tai", "boolean", "true")
    with pytest.raises(ValueError, match="khong tim thay node"):
        set_value(MIRROR_FIRST_OPEN, ghost, "false")


def test_chi_doi_dung_1_byte_can_doi():
    n = parse_nodes(MIRROR_FIRST_OPEN)
    out = set_value(MIRROR_FIRST_OPEN, n["enable_onb3_screen"], "false")
    assert len(out.splitlines()) == len(MIRROR_FIRST_OPEN.splitlines())
    assert out.replace('value="false"', 'value="true"', 1) == MIRROR_FIRST_OPEN


def test_escape_khong_double():
    assert escape("a&amp;b") == "a&amp;amp;b"  # dung: & duoc escape 1 lan
    assert unescape(escape('x&<>"y')) == 'x&<>"y'


def test_coerce_bool_chap_nhan_hoa_thuong():
    assert coerce("boolean", "TRUE") == "true"
    assert coerce("boolean", " False ") == "false"


def test_read_va_set_long_moc_throttle():
    assert read_long(SETTINGS_XML, "last_fetch_time_in_millis") == 1781492084614
    out = set_long(SETTINGS_XML, "last_fetch_time_in_millis", 1788519653885)
    assert read_long(out, "last_fetch_time_in_millis") == 1788519653885
    # etag va cac field khac khong duoc doi
    assert "etag-310944273102-firebase-fetch-781665809" in out
    assert read_long(out, "last_template_version") == 232


def test_set_long_khong_co_key_thi_raise():
    with pytest.raises(ValueError, match="last_fetch_time_in_millis"):
        set_long("<map></map>", "last_fetch_time_in_millis", 1)


def test_read_long_khong_co_tra_none():
    assert read_long("<map></map>", "last_fetch_time_in_millis") is None
