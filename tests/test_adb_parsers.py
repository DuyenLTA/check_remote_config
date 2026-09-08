"""Test parse output adb + regex loc. Thuan ham."""

from __future__ import annotations

from conftest import DEVICES_OUT, PACKAGES_OUT

from rcr.adb_parsers import (
    PACKAGE_RE, SERIAL_RE, find_activate_file, output_error, parse_devices,
    parse_ls, parse_packages,
)


def test_parse_devices_doc_model_va_state():
    ds = parse_devices(DEVICES_OUT)
    assert len(ds) == 2
    assert ds[0].serial == "29301FDH2006K7"
    assert ds[0].model == "Pixel_7"
    assert ds[0].ready
    assert "Pixel_7" in ds[0].label
    assert ds[1].state == "unauthorized"
    assert not ds[1].ready


def test_parse_packages_bo_prefix_va_sort():
    ps = parse_packages(PACKAGES_OUT)
    assert ps == sorted(ps)
    assert "com.ai.videogenerator.photocreator.aiart" in ps


def test_regex_chan_ky_tu_la():
    for bad in ("x; rm -rf /", "com.x && id", "com.x|sh", "com.x`id`", "com.x $(id)", "a b"):
        assert not PACKAGE_RE.fullmatch(bad), bad
    assert PACKAGE_RE.fullmatch("com.ai.videogenerator.photocreator.aiart")
    assert SERIAL_RE.fullmatch("29301FDH2006K7")
    assert SERIAL_RE.fullmatch("emulator-5554")
    assert SERIAL_RE.fullmatch("192.168.1.5:5555")
    assert not SERIAL_RE.fullmatch("x; reboot")


def test_find_activate_chi_nhan_namespace_firebase():
    names = [
        "frc_1:123:android:abc_fireperf_activate.json",
        "frc_1:123:android:abc_firebase_defaults.json",
        "frc_1:123:android:abc_firebase_activate.json",
    ]
    got = find_activate_file(names)
    assert got == ("frc_1:123:android:abc_firebase_activate.json", "1:123:android:abc")


def test_find_activate_khong_co_tra_none():
    assert find_activate_file(["profileInstalled", "generatefid.lock"]) is None


def test_output_error_bat_loi_khi_exit_0():
    """run-as/pm/am bao loi ma van exit 0 -> phai quet output."""
    assert output_error("", "run-as: package not debuggable: com.x")
    assert output_error("Unknown package: com.x", "")
    assert output_error("", "Permission denied")
    assert output_error("ls: files: No such file or directory", "")
    assert output_error("uid=10123(com.x)", "") is None
    assert output_error("", "") is None


def test_parse_ls_bo_dong_loi():
    out = parse_ls("a.json\nb.xml\n")
    assert out == ["a.json", "b.xml"]
