"""Kiem dieu kien truoc khi chay. Khong can may that, khong tai sheet that."""

from __future__ import annotations

import asyncio

from rcr import ad_units_sheet, app_sandbox, cli_check, preflight, tc_source
from rcr.adb_parsers import AdbError

PKG = "com.ai.app"
MO = ("isKeyguardShowing=false mDreamingLockscreen=false", "mWakefulness=Awake")


class FakeClient:
    def __init__(self, window=MO[0], power=MO[1], cai=True):
        self.window, self.power, self.cai = window, power, cai

    async def shell(self, serial, *args, timeout=None):
        if args[:2] == ("dumpsys", "window"):
            return self.window, "", 0
        if args[:2] == ("dumpsys", "power"):
            return self.power, "", 0
        if args[:2] == ("pm", "path"):
            return ("package:/data/app/base.apk" if self.cai else ""), "", 0
        if args[:2] == ("dumpsys", "package"):
            return "    versionName=1.6.0", "", 0
        return "", "", 0


def _gia(monkeypatch, debuggable=True, co_tab=True, ram=8.0,
         units=("ca-app-pub-4584260126367940/2920391588",), sdk="3.5.3"):
    async def mo_app(client, serial, package):
        return preflight.muc_ads_test(list(units)), sdk

    monkeypatch.setattr(preflight, "_mo_app_mot_lan", mo_app)

    async def detect(client, serial, package):
        if debuggable:
            return app_sandbox.RUN_AS
        raise AdbError("Khong vao duoc\n  run-as: package not debuggable: x\n  su: may khong root")

    monkeypatch.setattr(app_sandbox, "detect_mode", detect)
    monkeypatch.setattr(tc_source, "tai_ve", lambda tc, out: __file__)
    monkeypatch.setattr(ad_units_sheet, "tai",
                        lambda p, o: ({"id_101": "x"}, "1 vị trí") if co_tab
                        else ({}, f"sheet {ad_units_sheet.THIEU_TAB} {p}"))
    monkeypatch.setattr(preflight, "ram_trong_gb", lambda: ram)


def _chay(client):
    return asyncio.run(preflight.chay(client, "S1", PKG, cli_check.TC_MAC_DINH, "."))


def _trang_thai(kq, ten):
    return next(m for m in kq["muc"] if m["ten"] == ten)["trang_thai"]


def test_du_dieu_kien_thi_san_sang(monkeypatch):
    _gia(monkeypatch)
    kq = _chay(FakeClient())
    assert kq["ok"] and all(m["trang_thai"] == "ok" for m in kq["muc"])


def test_ban_release_bao_loi_kem_ly_do_run_as(monkeypatch):
    """23/10/2026 cai nham ban release 3 lan - phai biet TRUOC khi chay."""
    _gia(monkeypatch, debuggable=False)
    kq = _chay(FakeClient())
    m = next(m for m in kq["muc"] if m["ten"] == "Vào được dữ liệu app")
    assert not kq["ok"] and m["trang_thai"] == "loi" and "not debuggable" in m["chi_tiet"]


def test_may_khoa_man_hinh_la_loi(monkeypatch):
    _gia(monkeypatch)
    kq = _chay(FakeClient(window="isKeyguardShowing=true"))
    assert not kq["ok"] and _trang_thai(kq, "Màn hình") == "loi"


def test_chua_cai_app_la_loi(monkeypatch):
    _gia(monkeypatch)
    assert _trang_thai(_chay(FakeClient(cai=False)), "App đã cài") == "loi"


def test_sheet_id_khong_co_tab_cua_app_la_loi(monkeypatch):
    _gia(monkeypatch, co_tab=False)
    kq = _chay(FakeClient())
    assert not kq["ok"] and _trang_thai(kq, "Sheet ID ads") == "loi"


def test_ram_thap_chi_canh_bao_khong_chan(monkeypatch):
    _gia(monkeypatch, ram=1.7)
    kq = _chay(FakeClient())
    assert kq["ok"] and _trang_thai(kq, "RAM máy tính") == "canh_bao"


def test_cli_tra_ma_loi_khi_preflight_khong_dat(monkeypatch, capsys):
    _gia(monkeypatch, debuggable=False)

    class Adb(FakeClient):
        async def devices(self):
            from rcr.adb_parsers import Device
            return [Device("S1", "device")]

    monkeypatch.setattr(cli_check, "AdbClient", lambda _p=None: Adb())
    assert cli_check.main(["--package", PKG, "--preflight"]) == 1


def test_loi_mot_dong_khong_lam_preflight_vo(monkeypatch):
    _gia(monkeypatch)

    async def detect(client, serial, package):
        raise AdbError("Package khong hop le: 'x'")

    monkeypatch.setattr(app_sandbox, "detect_mode", detect)
    kq = _chay(FakeClient())
    assert _trang_thai(kq, "Vào được dữ liệu app") == "loi"


# Do 24/10/2026 (Piclux 2.4.0): native/banner request bang unit test cua Google.
TEST_NATIVE = "ca-app-pub-3940256099942544/2247696110"
THAT_INTER = "ca-app-pub-4584260126367940/2920391588"


def test_build_dung_id_test_cua_google_la_loi(monkeypatch):
    _gia(monkeypatch, units=(TEST_NATIVE, THAT_INTER))
    kq = _chay(FakeClient())
    assert not kq["ok"] and _trang_thai(kq, "Ads dùng ID thật") == "loi"
    muc = next(m for m in kq["muc"] if m["ten"] == "Ads dùng ID thật")
    assert "2247696110" in muc["chi_tiet"] and "ID ads thật" in muc["viec_can_lam"]


def test_chua_thay_request_ads_chi_canh_bao(monkeypatch):
    _gia(monkeypatch, units=())
    kq = _chay(FakeClient())
    assert kq["ok"] and _trang_thai(kq, "Ads dùng ID thật") == "canh_bao"


def test_app_chua_cai_thi_khong_mo_app_kiem_ads(monkeypatch):
    _gia(monkeypatch)
    kq = _chay(FakeClient(cai=False))
    assert all(m["ten"] != "Ads dùng ID thật" for m in kq["muc"])


def test_unit_ads_doc_ca_hai_ten_param():
    events = [
        {"name": "track_ad_request", "params": {"adunitid": TEST_NATIVE}},
        {"name": "ad_load", "params": {"ad_unit_id": THAT_INTER}},
        {"name": "screen_view", "params": {"ad_unit_id": "khong-phai-ads"}},
    ]
    assert preflight.unit_ads(events) == [TEST_NATIVE, THAT_INTER]


def test_sdk_3_7_0_chay_checklist_next_gen_khong_can_sheet_hay_debuggable(monkeypatch):
    _gia(monkeypatch, sdk="3.7.0", debuggable=False, co_tab=False)
    kq = _chay(FakeClient())
    assert kq["nhanh"] == "nextgen" and kq["sdk"] == "3.7.0" and kq["ok"]
    assert _trang_thai(kq, "Vào được dữ liệu app") == "canh_bao"
    assert not any(m["ten"].startswith("Sheet") for m in kq["muc"])


def test_sdk_khac_3_7_0_van_chay_bo_tc(monkeypatch):
    # 3.6.1 = ban "revert next-gen" (tin build AIP882 4.3.0, 27/10/2026) -> bo TC
    for sdk in ("3.5.3", "3.6.0", "3.6.1", "3.6.1-alpha02", "3.7.1", "3.8.0"):
        _gia(monkeypatch, sdk=sdk)
        kq = _chay(FakeClient())
        assert kq["nhanh"] == "tc", sdk
        assert any(m["ten"] == "Sheet testcase" for m in kq["muc"])


def test_khong_doc_duoc_sdk_thi_canh_bao_va_chay_bo_tc(monkeypatch):
    _gia(monkeypatch, sdk="")
    kq = _chay(FakeClient())
    assert kq["nhanh"] == "tc" and _trang_thai(kq, "Bản SDK FO") == "canh_bao"


def test_tham_so_sdk_thang_doc_tu_log(monkeypatch):
    _gia(monkeypatch, sdk="3.5.3")
    kq = asyncio.run(preflight.chay(FakeClient(), "S1", PKG, cli_check.TC_MAC_DINH, ".", "3.7.0"))
    assert kq["nhanh"] == "nextgen"


def test_tin_build_ghi_next_gen_thi_ep_nhanh_checklist(monkeypatch):
    """AIP918 2.4.0 29/10/2026: tutorial 3.7.1-alpha01 + GMA Next-Gen, ban release -> khong duoc roi vao bo TC."""
    _gia(monkeypatch, sdk="3.7.1-alpha01")
    assert _chay(FakeClient())["nhanh"] == "tc"                      # khong ep: giu quy tac chi 3.7.0
    kq = asyncio.run(preflight.chay(FakeClient(), "S1", PKG, cli_check.TC_MAC_DINH, ".", ep_nextgen=True))
    assert kq["nhanh"] == "nextgen" and not any(m["ten"] == "Sheet testcase" for m in kq["muc"])
    assert "theo tin build" in next(m["chi_tiet"] for m in kq["muc"] if m["ten"] == "Bản SDK FO")


def test_la_nextgen_chi_dung_3_7_0():
    from rcr import sdk_probe
    assert sdk_probe.la_nextgen("3.7.0") and sdk_probe.la_nextgen("3.7.0-alpha02")
    assert not any(sdk_probe.la_nextgen(v) for v in ("3.6.1", "3.6.1-alpha02", "3.7.1", "3.7.10", "3.5.3", "", "x"))


class DnsClient(FakeClient):
    def __init__(self, mode, spec):
        super().__init__()
        self.dns = {"private_dns_mode": mode, "private_dns_specifier": spec}

    async def shell(self, serial, *args, timeout=None):
        if args[:3] == ("settings", "get", "global"):
            return self.dns[args[3]] + "\n", "", 0
        return await super().shell(serial, *args, timeout=timeout)


def test_private_dns_chan_ad_con_sot_tu_luot_truoc_la_loi(monkeypatch):
    """Luot chet giua case no-fill (hoac giu splash o muc 5b) de lai DNS chan ads."""
    _gia(monkeypatch)
    for spec in preflight.DNS_CUA_TOOL:
        kq = _chay(DnsClient("hostname", spec))
        assert not kq["ok"] and _trang_thai(kq, "Private DNS") == "loi", spec


def test_private_dns_cua_nguoi_dung_chi_canh_bao(monkeypatch):
    _gia(monkeypatch)
    kq = _chay(DnsClient("hostname", "dns.google"))
    assert kq["ok"] and _trang_thai(kq, "Private DNS") == "canh_bao"


def test_private_dns_tat_hoac_tu_dong_la_ok(monkeypatch):
    _gia(monkeypatch)
    for mode in ("null", "off", "opportunistic"):
        assert _trang_thai(_chay(DnsClient(mode, "null")), "Private DNS") == "ok", mode


def test_con_snapshot_keep_chua_restore_la_loi(monkeypatch, tmp_path):
    """Con snapshot = may giu config da patch; --keep lan nua ghi de mat gia tri goc."""
    _gia(monkeypatch)
    from rcr import rc_snapshot
    rc_snapshot.path_for(tmp_path, PKG, "S1").write_text('{"saved_at": "2026-10-27T10:00:00+0700"}')
    kq = asyncio.run(preflight.chay(FakeClient(), "S1", PKG, cli_check.TC_MAC_DINH, tmp_path))
    muc = next(m for m in kq["muc"] if m["ten"] == "Config đã trả về")
    assert not kq["ok"] and muc["trang_thai"] == "loi"
    assert "2026-10-27T10:00" in muc["chi_tiet"] and "--restore" in muc["viec_can_lam"]


def test_snapshot_cua_may_khac_khong_tinh(monkeypatch, tmp_path):
    _gia(monkeypatch)
    from rcr import rc_snapshot
    rc_snapshot.path_for(tmp_path, PKG, "S2").write_text("{}")
    kq = asyncio.run(preflight.chay(FakeClient(), "S1", PKG, cli_check.TC_MAC_DINH, tmp_path))
    assert kq["ok"] and _trang_thai(kq, "Config đã trả về") == "ok"
