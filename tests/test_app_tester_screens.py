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
    ("oppo_install_anyway", "oppo_cai"),
    ("inter_dismiss_button", "khac"),
])
def test_nhan_man(ten, man):
    assert s.man(dump(ten)) == man


def test_tim_app_theo_bundle_id_khop_chinh_xac():
    nodes = dump("apptester_list")
    assert s.dong_app(nodes, "com.aiheadshot.idphoto.photogenerator").text == \
        "com.aiheadshot.idphoto.photogenerator"
    assert s.dong_app(nodes, "com.aiheadshot.idphoto") is None   # khong khop mot phan


def test_dong_package_bi_cat_mep_duoi_thi_bam_ten_app():
    """AIP882 29/10/2026 (OPPO CPH2375): dong package cat con 32px o mep duoi, ten app van hien du."""
    n = s.dong_app(dump("apptester_list_cat_mep"), "com.aivideogenerator.aiphotoeditor.beautyeditor.imagetoimage")
    assert n is not None and n.resource_id == "app_name" and n.bounds.top == 1361


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
    assert ly_do == "" and "fix bug r1" in ban["note"]                  # lay lan day moi nhat (3:10 PM)


def test_trung_version_lay_lan_day_moi_nhat_theo_ngay_khong_theo_thu_tu():
    cac = [{"version": "2.2.0 (13)", "loai": "debug", "ngay": "Oct 9, 2026 at 9:05 AM", "note": "debug r1"},
           {"version": "2.3.0 (14)", "loai": "debug", "ngay": "Oct 20, 2026 at 8:00 AM", "note": "debug"},
           {"version": "2.2.0 (13)", "loai": "debug", "ngay": "Oct 9, 2026 at 4:40 PM", "note": "debug r2"},
           {"version": "2.2.0 (13)", "loai": "release", "ngay": "Oct 10, 2026 at 1:00 PM", "note": "release"}]
    assert s.chon_ban(cac, "2.2.0 (13)", "debug")[0]["note"] == "debug r2"
    la = [{"version": "1.0.0 (1)", "loai": "release", "ngay": "?", "note": "tren"},
          {"version": "1.0.0 (1)", "loai": "release", "ngay": "??", "note": "duoi"}]
    assert s.chon_ban(la, "1.0.0 (1)", "release")[0]["note"] == "tren"  # khong doc duoc ngay -> ban tren cung


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


@pytest.mark.parametrize("note, loai", [
    ("1.4.0 (14) - prodDebug\nbranch tutorial-sdk/3.6.1", "debug"),   # AIP805 29/10/2026
    ("devDebug r2", "debug"), ("debug build", "debug"), ("Debug", "debug"),
    ("1.4.0 (14) - prodRelease", "release"), ("ban rls", "release"), ("release build", "release"),
    ("No release notes", "?"), ("fix bug r1", "?"), ("fix debugger crash", "?")])
def test_loai_theo_note_ca_ten_variant(note, loai):
    assert s.loai_theo_note(note) == loai


def _b(loai, ngay, note="n"):
    return {"version": "1.4.0 (14)", "loai": loai, "ngay": ngay, "note": note}


def test_debug_khong_ghi_ro_thi_lay_ban_chua_ro_moi_nhat():
    cac = [_b("?", "Oct 29, 2026 at 10:03 AM", "moi"), _b("release", "Oct 27, 2026 at 10:15 AM"),
           _b("?", "Oct 20, 2026 at 9:00 AM", "cu")]
    assert s.chon_ban(cac, "1.4.0 (14)", "debug")[0]["note"] == "moi"


def test_co_ban_ghi_ro_debug_thi_khong_lay_ban_chua_ro():
    cac = [_b("?", "Oct 29, 2026 at 10:03 AM", "moi"), _b("debug", "Oct 27, 2026 at 10:15 AM", "ro")]
    assert s.chon_ban(cac, "1.4.0 (14)", "debug")[0]["note"] == "ro"


def test_release_van_tinh_ban_chua_ro_nhu_truoc():
    cac = [_b("?", "Oct 29, 2026 at 10:03 AM", "moi"), _b("release", "Oct 27, 2026 at 10:15 AM", "ro"),
           _b("debug", "Oct 29, 2026 at 11:00 AM")]
    assert s.chon_ban(cac, "1.4.0 (14)", "release")[0]["note"] == "moi"
    assert s.chon_ban([_b("debug", "a")], "1.4.0 (14)", "release")[1] == "1.4.0 (14) chưa có bản release (mới có: debug)"


def test_man_quet_cai_cua_oppo_co_nut_install_anyway():
    nodes = dump("oppo_install_anyway")
    assert s.nut_chu(nodes, s.OPPO_CAI, s.OPPO_MARKET).bounds.top == 552


def dump_vi(ten: str, doi: dict[str, str]):
    """Dump that doi chu sang tieng Viet (may de vi-VN, Pixel 7 30/10/2026)."""
    xml = (FIX / f"uidump_{ten}.xml").read_text("utf-8")
    for en, vi in doi.items():
        xml = xml.replace(f'text="{en}"', f'text="{vi}"')
    return parse_dump(xml)


def test_may_tieng_viet_van_nhan_man_play_protect():
    quet = dump_vi("playprotect_scan_recommended", {"Scan app": "Quét ứng dụng"})
    assert s.man(quet) == "pp_quet"
    assert s.nut_chu(quet, s.PP_QUET, s.PLAY_STORE) is not None
    an_toan = dump_vi("playprotect_looks_safe", {"Install": "Cài đặt"})
    assert s.man(an_toan) == "pp_an_toan"
    assert s.nut_chu(an_toan, s.PP_CAI, s.PLAY_STORE) is not None


def test_may_tieng_viet_open_button_cai_dat_la_da_tai():
    moi = s.cac_ban(dump_vi("apptester_detail_downloaded", {"Install": "Cài đặt"}))[0]
    assert moi["nut"] == "da_tai"


def test_ngay_app_tester_tieng_viet():
    assert s._luc_day({"ngay": "thg 10 30, 2026 lúc 3:42 CH"}) == s.datetime(2026, 10, 30, 15, 42)
    assert s._luc_day({"ngay": "thg 10 30, 2026 lúc 12:21 CH"}) == s.datetime(2026, 10, 30, 12, 21)
    assert s._luc_day({"ngay": "thg 10 30, 2026 lúc 12:05 SA"}) == s.datetime(2026, 10, 30, 0, 5)


@pytest.mark.parametrize("ten, doi", [
    ("playprotect_scan_recommended", {}),
    ("playprotect_scan_recommended", {"Scan app": "Quét ứng dụng"}),
    ("playprotect_looks_safe", {"Install": "Cài đặt"}),
    ("oppo_install_anyway", {}),
])
def test_hop_quet_moi_hang_deu_co_nut_chap_nhan(ten, doi):
    n = s.nut_chap_nhan(dump_vi(ten, doi))
    assert n is not None and n.package != s.APP_TESTER


def test_khong_bam_nut_tu_choi():
    nodes = dump("playprotect_looks_safe")
    assert s.nut_chap_nhan(nodes).text == "Install"
