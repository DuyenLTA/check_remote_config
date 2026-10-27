"""Tach tin build cua dev: ma app, version, loai ban can cai; ma app -> package qua sheet KT."""

from __future__ import annotations

import openpyxl
import pytest

from rcr import build_ma_app as b

# Hai tin that kenh build 27/10/2026 (bo mention ten nguoi).
TIN_REVERT = ("Bản build AIP882---AI-Video v4.3.0 (40) đã được hoàn thiện. Please check\n"
              "apply tutorial 3.6.1 (revert next-gen)\n"
              "https://drive.google.com/drive/folders/1AbC")
TIN_NEXT_GEN = ("Bản build ADA895-AI-Photoshoot v3.0.0 (22) đã được hoàn thiện. Please check\n"
                "apply next-gen, apply 3.7.0\n"
                "https://drive.google.com/drive/folders/9.9.9")


def test_tin_revert_next_gen_can_ban_debug():
    tin = b.tach(TIN_REVERT)
    assert tin == {"ma": "AIP882", "ten": "AI-Video", "version": "4.3.0 (40)",
                   "next_gen": False, "tutorial": "3.6.1"}
    assert b.loai_ban(tin) == "debug"


def test_tin_apply_next_gen_cai_ban_release():
    tin = b.tach(TIN_NEXT_GEN)
    assert (tin["ma"], tin["version"], tin["next_gen"], tin["tutorial"]) == \
        ("ADA895", "3.0.0 (22)", True, "3.7.0")   # khong lay so trong link
    assert b.loai_ban(tin) == "release"


@pytest.mark.parametrize("ghi_chu, loai", [
    ("", "debug"),                              # khong nhac next-gen -> debug chay duoc moi nhanh
    ("apply tutorial 3.7.0", "release"),        # tutorial 3.7.0 = Next-Gen
    ("apply tutorial 3.6.1", "debug"),
    ("revert next gen, tutorial 3.7.0", "debug"),
])
def test_loai_ban_theo_ghi_chu(ghi_chu, loai):
    tin = b.tach(f"Bản build AIP924---LingoSpeak v1.2.0 (12) đã được hoàn thiện.\n{ghi_chu}")
    assert b.loai_ban(tin) == loai


def test_tin_lech_mau_khong_doan():
    assert b.tach("Build AIP882 4.3.0 xong rồi nha") is None
    assert b.tach("") is None


def test_package_lay_theo_tab_ma_app(tmp_path):
    wb = openpyxl.Workbook()
    wb.active.title = "AIP882"
    wb.active.append(["Package name", "com.aivideogenerator.aiphotoeditor"])
    wb.create_sheet("AIP940").append(["Package name"])          # tab chua dien package
    p = tmp_path / "kt.xlsx"
    wb.save(p)
    assert b.package_cua(p, "aip882") == "com.aivideogenerator.aiphotoeditor"
    assert b.package_cua(p, "AIP940") == ""
    assert b.package_cua(p, "ADA999") == ""


def test_tin_khong_co_ten_app():
    tin = b.tach("@An Duyên @Nancy\nBản build AIP920 v1.6.0 (7) đã được hoàn thiện. ")
    assert (tin["ma"], tin["ten"], tin["version"], b.loai_ban(tin)) == ("AIP920", "", "1.6.0 (7)", "debug")


def test_tin_co_in_dam_markdown():
    """Noi dung tho cua tin chuyen tiep (AIP920, 27/10/2026): ma app boc **."""
    tin = b.tach("<@1476079991161880668> <@1260451147215405152>\nBản build **AIP920** v1.6.0 (7) đã được "
                 "hoàn thiện. Please check\n- apply next-gen, apply 3.7.0\nhttps://drive.google.com/drive/folders/18vg")
    assert (tin["ma"], tin["version"], b.loai_ban(tin)) == ("AIP920", "1.6.0 (7)", "release")
