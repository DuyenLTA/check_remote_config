"""Test CLI mot luot (`rcr-check`) - khong can cam may.

Diem phai gac:
  - mot may san sang -> khong bat nhap --serial; nhieu may -> BAT BUOC chi dinh
  - mo app di qua `am start -n <component>` do PMS tra ve, KHONG dung monkey
  - phai `force-stop` TRUOC khi mo lai, neu khong app tra config cu trong RAM
  - app fetch de mat patch -> BLOCKED, KHONG phai FAIL
  - mac dinh tra config ve nguyen trang; --keep thi giu
  - --case tro toi case khong chay tu dong duoc -> loi RO, khong chay bua
"""

from __future__ import annotations

import asyncio
import json

import pytest
from conftest import ACTIVATE, PKG, SERIAL, FakeAdb

from rcr import case_run, cli_check, device_app, dex_check, rc_baseline, rc_snapshot, sdk_probe, tc_select
from rcr.adb_parsers import AdbError
from rcr.models import RcError

COMPONENT = f"{PKG}/.MainActivity"
DEVICE_OUT = {
    "resolve-activity": (f"priority=0\n  {COMPONENT}\n", "", 0),
    "dumpsys window": (f"  mCurrentFocus=Window{{4a2 u0 {COMPONENT}}}\n", "", 0),
}


@pytest.fixture
def adb_ui():
    return FakeAdb(fails=dict(DEVICE_OUT))


def baseline_of(adb):
    return asyncio.run(rc_baseline.read(adb, SERIAL, PKG))


def make_xlsx(path, rows):
    import openpyxl

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Test Cases"
    ws.append(("N°", "Feature", "Test Description", "Sub-scenario", "Precondition",
               "Test Data", "Action", "Expected Result", "PASS/FAIL"))
    for r in rows:
        ws.append(r)
    wb.save(path)
    return path


# --- chon may ---------------------------------------------------------------

def test_mot_may_san_sang_thi_khong_can_serial(adb):
    assert asyncio.run(cli_check.pick_serial(adb, None)) == SERIAL


def test_serial_khong_co_tren_may_thi_bao_loi(adb):
    with pytest.raises(AdbError, match="Khong thay may"):
        asyncio.run(cli_check.pick_serial(adb, "khongcothat"))


def test_nhieu_may_thi_bat_buoc_chi_dinh(adb, monkeypatch):
    from rcr.adb_parsers import parse_devices

    two = parse_devices(
        f"List of devices attached\n{SERIAL}  device\n99261FFAZ0077C  device\n"
    )

    async def devices():
        return two

    monkeypatch.setattr(adb, "devices", devices)
    with pytest.raises(AdbError, match="--serial"):
        asyncio.run(cli_check.pick_serial(adb, None))


# --- --set ------------------------------------------------------------------

def test_set_sai_dang_thi_bao_ro():
    with pytest.raises(RcError, match="key=value"):
        cli_check.parse_sets(["enable_onb3_screen"])


def test_set_giu_nguyen_gia_tri_co_dau_bang():
    assert cli_check.parse_sets(["a=x=y"]) == {"a": "x=y"}


# --- chay 1 case ------------------------------------------------------------

def test_apply_case_tat_han_app_roi_moi_mo_lai(adb_ui, tmp_path):
    bl = baseline_of(adb_ui)
    out = asyncio.run(
        case_run.apply_case(adb_ui, bl, {"enable_onb3_screen": "false"}, True, tmp_path)
    )
    assert out["verdict"] == "CONFIG_OK"
    assert out["launch"]["component"] == COMPONENT
    assert out["restored"] is False

    order = [c for c in adb_ui.calls if "force-stop" in c or "am start" in c]
    assert "force-stop" in order[0] and "am start" in order[1]
    # mo bang am start -n, khong phai monkey: monkey ban su kien that vao man hinh
    assert not adb_ui.cmds_with("monkey")


def test_mac_dinh_tra_config_ve_nguyen_trang(adb_ui, tmp_path):
    bl = baseline_of(adb_ui)
    out = asyncio.run(
        case_run.apply_case(adb_ui, bl, {"enable_onb3_screen": "false"}, False, tmp_path)
    )
    assert out["restored"] is True
    assert json.loads(adb_ui.files[f"files/{ACTIVATE}"])["configs_key"] == bl.configs


def test_app_fetch_de_mat_patch_thi_BLOCKED_khong_phai_FAIL(adb_ui, tmp_path):
    """App dat minimumFetchInterval=0 -> mo app la config that de len patch."""
    bl = baseline_of(adb_ui)
    goc = adb_ui.files[f"files/{ACTIVATE}"]
    real_dispatch = adb_ui._dispatch

    def dispatch(cmd):
        res = real_dispatch(cmd)
        if "am start" in cmd:
            adb_ui.files[f"files/{ACTIVATE}"] = goc  # app fetch that, patch bay mat
        return res

    adb_ui._dispatch = dispatch
    out = asyncio.run(
        case_run.apply_case(adb_ui, bl, {"enable_onb3_screen": "false"}, True, tmp_path)
    )
    assert out["verdict"] == "BLOCKED"
    assert out["verify"]["verdict_hint"] == "BLOCKED"


# --- file testcase ----------------------------------------------------------

def test_load_cases_loc_bang_key_that_cua_app(adb, tmp_path):
    bl = baseline_of(adb)
    path = make_xlsx(tmp_path / "tc.xlsx", [
        ("1", "Onb", "Config", "tat onb3", "", "enable_onb3_screen = false", "1. Mo app.", "1. Khong hien.", ""),
        ("2", "Track", "Analytics", "param", "", "source = navigation", "1. Mo app.", "1. Ban event.", ""),
    ])
    rows, runnable, _ = tc_select.load_cases(path, bl)
    assert [r["n"] for r in rows] == ["1", "2"]
    assert runnable["1"]["runs"] == ({"enable_onb3_screen": "false"},)
    # case 2 chi co param analytics -> khong co key RC nao, phai neu ly do
    assert rows[1]["needs_human"]


def test_case_khong_chay_tu_dong_duoc_thi_bao_ro(adb_ui, tmp_path, monkeypatch):
    path = make_xlsx(tmp_path / "tc.xlsx", [
        ("1", "Track", "Analytics", "param", "", "source = navigation", "", "", ""),
    ])
    monkeypatch.setattr(cli_check, "AdbClient", lambda _p=None: adb_ui)
    args = cli_check.build_parser().parse_args(
        ["--package", PKG, "--serial", SERIAL, "--tc", str(path), "--case", "1"]
    )
    # Case khong chay tu dong duoc thi ghi vao report roi di tiep, KHONG nem loi:
    # nem loi la mat sach ket qua cua nhung case da chay xong trong cung luot.
    out = asyncio.run(cli_check.run(args))
    assert out["cases"][0]["verdict"] == "BLOCKED"
    assert "khong chay tu dong duoc" in out["cases"][0]["actual"]


def test_case_can_file_tc(adb_ui, monkeypatch):
    monkeypatch.setattr(cli_check, "AdbClient", lambda _p=None: adb_ui)
    args = cli_check.build_parser().parse_args(["--package", PKG, "--case", "3"])
    with pytest.raises(RcError, match="--tc"):
        asyncio.run(cli_check.run(args))


def test_main_tra_mot_dong_json_va_ma_loi(adb_ui, monkeypatch, capsys):
    monkeypatch.setattr(cli_check, "AdbClient", lambda _p=None: adb_ui)
    code = cli_check.main(["--package", PKG, "--set", "enable_onb3_screen=false", "--no-dex-check"])
    out = capsys.readouterr().out.strip().splitlines()
    assert code == 0 and len(out) == 1
    payload = json.loads(out[0])
    assert payload["run"]["verdict"] == "CONFIG_OK"
    assert payload["baseline"]["package"] == PKG


# --- device_app -------------------------------------------------------------

def test_khong_resolve_duoc_activity_thi_nhac_mo_khoa_may(adb):
    with pytest.raises(AdbError, match="May dang khoa"):
        asyncio.run(device_app.resolve_launcher(adb, SERIAL, PKG))


def test_app_khong_len_foreground_thi_bao_het_gio(adb_ui, monkeypatch):
    monkeypatch.setitem(adb_ui.fails, "dumpsys window",
                        ("  mCurrentFocus=Window{1 u0 com.android.systemui/x.Y}\n", "", 0))
    monkeypatch.setattr(device_app, "POLL_INTERVAL", 0.01)
    with pytest.raises(AdbError, match="khong len foreground"):
        asyncio.run(device_app.wait_foreground(adb_ui, SERIAL, PKG, timeout=0.05))


# --- snapshot: duong ve sau khi giu patch -----------------------------------

def test_giu_patch_thi_luu_snapshot_config_goc(adb_ui, tmp_path):
    bl = baseline_of(adb_ui)
    out = asyncio.run(
        case_run.apply_case(adb_ui, bl, {"enable_onb3_screen": "false"}, True, tmp_path)
    )
    saved = rc_snapshot.load(out["snapshot"])
    assert saved.activate_raw == bl.activate_raw
    assert saved.mirror_raw == bl.mirror_raw


def test_restore_tu_snapshot_tra_ve_dung_gia_tri_goc(adb_ui, tmp_path):
    """Luot sau doc baseline se ra ban DA PATCH - chi snapshot moi biet gia tri that."""
    bl = baseline_of(adb_ui)
    goc = adb_ui.files[f"files/{ACTIVATE}"]
    asyncio.run(case_run.apply_case(adb_ui, bl, {"enable_onb3_screen": "false"}, True, tmp_path))
    assert adb_ui.files[f"files/{ACTIVATE}"] != goc

    asyncio.run(case_run.restore_saved(adb_ui, PKG, SERIAL, tmp_path))
    assert adb_ui.files[f"files/{ACTIVATE}"] == goc
    # xoa sau khi ghi xong: de lai la luot sau restore nham ve ban khong con dung
    assert not rc_snapshot.path_for(tmp_path, PKG, SERIAL).exists()


def test_khong_co_snapshot_thi_bao_ro_chu_khong_restore_bua(adb_ui, tmp_path):
    with pytest.raises(RcError, match="--keep"):
        asyncio.run(case_run.restore_saved(adb_ui, PKG, SERIAL, tmp_path))


# --- bo TC chung: nhieu tab theo ban SDK -------------------------------------

def make_workbook(path, tabs):
    """tabs: {ten_tab: [dong case]}"""
    import openpyxl

    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    header = ("N°", "Feature", "Test Description", "Sub-scenario", "Precondition",
              "Test Data", "Action", "Expected Result", "PASS/FAIL")
    for name, rows in tabs.items():
        ws = wb.create_sheet(name)
        ws.append(header)
        for r in rows:
            ws.append(r)
    wb.save(path)
    return path


def test_workbook_nhieu_tab_ma_thieu_sdk_thi_dung_lai(adb, tmp_path):
    bl = baseline_of(adb)
    path = make_workbook(tmp_path / "bo-chung.xlsx", {
        "TC SDK 6.4.0": [("1", "Onb", "Config", "s1", "", "enable_onb3_screen = false", "1. Mo app.", "1. An.", "")],
        "TC SDK 3.2.0": [("2", "Onb", "Config", "s2", "", "enable_onb2_screen = false", "1. Mo app.", "1. An.", "")],
    })
    with pytest.raises(RcError, match="--sdk"):
        tc_select.load_cases(path, bl)


def test_gia_tri_lua_chon_nhan_ra_thanh_nhieu_luot(adb, tmp_path):
    """`a/b` la "mot trong cac gia tri" -> moi gia tri 1 luot, khong ghi nguyen chuoi."""
    bl = baseline_of(adb)
    path = make_xlsx(tmp_path / "tc.xlsx", [
        ("1", "Onb", "Layout", "s1", "", "enable_onb3_screen = true/false", "1. Mo app.", "1. An.", ""),
    ])
    rows, runnable, _ = tc_select.load_cases(path, bl)
    assert rows[0]["runs"] == 2
    assert runnable["1"]["runs"] == (
        {"enable_onb3_screen": "true"},
        {"enable_onb3_screen": "false"},
    )


# --- do ban SDK tu logcat ----------------------------------------------------

LOG_VERSION = "09-25 15:14:49.109 22063 22063 I VslTemplate4FirstOpenSDK: Using version 3.5.4-alpha02\n"


def test_doc_ban_sdk_tu_logcat_cua_dung_app(adb_ui):
    """App dang chay -> doc log cua RIENG pid do, khong dong cham app."""
    adb_ui.fails["pidof"] = ("22131\n", "", 0)
    adb_ui.fails["logcat"] = (LOG_VERSION, "", 0)
    out = asyncio.run(sdk_probe.detect(adb_ui, SERIAL, PKG))
    assert out == {"version": "3.5.4-alpha02", "source": "logcat cua pid 22131"}
    assert not adb_ui.cmds_with("force-stop")
    # phai loc theo pid: tag nay moi app nhung SDK deu in, logcat thi chung ca may
    assert any("--pid 22131" in c for c in adb_ui.cmds_with("logcat"))


def test_app_khong_chay_thi_mo_lai_chu_khong_doc_buffer_chung(adb_ui, monkeypatch):
    """Khong co pid ma van doc buffer la nhat ban SDK cua APP KHAC."""
    state = {"running": False}
    real = adb_ui._run

    async def run(*args, timeout=None):
        cmd = " ".join(args)
        if "logcat" in cmd and "-c" in args:
            return "", "", 0
        if "logcat" in cmd:
            return (LOG_VERSION if state["running"] else ""), "", 0
        return await real(*args, timeout=timeout)

    real_shell = adb_ui.shell

    async def shell(serial, *args, timeout=None):
        if args and args[0] == "pidof":
            return ("22131\n" if state["running"] else "", "", 0)
        if args and args[0] == "am" and args[1] == "start":
            state["running"] = True
        return await real_shell(serial, *args, timeout=timeout)

    monkeypatch.setattr(adb_ui, "_run", run)
    monkeypatch.setattr(adb_ui, "shell", shell)
    out = asyncio.run(sdk_probe.detect(adb_ui, SERIAL, PKG))
    assert out["version"] == "3.5.4-alpha02"
    assert "mo lai app" in out["source"]


def test_lay_dong_moi_nhat_khong_phai_dong_dau():
    """App vua nang cap thi dong cu van con trong buffer."""
    two = LOG_VERSION.replace("3.5.4-alpha02", "3.4.0") + LOG_VERSION
    assert sdk_probe.last_version(two) == "3.5.4-alpha02"


def test_app_khong_co_tag_sdk_thi_chi_cach_lam_tay(adb_ui, monkeypatch):
    adb_ui.fails["pidof"] = ("22131\n", "", 0)
    monkeypatch.setattr(sdk_probe, "WAIT_AFTER_LAUNCH", 0.02)
    monkeypatch.setattr(sdk_probe, "POLL_INTERVAL", 0.01)
    with pytest.raises(AdbError, match="--sdk"):
        asyncio.run(sdk_probe.detect(adb_ui, SERIAL, PKG))


def test_nhan_ra_file_nao_can_sdk(adb, tmp_path):
    chung = make_workbook(tmp_path / "chung.xlsx", {
        "TC SDK 6.4.0": [("1", "Onb", "C", "s1", "", "enable_onb3_screen = false", "1. Mo.", "1. An.", "")],
    })
    rieng = make_xlsx(tmp_path / "rieng.xlsx", [
        ("1", "Onb", "C", "s1", "", "enable_onb3_screen = false", "1. Mo.", "1. An.", ""),
    ])
    assert tc_select.needs_sdk(chung) is True
    assert tc_select.needs_sdk(rieng) is False


# --- chan bang DEX truoc khi ton mot luot mo app -----------------------------

def test_app_khong_doc_key_thi_KEY_NOT_USED_va_khong_mo_app(adb_ui, monkeypatch, capsys):
    """Key co trong config Firebase KHAC voi app doc key do - cham tiep la PASS gia."""
    async def check(client, serial, package, keys, cache_dir):
        return {k: False for k in keys}

    monkeypatch.setattr(dex_check, "check", check)
    monkeypatch.setattr(cli_check, "AdbClient", lambda _p=None: adb_ui)
    code = cli_check.main(["--package", PKG, "--set", "enable_onb3_screen=false"])
    out = json.loads(capsys.readouterr().out.strip())
    assert code == 0
    assert out["run"]["verdict"] == "KEY_NOT_USED"
    assert out["run"]["keys_not_used"] == ["enable_onb3_screen"]
    assert out["run"]["runs"] == []
    # khong dong vao may: khong tat app, khong ghi file
    assert not adb_ui.cmds_with("force-stop") and not adb_ui.cmds_with("push")


def test_app_co_doc_key_thi_chay_binh_thuong(adb_ui, monkeypatch, capsys):
    async def check(client, serial, package, keys, cache_dir):
        return {k: True for k in keys}

    monkeypatch.setattr(dex_check, "check", check)
    monkeypatch.setattr(cli_check, "AdbClient", lambda _p=None: adb_ui)
    code = cli_check.main(["--package", PKG, "--set", "enable_onb3_screen=false"])
    assert code == 0
    assert json.loads(capsys.readouterr().out.strip())["run"]["verdict"] == "CONFIG_OK"


# --- so case trung nhau giua cac tab ----------------------------------------

def test_so_case_trung_giua_cac_tab_thi_khong_de_len_nhau(adb, tmp_path):
    """Bo chung that: so `1` co o 5 tab. Lay so lam khoa la mat case im lang."""
    bl = baseline_of(adb)
    row = ("1", "Onb", "C", "s", "", "enable_onb3_screen = false", "1. Mo app.", "1. An.", "")
    path = make_workbook(tmp_path / "chung.xlsx", {
        "TC SDK 6.4.0": [row],
        "TC SDK 3.2.0": [row],
    })
    rows, runnable, _ = tc_select.load_cases(path, bl, tab="3.2.0")
    assert list(runnable) == ["3.2.0#1"]
    # khoa co ten tab nen khong de len case cung so o tab khac
    rows2, runnable2, _ = tc_select.load_cases(path, bl, tab="6.4.0")
    assert list(runnable2) == ["6.4.0#1"]


def test_go_so_mo_ho_thi_dung_lai_chu_khong_chay_bua():
    runnable = {"6.4.0#1": {}, "3.2.0#1": {}, "3.3.0#7": {}}
    assert tc_select.pick(runnable, "7") == "3.3.0#7"        # chi co mot tab -> ro rang
    assert tc_select.pick(runnable, "6.4.0#1") == "6.4.0#1"  # go day du
    with pytest.raises(RcError, match="nhieu tab"):
        tc_select.pick(runnable, "1")
    with pytest.raises(RcError, match="khong ton tai"):
        tc_select.pick(runnable, "99")


def test_chi_chay_dung_tab_duoc_neu_ten(adb, tmp_path):
    """Neu dich danh ban SDK thi chay them tab khac la mat thoi gian tren may that."""
    bl = baseline_of(adb)
    row = ("1", "Onb", "C", "s", "", "enable_onb3_screen = false", "1. Mo app.", "1. An.", "")
    path = make_workbook(tmp_path / "chung.xlsx", {
        "TC SDK 6.4.0": [row], "TC SDK 3.2.0": [row], "TC SDK 3.4.0": [row],
    })
    rows, runnable, notes = tc_select.load_cases(path, bl, tab="3.4.0")
    assert [r["tab"] for r in rows] == ["TC SDK 3.4.0"]
    assert list(runnable) == ["3.4.0#1"] and "Chỉ chạy tab" in notes[0]


def test_go_ten_tab_khong_co_thi_liet_ke_tab_that(adb, tmp_path):
    bl = baseline_of(adb)
    path = make_workbook(tmp_path / "chung.xlsx", {
        "TC SDK 6.4.0": [("1", "Onb", "C", "s", "", "enable_onb3_screen = false", "1. Mo.", "1. An.", "")],
    })
    with pytest.raises(RcError, match="Tab co trong file"):
        tc_select.load_cases(path, bl, tab="9.9.9")


def test_sdk_rieng_khong_thuoc_luong_FO_thi_goi_theo_ten(adb, tmp_path):
    """"sdk rating" / "sdk widget" - SDK rieng, goi dich danh ten tab."""
    bl = baseline_of(adb)
    row = ("1", "Rating", "Popup", "s", "", "enable_onb3_screen = false", "1. Mo app.", "1. An.", "")
    path = make_workbook(tmp_path / "chung.xlsx", {
        "TC SDK 3.5.0": [row], "TC SDK rating": [row], "TC SDK widget": [row],
    })
    rows, runnable, notes = tc_select.load_cases(path, bl, tab="rating")
    assert {r["tab"] for r in rows} == {"TC SDK rating"}
    assert list(runnable) == ["rating#1"]
    # goi ten tab thi KHONG do ban SDK First Open - SDK rieng khong lien quan
    assert "Chỉ chạy tab" in notes[0]
