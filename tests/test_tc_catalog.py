"""Chon bo TC theo ban SDK. Thuan du lieu, khong can device."""

from __future__ import annotations

import pytest

from rcr import tc_catalog
from rcr.models import RcError

HEADER = ("N°", "Feature", "Test Description", "Sub-scenario", "Precondition",
          "Action", "Expected Result", "Actual Result", "PASS/FAIL")


def sheet(key: str):
    return [("Spec: demo",), HEADER, (1.0, "F", "d", "s", f"1. {key} = true", "1. Mo app", "1. Thay", "", "")]


def workbook(tmp_path, tabs):
    import openpyxl

    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for name, rows in tabs:
        ws = wb.create_sheet(name)
        for r in rows:
            ws.append(list(r))
    p = tmp_path / "sdk.xlsx"
    wb.save(p)
    return p


@pytest.fixture
def tabs(tmp_path):
    p = workbook(tmp_path, [
        ("Tổng hợp SDK 3.5.0", [("khong phai TC",)]),
        ("TC SDK 3.5.0", sheet("k35")),
        ("TC SDK rating", sheet("show_rating_placement")),
        ("TC SDK daily checkin", sheet("show_checkin_screen")),
        ("TC SDK 3.2.0", sheet("k32")),
        ("TC SDK 6.4.0", sheet("k_base")),
        ("TC SDK 3.4.0", sheet("k34")),
    ])
    return tc_catalog.read_tabs(p)


WL = frozenset({"k_base", "k32", "k34", "k35", "show_rating_placement"})


def test_sdk_version_tu_log():
    log = "09-24 14:07:44.1 I/VslTemplate4FirstOpenSDK( 3589): Using version 3.5.4-alpha02"
    assert tc_catalog.sdk_version(log) == "3.5.4-alpha02"
    assert tc_catalog.sdk_version("I/VslBilling_SDK_Version( 1): Using version 1.0.0") == ""


def test_phan_loai_tab_theo_ten(tabs):
    kinds = {t.name: t.kind for t in tabs}
    assert kinds["TC SDK 6.4.0"] == "base"
    assert kinds["TC SDK 3.2.0"] == "delta"
    assert kinds["TC SDK rating"] == "feature"


def test_app_3_5_4_lay_base_moi_delta_va_tinh_nang_co_key(tabs):
    chosen, notes = tc_catalog.select(tabs, "3.5.4-alpha02", WL)
    assert [t.name for t in chosen] == ["TC SDK 6.4.0", "TC SDK 3.2.0", "TC SDK 3.4.0",
                                        "TC SDK 3.5.0", "TC SDK rating"]
    assert any("daily checkin" in n for n in notes)  # app khong co key checkin
    assert any("moi hon delta moi nhat" in n for n in notes)


def test_app_3_2_0_chi_lay_base_va_delta_3_2_0(tabs):
    chosen, notes = tc_catalog.select(tabs, "3.2.0", WL)
    assert [t.name for t in chosen if t.kind != "feature"] == ["TC SDK 6.4.0", "TC SDK 3.2.0"]
    assert any("3.4.0" in n and "3.5.0" in n for n in notes)


def test_ban_sdk_khong_doc_duoc_thi_bao_loi(tabs):
    with pytest.raises(RcError, match="ban SDK"):
        tc_catalog.select(tabs, "", WL)


def test_workbook_khong_co_tab_tc(tmp_path):
    p = workbook(tmp_path, [("Tổng hợp SDK 3.5.0", [("x",)])])
    with pytest.raises(RcError, match="TC SDK"):
        tc_catalog.read_tabs(p)
