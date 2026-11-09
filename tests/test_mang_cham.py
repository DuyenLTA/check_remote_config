"""Precondition "ad ve muon": tool lam cham domain quang cao bang proxy, roi KIEM bang log.

AIP872 1.9.0 (05/11/2026): S03-01 "Di qua LFO2 ngay de 202 chua kip show", S04-01 "Roi OB3 truoc khi
303 ve" bi BLOCKED voi ly do "may khong root, khong co proxy" - trong khi repo da co slow_ads_proxy.py.
"""
from __future__ import annotations

import asyncio
import socket
import subprocess
import sys

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
    assert thieu and "không về lần nào" in thieu[0]


def test_khong_bat_duoc_proxy_thi_chua_dat():
    thieu, _ = mang_cham.kiem_dieu_kien([], "ob3", False, "không bật được proxy làm chậm ad (x)")
    assert thieu == ["không bật được proxy làm chậm ad (x)"]


def test_cong_proxy_on_dinh_theo_may_va_khac_nhau_giua_may():
    assert mang_cham.cong_cua("18311FDF60085N") == mang_cham.cong_cua("18311FDF60085N")
    assert mang_cham.cong_cua("18311FDF60085N") != mang_cham.cong_cua("99261FFAZ0077C")


def _gia_proxy(monkeypatch, loi=None):
    da = {"bat": 0, "tat": 0}

    async def bat(client, serial):
        da["bat"] += 1
        if loi:
            raise loi
        return {"cong": 1}

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
    assert da == {"bat": 1, "tat": 1}
    assert recs[0]["verdict"] == "PASS" and "OB3" in recs[0]["mang_cham"]


def test_batch_dieu_kien_chua_dat_thi_blocked(monkeypatch):
    _gia_proxy(monkeypatch)
    monkeypatch.setitem(RUNNABLE["a"], "precondition", "2. Rời OB3 trước khi 303 về.")
    recs = run(monkeypatch, {"a": {"verdict": "FAIL", "runs": [_run("ob3", True) | {"verdict": "FAIL"}]},
                             "b": "PASS", "c": "PASS"})
    assert recs[0]["verdict"] == "BLOCKED"
    assert any("vẫn show ngay ở OB3" in t for t in recs[0]["precondition_thieu"])


def test_batch_throttle_khong_noi_man_thi_pass_chua_duoc_nhan(monkeypatch):
    _gia_proxy(monkeypatch)
    monkeypatch.setitem(RUNNABLE["a"], "precondition", "1. Throttle mạng ≤50kbps.")
    recs = run(monkeypatch, {"a": "PASS", "b": "PASS", "c": "PASS"})
    assert recs[0]["verdict"] == "NEEDS_HUMAN" and "đối chiếu log" in recs[0]["mang_cham"]


def test_batch_khong_bat_duoc_proxy_thi_blocked(monkeypatch):
    _gia_proxy(monkeypatch, RuntimeError("cong ban"))
    monkeypatch.setitem(RUNNABLE["a"], "precondition", "2. Rời OB3 trước khi 303 về.")
    recs = run(monkeypatch, {"a": "PASS", "b": "PASS", "c": "PASS"})
    assert recs[0]["verdict"] == "BLOCKED"
    assert any("không bật được proxy" in t for t in recs[0]["precondition_thieu"])


def test_proxy_that_mo_cong_va_tat_sach():
    """Chay proxy that tren may tinh (khong can may Android): mo duoc cong, tat xong khong con nghe."""
    cong = mang_cham.cong_cua("test-proxy-that")
    proc = subprocess.Popen([mang_cham.PYTHON_GOC, "-I", str(mang_cham.PROXY_SCRIPT), str(cong), "0", "50",
                             mang_cham.AD_HOSTS], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        assert asyncio.run(mang_cham._cho_cong_mo(cong))
    finally:
        proc.terminate()
        proc.wait(timeout=5)
    with socket.socket() as s:
        s.settimeout(0.3)
        assert s.connect_ex(("127.0.0.1", cong)) != 0


def test_preflight_bat_proxy_cham_con_sot():
    from rcr import preflight

    assert preflight.muc_http_proxy("null")["trang_thai"] == preflight.OK
    assert preflight.muc_http_proxy(":0")["trang_thai"] == preflight.OK
    sot = preflight.muc_http_proxy(f"127.0.0.1:{mang_cham.cong_cua('S')}")
    assert sot["trang_thai"] == preflight.LOI and "http_proxy :0" in sot["viec_can_lam"]


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
