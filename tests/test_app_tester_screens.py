"""Doc man App Tester + hop cai Android + Play Protect tu dump that (Pixel 6, 27/10/2026)."""

from __future__ import annotations

from pathlib import Path

import pytest

from rcr import app_tester_screens as s
from rcr.ui_dump import parse_dump

FIX = Path(__file__).parent / "fixtures"


def dump(ten: str):
    return parse_dump((FIX / f"uidump_{ten}.xml").read_text("utf-8"))


@pytest.mark.parametrize("ten, man", [
    ("apptester_list", "danh_sach"),
    ("apptester_detail_download", "chi_tiet"),
    ("apptester_downloading", "chi_tiet"),
    ("apptester_consent", "consent"),
    ("installer_update_dialog", "hop_cai"),
    ("playprotect_scan_recommended", "pp_quet"),
    ("playprotect_scanning", "pp_dang_quet"),
    ("playprotect_looks_safe", "pp_an_toan"),
    ("inter_dismiss_button", "khac"),
])
def test_nhan_man(ten, man):
    assert s.man(dump(ten)) == man


def test_tim_app_theo_bundle_id_khop_chinh_xac():
    nodes = dump("apptester_list")
    assert s.dong_app(nodes, "com.aiheadshot.idphoto.photogenerator").text == \
        "com.aiheadshot.idphoto.photogenerator"
    assert s.dong_app(nodes, "com.aiheadshot.idphoto") is None   # khong khop mot phan


def test_release_moi_co_nut_tai():
    cac = s.cac_ban(dump("apptester_detail_download"))
    moi = cac[0]
    assert (moi["version"], moi["ngay"], moi["loai"], moi["mo_rong"], moi["nut"]) == \
        ("4.3.0 (40)", "Oct 27, 2026 at 3:53 PM", "release", True, "tai")
    assert cac[1]["version"] == "4.2.0 (39)" and cac[1]["nut"] == ""   # dang gap


def test_cung_version_hai_release_phan_biet_bang_note():
    cac = s.cac_ban(dump("apptester_detail_downgrade"))
    r13 = [b for b in cac if b["version"] == "1.3.0 (13)"]
    assert len(r13) == 2 and r13[0]["nut"] == "ha_cap"
    assert "fix bug r1" in r13[0]["note"] and "next-gen" in r13[1]["note"]
    ban, ly_do = s.chon_ban(cac, "1.3.0 (13)", "release")
    assert ban is None and "2 bản release" in ly_do                     # khong chon bua


def test_chon_ban_theo_loai():
    cac = [{"version": "4.3.0 (40)", "loai": "release", "ngay": "a", "note": ""},
           {"version": "4.3.0 (40)", "loai": "debug", "ngay": "b", "note": "debug build"}]
    assert s.chon_ban(cac, "4.3.0 (40)", "debug")[0]["ngay"] == "b"
    assert s.chon_ban(cac[:1], "4.3.0 (40)", "debug") == (None, "4.3.0 (40) chưa có bản debug (mới có: release)")
    assert s.chon_ban(cac, "4.4.0 (41)", "debug") == (None, "App Tester chưa có 4.4.0 (41)")


def test_nut_play_protect_chi_nhan_cua_play_store():
    nodes = dump("playprotect_looks_safe")
    assert s.nut_chu(nodes, "Install", s.PLAY_STORE) is not None
    assert s.nut_chu(nodes, "Install", s.APP_TESTER) is None


def test_dong_bi_cat_o_mep_khong_thanh_release_gia():
    """LingoSpeak 27/10: dong dau mat version, dong cuoi mat note -> ca hai bo qua."""
    cac = s.cac_ban(dump("apptester_detail_row_cut"))
    assert [b["version"] for b in cac] == ["1.9.0 (9)", "1.9.0 (9)", "1.9.0 (9)", "1.8.0 (9)"]
    assert all(b["ngay"] and b["note"] for b in cac)


def test_open_button_ghi_install_la_da_tai_chua_cai():
    """Cancel hop cai -> App Tester doi nut thanh open_button "Install", app chua cai."""
    moi = s.cac_ban(dump("apptester_detail_downloaded"))[0]
    assert (moi["version"], moi["nut"]) == ("4.3.0 (40)", "da_tai")
    assert s.cac_ban(dump("apptester_detail_download"))[0]["nut"] == "tai"
