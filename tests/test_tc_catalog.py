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


def test_tab_ban_sao_chon_theo_ten_that_giu_khoa_case(tmp_path):
    from rcr import tc_select

    p = workbook(tmp_path, [
        ("TC SDK 3.5.4", sheet("k_goc")),
        ("Bản sao của TC SDK 3.5.4", sheet("k_sao")),
    ])
    pairs, notes = tc_select.read_cases(p, frozenset({"k_goc", "k_sao"}), "", "Bản sao của TC SDK 3.5.4")
    assert [t for t, _ in pairs] == ["TC SDK 3.5.4"]  # khoa `3.5.4#...` trung luot cu
    assert "k_sao" in pairs[0][1].precondition
    assert any("Bản sao" in n for n in notes)
    goc, _ = tc_select.read_cases(p, frozenset(), "", "3.5.4")
    assert "k_goc" in goc[0][1].precondition
    assert tc_catalog.read_tab_ten(p, "TC SDK 3.5.4") is None
    assert tc_catalog.read_tab_ten(p, "Bản sao của TC SDK 9.9.9") is None


def test_workbook_khong_co_tab_tc(tmp_path):
    p = workbook(tmp_path, [("Tổng hợp SDK 3.5.0", [("x",)])])
    with pytest.raises(RcError, match="TC SDK"):
        tc_catalog.read_tabs(p)


def test_tab_rong_khong_lam_hong_ca_workbook(tmp_path):
    """09/11/2026: QA xoa het case tab "TC SDK rating" -> read_tabs nem loi cho CA workbook, tc_select
    tuong file mot sheet va doc sheet dau tien ("TC SDK Next Gen") cho app 3.5.4: 0 case chay duoc."""
    from rcr import tc_select

    p = workbook(tmp_path, [
        ("TC SDK Next Gen", sheet("k_ng")),
        ("TC SDK 3.5.4", sheet("k354")),
        ("TC SDK rating", [("Spec: demo",), HEADER]),     # header co, khong dong case nao
        ("TC SDK 6.4.0", sheet("k_base")),
    ])
    tabs = tc_catalog.read_tabs(p)
    assert [t.name for t in tabs] == ["TC SDK Next Gen", "TC SDK 3.5.4", "TC SDK 6.4.0"]
    assert tc_select.needs_sdk(p)
    chon, ghi_chu = tc_select.read_cases(p, frozenset({"k_ng", "k354", "k_base"}), "3.5.4")
    assert {ten for ten, _ in chon} == {"TC SDK 3.5.4"}


def test_tab_chua_co_header_khong_lam_hong_ca_workbook(tmp_path):
    """09/11/2026: QA vua tao tab "TC SDK 3.6.2" chua dien header -> luot 3.5.4 dung han."""
    p = workbook(tmp_path, [
        ("TC SDK 3.6.2", [("Spec: dang soan",), ("ghi chu",)]),
        ("TC SDK 3.5.4", sheet("k354")),
    ])
    assert [t.name for t in tc_catalog.read_tabs(p)] == ["TC SDK 3.5.4"]


def test_workbook_tc_loi_thi_noi_ra_khong_lui_ve_sheet_dau(tmp_path):
    """Moi tab TC SDK deu rong: dung kem ly do, khong doc sheet dau tien nhu file mot sheet."""
    from rcr import tc_select

    p = workbook(tmp_path, [("TC SDK 3.5.4", [("Spec: demo",), HEADER])])
    with pytest.raises(RcError, match="chua co dong case"):
        tc_select.read_cases(p, frozenset(), "3.5.4")


def test_file_mot_sheet_van_doc_thang(tmp_path):
    from rcr import tc_select

    p = workbook(tmp_path, [("Sheet1", sheet("k1"))])
    assert not tc_select.needs_sdk(p)
    chon, _ = tc_select.read_cases(p, frozenset({"k1"}), "")
    assert len(chon) == 1 and chon[0][0] == ""
