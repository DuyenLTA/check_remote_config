"""Precondition "ad ve muon": tool giu mang app theo man (tuong lua Android 13+), roi KIEM bang log.

AIP872 1.9.0 (05/11/2026): S03-01 "Di qua LFO2 ngay de 202 chua kip show", S04-01 "Roi OB3 truoc khi
303 ve" bi BLOCKED. Proxy HTTP khong giu duoc ad (GMA di QUIC); tuong lua theo app cua Android 13+ thi duoc.
"""
from __future__ import annotations

import asyncio

from rcr import mang_cham

from test_run_batch import RUNNABLE, run


def test_nhan_precondition_ad_ve_muon_va_man():
    assert mang_cham.can_lam_cham("2. Đi qua LFO2 ngay khi vào màn để 202 chưa kịp show.") == (True, "lfo2")
    assert mang_cham.can_lam_cham("2. 202 đã load nhưng chưa kịp show ở LFO2.") == (True, "lfo2")
    assert mang_cham.can_lam_cham("2. Rời OB3 trước khi 303-onb3-n-native-high về.") == (True, "ob3")
    assert mang_cham.can_lam_cham("Throttle mạng ≤50kbps") == (True, "")
    assert mang_cham.can_lam_cham("1. Mạng vừa phải để native show sau ~2–3s (vẫn fill).") == (True, "")
    assert mang_cham.can_lam_cham("1. Clear data.") == (False, "")
    assert mang_cham.can_lam_cham("2. Làm 303 no-fill trước khi vào OB3.") == (False, "")


def _run(man_show: str | None, loaded: bool) -> dict:
    events = [{"name": "ob3_view"}]
    if man_show:
        events += [{"name": "ad_show", "params": {"ad_unit_id": "ca-app-pub-1/2764762034"}},
                   {"name": f"{man_show}_view"}]
    unit = {"type": "native", "unit": "*****034", "requested": True, "rc_keys": ["id_303_onb3_n_native_high"], "loaded": loaded,
            "shown": bool(man_show)}
    return {"events": events, "ads": {"units": {"u": unit}}}


def test_dat_khi_ad_co_ve_nhung_khong_show_ngay_tai_man():
    thieu, ghi = mang_cham.kiem_dieu_kien([_run("ob5", True)], "ob3", True)
    assert thieu == [] and "OB3" in ghi


def test_ad_van_show_ngay_tai_man_la_chua_dat():
    thieu, ghi = mang_cham.kiem_dieu_kien([_run("ob3", True)], "ob3", True)
    assert thieu and "vẫn show ngay ở OB3" in thieu[0] and not ghi


def test_ad_khong_ve_lan_nao_khong_phai_ve_muon():
    thieu, _ = mang_cham.kiem_dieu_kien([_run(None, False)], "ob3", True)
    assert thieu and "về lần nào" in thieu[0]


def _run_gop(show_uid: str | None, man_show: str = "ob5") -> dict:
    """Unit `*****034` gop 202 (…2764762034) + 303 (…8588924034): `loaded` cua 202 khong noi gi ve 303."""
    events = [{"name": "lfo2_view"}, {"name": "ob3_view"}]
    if show_uid:
        events += [{"name": "ad_show", "params": {"ad_unit_id": show_uid}}, {"name": f"{man_show}_view"}]
    unit = {"type": "native", "unit": "*****034", "requested": True, "loaded": True, "shown": True,
            "rc_keys": ["id_202_lfo2_n_native_high", "id_303_onb3_n_native_high"],
            "ids": {"id_202_lfo2_n_native_high": ["ca-app-pub-1/2764762034"],
                    "id_303_onb3_n_native_high": ["ca-app-pub-1/8588924034"]}}
    return {"events": events, "ads": {"units": {"u": unit}}}


def test_unit_gop_duoi_id_load_cua_202_khong_tinh_la_303_ve():
    thieu, _ = mang_cham.kiem_dieu_kien([_run_gop("ca-app-pub-1/2764762034", "ob4")], "ob3", True)
    assert thieu and "về lần nào" in thieu[0]


def test_unit_gop_duoi_id_303_show_o_ob5_bang_id_day_du_la_dat():
    thieu, ghi = mang_cham.kiem_dieu_kien([_run_gop("ca-app-pub-1/8588924034")], "ob3", True)
    assert thieu == [] and "OB3" in ghi


def test_khong_bat_duoc_tuong_lua_thi_chua_dat():
    thieu, _ = mang_cham.kiem_dieu_kien([], "ob3", False, "không tạo được điều kiện ad về muộn: x")
    assert thieu == ["không tạo được điều kiện ad về muộn: x"]


class _CuaSoGia:
    """Thay CuaSo that (CuaSo that chay `adb logcat`): ghi lai ke hoach da nhan."""
    tao: list = []

    def __init__(self, client, serial, package, kh):
        self.kh, self.lich = kh, ["12:00:00 chặn mạng: vào LFO2", "12:00:09 trả mạng: rời OB3 sang OB4 (chặn 9s)"]
        _CuaSoGia.tao.append(kh)

    def bat(self):
        pass

    async def tat(self):
        pass


def _gia_proxy(monkeypatch, loi=None):
    from rcr import mang_cham_cua_so
    da = {"bat": 0, "tat": 0, "pkg": []}
    _CuaSoGia.tao = []
    monkeypatch.setattr(mang_cham_cua_so, "CuaSo", _CuaSoGia)

    async def bat(client, serial, package):
        da["bat"] += 1
        da["pkg"].append(package)
        if loi:
            raise loi
        return {"package": package, "chain_cu": False}

    async def tat(client, serial, tt):
        da["tat"] += 1

    monkeypatch.setattr(mang_cham, "bat", bat)
    monkeypatch.setattr(mang_cham, "tat", tat)
    return da


def test_batch_bat_proxy_cho_case_va_luon_go(monkeypatch):
    da = _gia_proxy(monkeypatch)
    monkeypatch.setitem(RUNNABLE["a"], "precondition", "2. Rời OB3 trước khi 303 về.")
    recs = run(monkeypatch, {"a": {"verdict": "PASS", "runs": [_run("ob5", True) | {"verdict": "PASS"}]},
                             "b": "PASS", "c": "PASS"})
    assert (da["bat"], da["tat"]) == (1, 1) and da["pkg"] == ["com.ai.app"]
    assert _CuaSoGia.tao == [{"man": "ob3", "bat_dau": "lfo2", "ids": []}]
    assert recs[0]["verdict"] == "PASS" and "OB3" in recs[0]["mang_cham"] and "chặn 9s" in recs[0]["mang_cham"]


def test_batch_dieu_kien_chua_dat_thi_blocked(monkeypatch):
    _gia_proxy(monkeypatch)
    monkeypatch.setitem(RUNNABLE["a"], "precondition", "2. Rời OB3 trước khi 303 về.")
    recs = run(monkeypatch, {"a": {"verdict": "FAIL", "runs": [_run("ob3", True) | {"verdict": "FAIL"}]},
                             "b": "PASS", "c": "PASS"})
    assert recs[0]["verdict"] == "BLOCKED"
    assert any("vẫn show ngay ở OB3" in t for t in recs[0]["precondition_thieu"])


def test_batch_throttle_khong_noi_man_thi_blocked_khong_bat_tuong_lua(monkeypatch):
    da = _gia_proxy(monkeypatch)
    monkeypatch.setitem(RUNNABLE["a"], "precondition", "1. Throttle mạng ≤50kbps.")
    recs = run(monkeypatch, {"a": "PASS", "b": "PASS", "c": "PASS"})
    assert da["bat"] == 0 and recs[0]["verdict"] == "BLOCKED"
    assert any("băng thông" in t for t in recs[0]["precondition_thieu"])


def test_batch_may_duoi_android_13_thi_blocked(monkeypatch):
    _gia_proxy(monkeypatch, RuntimeError("máy Android API 31 không có tường lửa theo app (cần Android 13+)"))
    monkeypatch.setitem(RUNNABLE["a"], "precondition", "2. Rời OB3 trước khi 303 về.")
    recs = run(monkeypatch, {"a": "PASS", "b": "PASS", "c": "PASS"})
    assert recs[0]["verdict"] == "BLOCKED"
    assert any("cần Android 13+" in t for t in recs[0]["precondition_thieu"])


def test_preflight_bat_proxy_con_sot():
    from rcr import preflight

    assert preflight.muc_http_proxy("null")["trang_thai"] == preflight.OK
    assert preflight.muc_http_proxy(":0")["trang_thai"] == preflight.OK
    sot = preflight.muc_http_proxy("127.0.0.1:18123")
    assert sot["trang_thai"] == preflight.LOI and "http_proxy :0" in sot["viec_can_lam"]


def test_preflight_bat_tuong_lua_con_chan_app():
    from rcr import preflight

    assert preflight.muc_tuong_lua("com.ai.app:allow")["trang_thai"] == preflight.OK
    assert preflight.muc_tuong_lua("UnsupportedOperationException: pre-T")["trang_thai"] == preflight.OK
    sot = preflight.muc_tuong_lua("com.ai.app:deny")
    assert sot["trang_thai"] == preflight.LOI and "networking-enabled true" in sot["viec_can_lam"]


class _AdbGia:
    """Ghi lai lenh tool gui; tra loi nhu Pixel 6 Android 17 (do 09/11/2026)."""

    def __init__(self, sdk="37", chain="chain:disabled"):
        self.sdk, self.chain, self.lenh = sdk, chain, []

    async def shell(self, serial, *args):
        self.lenh.append(" ".join(args))
        if args[:2] == ("getprop", "ro.build.version.sdk"):
            return self.sdk + "\n", "", 0
        if args[-1] == "get-chain3-enabled":
            return self.chain + "\n", "", 0
        if "set-package-networking-enabled" in args:
            bat = "Disabled" if args[3] == "false" else "Enabled"
            return f"{bat} networking for {args[4]}, appId 10593\n", "", 0
        return "", "", 0


def test_tuong_lua_bat_chan_tra_va_tra_chain_ve_cu(monkeypatch):
    monkeypatch.setattr(mang_cham, "guard", lambda *a: None)
    adb = _AdbGia()
    tt = asyncio.run(mang_cham.bat(adb, "S", "com.ai.app"))
    asyncio.run(mang_cham.chan(adb, "S", "com.ai.app", True))
    asyncio.run(mang_cham.tat(adb, "S", tt))
    gms = "com.google.android.gms"     # GMA du phong qua Play services -> chan kem
    assert adb.lenh[2:] == ["cmd connectivity set-chain3-enabled true",
                            "cmd connectivity set-package-networking-enabled true com.ai.app",
                            f"cmd connectivity set-package-networking-enabled true {gms}",
                            "cmd connectivity set-package-networking-enabled false com.ai.app",
                            f"cmd connectivity set-package-networking-enabled false {gms}",
                            "cmd connectivity set-package-networking-enabled true com.ai.app",
                            f"cmd connectivity set-package-networking-enabled true {gms}",
                            "cmd connectivity set-chain3-enabled false"]


def test_tuong_lua_chain_da_bat_san_thi_khong_tat(monkeypatch):
    monkeypatch.setattr(mang_cham, "guard", lambda *a: None)
    adb = _AdbGia(chain="chain:enabled")
    asyncio.run(mang_cham.tat(adb, "S", asyncio.run(mang_cham.bat(adb, "S", "com.ai.app"))))
    assert not any("set-chain3-enabled" in x for x in adb.lenh)


def test_may_android_12_khong_lam_duoc(monkeypatch):
    import pytest

    monkeypatch.setattr(mang_cham, "guard", lambda *a: None)
    with pytest.raises(RuntimeError, match="Android 13"):
        asyncio.run(mang_cham.bat(_AdbGia(sdk="31"), "S", "com.ai.app"))


def test_hai_vi_tri_trung_duoi_tach_bang_id_day_du_cua_ad_show():
    """AIP872 09/11/2026: 202 high …2764762034 va 303 high …8588924034 trung duoi 034, log app gop
    thanh MOT unit. 303 show o OB5 khong duoc tinh la "202 show" hay "ad OB3 show o OB3"."""
    from rcr import assert_ad_screen

    unit = {"type": "native", "unit": "*****034", "requested": 3, "loaded": 3, "shown": 2,
            "rc_keys": ["id_202_lfo2_n_native_high", "id_303_onb3_n_native_high"],
            "ids": {"id_202_lfo2_n_native_high": ["ca-app-pub-4973559944609228/2764762034"],
                    "id_303_onb3_n_native_high": ["ca-app-pub-4973559944609228/8588924034"]}}
    events = [{"name": "ad_show", "params": {"ad_unit_id": "ca-app-pub-4973559944609228/2764762034"}},
              {"name": "lfo2_view"},
              {"name": "ob3_view"},
              {"name": "ad_show", "params": {"ad_unit_id": "ca-app-pub-4973559944609228/8588924034"}},
              {"name": "ob5_view"}]
    shows = assert_ad_screen.show_theo_man(events, [unit])
    assert [(s["man"], s["vi_tri"]) for s in shows] == [("lfo2", {"202"}), ("ob5", {"303"})]
    # 202 show ngay o LFO2 la that; 303 KHONG show o OB3 -> dieu kien "roi OB3 truoc khi 303 ve" dat
    assert assert_ad_screen.ad_man_nha_da_show(events, [unit], "ob3") == []
    assert assert_ad_screen.ad_man_nha_da_show(events, [unit], "lfo2") == ["…034"]


def test_khong_co_id_day_du_thi_giu_cach_cu():
    from rcr import assert_ad_screen

    unit = {"unit": "*****034", "rc_keys": ["id_202_lfo2_n_native_high", "id_303_onb3_n_native_high"]}
    events = [{"name": "ad_show", "params": {"ad_unit_id": "ca-app-pub-1/2764762034"}}, {"name": "ob3_view"}]
    assert assert_ad_screen.show_theo_man(events, [unit])[0]["vi_tri"] == {"202", "303"}


def test_ad_ve_muon_roi_khong_show_tinh_bang_ad_load_id_day_du():
    """303 load sau khi roi OB3 (event `ad_load` ID day du) nhung OB5 khong hien -> van la "da ve muon"."""
    run = _run_gop(None)
    run["events"] += [{"name": "ob4_view"},
                      {"name": "ad_load", "params": {"ad_unit_id": "ca-app-pub-1/8588924034", "load_status": "success"}}]
    thieu, ghi = mang_cham.kiem_dieu_kien([run], "ob3", True)
    assert thieu == [] and "OB3" in ghi


def test_bat_log_fa_tang_buffer_logcat(monkeypatch):
    """FA-SVC verbose lam troi buffer mac dinh: logcat -d cuoi case mat event dau case (Pixel 6 09/11/2026)."""
    from rcr import fa_log

    monkeypatch.setattr(fa_log, "guard", lambda *a: None)
    adb = _AdbGia()
    asyncio.run(fa_log.bat(adb, "S"))
    assert "logcat -G 16M" in adb.lenh


class _AdbChuaCoLuat(_AdbGia):
    """Pixel 6: tra mang cho uid chua co luat -> IllegalStateException 'does not have entry'."""

    async def shell(self, serial, *args):
        if "set-package-networking-enabled" in args and args[3] == "true":
            self.lenh.append(" ".join(args))
            return "", ("java.lang.IllegalStateException: android.os.ServiceSpecificException: "
                        f"sUidOwnerMap does not have entry for uid: 10593 (code 2)"), 0
        return await super().shell(serial, *args)


def test_tra_mang_cho_uid_chua_co_luat_la_thanh_cong(monkeypatch):
    monkeypatch.setattr(mang_cham, "guard", lambda *a: None)
    adb = _AdbChuaCoLuat()
    asyncio.run(mang_cham.tat(adb, "S", asyncio.run(mang_cham.bat(adb, "S", "com.ai.app"))))
    assert adb.lenh[-1] == "cmd connectivity set-chain3-enabled false"


def test_bat_loi_giua_chung_thi_tat_chain_lai(monkeypatch):
    import pytest

    class _Loi(_AdbGia):
        async def shell(self, serial, *args):
            if "set-package-networking-enabled" in args:
                self.lenh.append(" ".join(args))
                return "", "java.lang.SecurityException: nope", 0
            return await super().shell(serial, *args)
    monkeypatch.setattr(mang_cham, "guard", lambda *a: None)
    adb = _Loi()
    with pytest.raises(RuntimeError):
        asyncio.run(mang_cham.bat(adb, "S", "com.ai.app"))
    assert adb.lenh[-1] == "cmd connectivity set-chain3-enabled false"
