"""Doc ID ads tu sheet "Check thong so KT": chon tab theo package, doc cap o theo noi dung."""

from __future__ import annotations

import openpyxl

from rcr import ad_units, ad_units_sheet


def _wb(tmp_path):
    wb = openpyxl.Workbook()
    a = wb.active
    a.title = "AIP916"
    for r in (["Package name", "photomaker.image.editor.ai"], ["2. ID ads FO"],
              ["302-onb2-n-native", "ca-app-pub-1/2409093993"]):
        a.append(r)
    b = wb.create_sheet("ADA895")
    for r in (["Package name", "aiphotogenerator.photoshoot"], ["2. ID ads FO"],
              ["303-onb3-n-native-high1", "ca-app-pub-1/6781981098"],
              ["106_spl_o_native_high1", "ca-app-pub-1/4613476152"],
              ["4. ID ads resume"], ["ca-app-pub-2/3445258314", "501_aoa_high"]):
        b.append(r)
    p = tmp_path / "kt.xlsx"
    wb.save(p)
    return p


def test_chon_tab_theo_package_khong_theo_ten_tab(tmp_path):
    ids = ad_units_sheet.doc_tab(_wb(tmp_path), "aiphotogenerator.photoshoot")
    assert ids == {"id_303_onb3_n_native_high1": "ca-app-pub-1/6781981098",
                   "id_106_spl_o_native_high1": "ca-app-pub-1/4613476152",
                   "id_501_aoa_high": "ca-app-pub-2/3445258314"}


def test_package_khong_co_tab_thi_rong(tmp_path):
    assert ad_units_sheet.doc_tab(_wb(tmp_path), "khong.co.app") == {}


def test_sheet_de_len_yaml_chep_tay(tmp_path, monkeypatch):
    monkeypatch.setitem(ad_units._SHEET, "pkg.a", {"id_302_onb2_n_native": "moi"})
    yaml_p = tmp_path / "u.yaml"
    yaml_p.write_text("pkg.a:\n  id_302_onb2_n_native: cu\n  id_301_onb1_n_native: x\n")
    assert ad_units.cho_package("pkg.a", yaml_p) == {"id_302_onb2_n_native": "moi",
                                                     "id_301_onb1_n_native": "x"}
