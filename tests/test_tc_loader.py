"""Test doc file testcase. Thuan du lieu, khong can device.

Diem phai gac:
  - map cot theo TEN, khong theo chi so (file du an khac co the them/bo cot)
  - dong nhom / dong trong bi bo, chi dong co so o cot N° la case
  - o trong o Feature/Test Description ke thua dong tren
  - Action/Expected split theo so `1. 2. 3.`
  - thieu sheet / thieu cot -> loi RO, khong parse bua
"""

from __future__ import annotations

import pytest

from rcr.models import RcError
from rcr.tc_loader import parse_rows, split_steps

HEADER = ("N°", "Feature", "Test Description", "Sub-scenario", "Precondition",
          "Test Data", "Action", "Expected Result", "PASS/FAIL")


def rows(*data):
    return [("spec: demo",) + ("",) * 8, HEADER, *data]


def test_bo_dong_nhom_va_dong_trong():
    out = parse_rows(rows(
        ("Nhom A - Config",) + ("",) * 8,
        ("1", "Tab Moment", "Config", "sub 1", "pre", "k_a = false", "1. Mo tab.", "1. An di.", ""),
        ("",) * 9,
        ("tong: 1 case",) + ("",) * 8,
    ))
    assert [c.n for c in out] == ["1"]


def test_ke_thua_feature_va_description():
    out = parse_rows(rows(
        ("1", "Tab Moment", "Config", "s1", "", "k_a = false", "", "", ""),
        ("2", "", "", "s2", "", "k_b = true", "", "", ""),
        ("3", "Tab Explore", "Happy", "s3", "", "k_c = true", "", "", ""),
        ("4", "", "", "s4", "", "k_d = true", "", "", ""),
    ))
    assert [(c.feature, c.description) for c in out] == [
        ("Tab Moment", "Config"),
        ("Tab Moment", "Config"),
        ("Tab Explore", "Happy"),
        ("Tab Explore", "Happy"),
    ]


def test_map_cot_theo_ten_khong_theo_chi_so():
    """File du an khac them cot -> van phai parse dung."""
    hdr = ("STT", "Priority", "Feature", "Test Data", "Precondition", "Action",
           "Expected Result", "Note")
    out = parse_rows([hdr, ("1", "P1", "Tab X", "k_a = false", "pre", "1. Mo.", "1. An.", "n")])
    assert out[0].n == "1"
    assert out[0].test_data == "k_a = false"
    assert out[0].precondition == "pre"
    assert out[0].actions == ("Mo.",)
    assert out[0].expects == ("An.",)


def test_thieu_cot_bat_buoc_thi_bao_loi_ro():
    hdr = ("N°", "Feature", "Sub-scenario")  # thieu Test Data / Action / Expected
    with pytest.raises(RcError) as ei:
        parse_rows([hdr, ("1", "x", "y")], source="demo.xlsx")
    msg = str(ei.value)
    assert "khong tim thay dong header" in msg
    assert "test_data" in msg  # noi ro thieu cot nao


def test_co_header_ma_khong_co_case_thi_bao_loi():
    with pytest.raises(RcError, match="khong co dong case nao"):
        parse_rows(rows(("Nhom A",) + ("",) * 8), source="demo.xlsx")


def test_split_steps_theo_so():
    assert split_steps("1. Mo tab Moment.\n2. Cho tai xong.") == (
        "Mo tab Moment.", "Cho tai xong.")
    assert split_steps("1) Nhan See All.\n2) Quan sat.") == ("Nhan See All.", "Quan sat.")


def test_split_steps_khong_danh_so_thi_ra_mot_buoc():
    assert split_steps("Mo tab Moment roi quan sat") == ("Mo tab Moment roi quan sat",)


def test_split_steps_rong():
    assert split_steps("") == ()
    assert split_steps("   \n  ") == ()


def test_split_steps_giu_nguyen_so_trong_cau():
    """So o GIUA cau khong phai dau buoc - vd 'Nhan lan 2.'"""
    assert split_steps("1. Nhan tieu de lan 2.") == ("Nhan tieu de lan 2.",)


def test_so_khong_phai_case_thi_bo():
    out = parse_rows(rows(
        ("TC-01", "x", "y", "s", "", "k_a = false", "", "", ""),  # khong phai so
        ("2", "x", "y", "s", "", "k_b = false", "", "", ""),
    ))
    assert [c.n for c in out] == ["2"]


def test_label_de_hien_len_ui():
    out = parse_rows(rows(("7", "Tab X", "Config", "doi flag A", "", "k = false", "", "", "")))
    assert out[0].label == "#7 doi flag A"


def test_o_none_khong_lam_vo():
    out = parse_rows([HEADER, ("1", None, None, None, None, "k_a = false", None, None, None)])
    assert out[0].feature == ""
    assert out[0].actions == ()


def test_file_khong_ton_tai():
    from rcr.tc_loader import load

    with pytest.raises(RcError, match="Khong thay file"):
        load("/duong/dan/khong/ton/tai.xlsx")


def test_so_thu_tu_dang_float_tu_google_sheet():
    # Google Sheet export N° thanh 1.0, 2.0 - van phai la case
    out = parse_rows(rows(
        (1.0, "Splash", "y", "s", "", "k_a=false", "", "", ""),
        ("2.0", "", "", "s", "", "k_b=false", "", "", ""),
        (1.5, "", "", "s", "", "k_c=false", "", "", ""),  # khong nguyen -> bo
    ))
    assert [c.n for c in out] == ["1", "2"]


def _xlsx(tmp_path, sheets):
    import openpyxl

    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for name, data in sheets:
        ws = wb.create_sheet(name)
        for r in data:
            ws.append(list(r))
    p = tmp_path / "tc.xlsx"
    wb.save(p)
    return p


def test_load_sheet_ten_tuy_y_lay_sheet_co_header(tmp_path):
    from rcr.tc_loader import load

    p = _xlsx(tmp_path, [
        ("Ghi chu", [("chi la ghi chu",)]),
        ("Trang tính1", rows((1.0, "Splash", "y", "s", "", "k_a=false", "1. Mo app", "1. Thay", ""))),
    ])
    out = load(p)
    assert [c.n for c in out] == ["1"]
    assert out[0].actions == ("Mo app",)


def test_load_uu_tien_sheet_test_cases(tmp_path):
    from rcr.tc_loader import load

    p = _xlsx(tmp_path, [
        ("Khac", rows(("9", "x", "y", "s", "", "k=false", "", "", ""))),
        ("Test Cases", rows(("3", "x", "y", "s", "", "k=false", "", "", ""))),
    ])
    assert [c.n for c in load(p)] == ["3"]


def test_load_khong_sheet_nao_co_header_thi_bao_loi(tmp_path):
    from rcr.tc_loader import load

    p = _xlsx(tmp_path, [("A", [("x",)]), ("B", [("y",)])])
    with pytest.raises(RcError, match="khong sheet nao co dong header"):
        load(p)


def test_sheet_khong_co_cot_test_data_thi_doc_key_o_precondition():
    # Bo TC tu SDK 3.2.0: N°, Feature, ..., Precondition, Action, Expected - khong co Test Data
    header = ("N°", "Feature", "Test Description", "Sub-scenario", "Precondition",
              "Action", "Expected Result", "Actual Result", "PASS/FAIL")
    out = parse_rows([("spec",), header,
                      (1.0, "OB4", "x", "s", "1. enable_onb4_screen=true", "1. Mo app", "1. Thay", "", "")])
    assert out[0].n == "1"
    assert out[0].test_data == ""
    assert out[0].precondition == "1. enable_onb4_screen=true"


def test_thieu_ca_test_data_lan_precondition_thi_bao_loi():
    header = ("N°", "Feature", "Action", "Expected Result")
    with pytest.raises(RcError, match="precondition"):
        parse_rows([header, ("1", "x", "a", "b")])
