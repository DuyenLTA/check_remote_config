import openpyxl

from rcr import tong_hop_sdk


def _xlsx(tmp_path, tabs):
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for ten, rows in tabs.items():
        ws = wb.create_sheet(ten)
        for r in rows:
            ws.append(r)
    f = tmp_path / "tc.xlsx"
    wb.save(f)
    return f


def test_chi_doc_tab_tong_hop_va_giu_vi_tri_cot(tmp_path):
    f = _xlsx(tmp_path, {"TC SDK 3.5.4": [["bo qua"]],
                         "Tổng hợp SDK 3.2.0": [["splash", "inter splash", "LFO1"], [None, None, "305_high"]]})
    tabs = tong_hop_sdk.doc_tabs(f)
    assert list(tabs) == ["3.2.0"]
    assert " |  | 305_high" in tabs["3.2.0"]          # o trong giu vi tri -> biet ad load o cot LFO1


def test_tab_moi_va_tab_doi_thi_canh_bao_ghi_xong_thi_het(tmp_path):
    kho = tmp_path / "kho"
    f = _xlsx(tmp_path, {"Tổng hợp SDK 3.5.0": [["a"]], "Tổng hợp SDK 6.4.0": [["b"]]})
    assert sorted(tong_hop_sdk.so_sanh(f, kho)) == ["moi: 3.5.0", "moi: 6.4.0"]
    tong_hop_sdk.ghi(f, kho)
    assert tong_hop_sdk.so_sanh(f, kho) == []
    f2 = _xlsx(tmp_path, {"Tổng hợp SDK 3.5.0": [["a da sua"]], "Tổng hợp SDK 6.4.0": [["b"]]})
    assert tong_hop_sdk.so_sanh(f2, kho) == ["doi: 3.5.0"]
