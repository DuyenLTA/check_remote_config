"""Cham checklist SDK Next-Gen bang code: cung log -> cung ket qua, Sai dung cho.

Log that: Sorapix 1.6.0 (SDK FO 3.5.3) tren Pixel 6, 24/10/2026 - FO user moi
(chi giu event quang cao + screen_view + AperoAdmob) va 10 lan mo lanh.
Cac test "khong Sai/Khop gia" tai hien dung input reviewer da chay ra loi.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from rcr import sdk_nextgen_cham, sdk_nextgen_cham_build as B, sdk_nextgen_cham_ev_3a as A
from rcr import sdk_nextgen_cham_ev_3b as C, sdk_nextgen_cham_muc4 as M, sdk_nextgen_events as E, sdk_nextgen_report
from rcr.models import RcError

FIX = Path(__file__).parent / "fixtures"
FO = (FIX / "sdk-nextgen-sorapix-fo.txt").read_text("utf-8")
KHOI_DONG = (FIX / "sdk-nextgen-sorapix-khoi-dong.txt").read_text("utf-8")
PKG = "com.ai.aiimage.aivideogenerator"
PROC = f"10-24 18:00:00.000  1500  1600 I am_proc_start: [0,7000,10557,{PKG},top-activity,{{x}}]"


def _ev(name, t, unit="111", fmt="interstitial", **p):
    key = "ad_unit_id" if name in ("ad_show", "ad_load") else "adunitid"
    body = ", ".join(f"{k}={v}" for k, v in {key: f"ca-app-pub-1/{unit}", "ad_format": fmt, **p}.items())
    m, s = divmod(t, 60)
    return f"10-24 18:{int(m):02d}:{s:06.3f}  100  200 V FA-SVC  : Logging event: origin=app,name={name},params=Bundle[{{{body}}}]"


def _app(tag, msg, t="18:00:01.000"):
    return f"10-24 {t}  7000  7000 D {tag}: {msg}"


def _chuoi(t0=1.0, unit="111", fmt="interstitial", paid=1, matched=1):
    ds = [_ev("track_ad_request", t0, unit, fmt)] + [_ev("track_ad_matched_request", t0 + 0.4, unit, fmt)] * matched
    ds += [_ev("ad_load", t0 + 0.5, unit, fmt, load_status="success", won_ad_source="AdMob", non_won_ad_source=""),
           _ev("ad_show", t0 + 2, unit, fmt, show_status="success")]
    ds += [_ev("paid_ad_impression", t0 + 2.1, unit, fmt, valuemicros="1500", currency="USD", precision="1",
               network="AdMob", ad_platform="admob", ad_source="AdMob")] * paid
    return ds


def _evs(ds):
    return E.doc_events("\n".join(sorted(ds)))


def _ket(rs, ma):
    return next(r for r in rs if r["ma"] == ma)


# ---------- log that ----------

def test_log_that_sorapix_ra_ket_qua_co_dinh():
    ev = E.doc_events(FO)
    chay = lambda: A.tat_ca(ev, E.loc(ev, "ad_load", thanh_cong=False)) + C.tat_ca(ev, [], None, [], False, False)
    ket = {r["ma"]: r["ket"] for r in chay()}
    assert ket == {"EV-01": "KHOP", "EV-02": "KHOP", "EV-03": "KHOP", "EV-04": "KHOP", "EV-05": "KHOP",
                   "EV-06": "DO_TAY", "EV-07": "DO_TAY", "EV-08": "KHOP", "EV-09": "KHOP", "EV-10": "KHOP",
                   "EV-11": "KHOP", "EV-12": "KHONG_AP_DUNG", "EV-13": "KHONG_AP_DUNG", "EV-20": "KHONG_AP_DUNG",
                   "EV-21": "KHONG_AP_DUNG", "EV-22": "KHOP", "EV-23": "KHONG_AP_DUNG", "EV-24": "DO_TAY",
                   "EV-25": "DO_TAY", "EV-26": "DO_TAY", "EV-27": "DO_TAY"}
    assert chay() == chay()  # cham hai lan cung log ra y het


def test_log_that_muc1_va_muc4():
    assert B.muc17(FO)["ket"] == "KHOP" and len(B.muc17(FO)["bang_chung"]) == 4
    assert len(B.chia_lan(KHOI_DONG)) == 10                     # dong `adbd ... log -t RCR_SDK` khong phai moc
    assert B.muc13(KHOI_DONG, PKG)["ket"] == "DO_TAY"           # lib cu khong in queued/ready
    assert B.muc15(KHOI_DONG, PKG)["ket"] == "KHONG_AP_DUNG"    # mediation khong co Meta
    assert M.med01(KHOI_DONG, PKG)["ket"] == "KHOP"
    ev = E.doc_events(FO)
    assert M.ev30(ev)["ket"] == "DO_TAY"                        # may test: valuemicros = 0
    assert M.ev31(ev)["ket"] == "KHOP" and M.hv02(FO)["ket"] == "KHOP"


# ---------- muc 3: Sai dung cho, khong Khop gia ----------

def test_unit_va_dinh_dang_chuan_hoa_qua_ten_param_khac_nhau():
    ev = _evs(_chuoi()).copy()
    ev[0]["params"]["ad_format"] = "INTERSTITIAL"
    assert {E.fmt(e) for e in ev} == {"interstitial"} and {E.unit(e) for e in ev} == {"111"}


def test_show_thieu_paid_la_sai():
    ev = _evs(_chuoi(paid=0))
    assert A.ev05(ev)["ket"] == "SAI" and _ket(C.tat_ca(ev, [], None, [], False, False), "EV-22")["ket"] == "SAI"


def test_matched_ban_hai_lan_la_sai():
    assert A.ev02(_evs(_chuoi(matched=2)))["ket"] == "SAI"


def test_show_va_request_trung_trong_mot_luot_la_sai():
    ds = _chuoi() + [_ev("track_ad_request", 1.1), _ev("ad_show", 3.0, show_status="success")]
    ev = _evs(ds)
    assert A.ev05(ev)["ket"] == "SAI"  # hai show khong duoc dung chung mot paid
    assert _ket(C.tat_ca(ev, [], None, [], False, False), "EV-22")["ket"] == "SAI"


def test_reload_khong_co_request_rieng_la_sai():
    ds = _chuoi() + [_ev("ad_load", 10, load_status="success", won_ad_source="AdMob", non_won_ad_source="")]
    assert A.ev01(_evs(ds))["ket"] == "SAI"


def test_banner_ad_show_ghi_sai_unit_so_voi_paid_la_sai():
    ds = _chuoi(fmt="banner")
    ds[3] = ds[3].replace("ca-app-pub-1/111", "ca-app-pub-1/999")
    assert A.ev05(_evs(ds))["ket"] == "SAI"


def test_precision_chu_va_network_null_la_sai():
    ds = [d.replace("precision=1", "precision=ESTIMATED").replace("network=AdMob", "network=null") for d in _chuoi()]
    r = A.ev08(_evs(ds))
    assert r["ket"] == "SAI" and "precision=ESTIMATED" in r["bang_chung"][0]


def test_value_khong_bang_micros_chia_trieu_la_sai():
    assert A.ev09(_evs(_chuoi() + [_ev("paid_ad_impression_value", 3.1, value="0.15", currency="USD")]))["ket"] == "SAI"
    assert A.ev09(_evs(_chuoi() + [_ev("paid_ad_impression_value", 3.1, value="0.0015", currency="USD")]))["ket"] == "KHOP"


def test_load_status_hoa_va_app_open_hien_sau_fo_dai_khong_sai_oan():
    ds = [d.replace("load_status=success", "load_status=SUCCESS") for d in _chuoi(fmt="app_open")]
    ds = [d.replace("18:00:03", "18:07:03") if "ad_show" in d or "paid" in d else d for d in ds]  # hien sau 7 phut
    assert C.chuoi("EV-25", "x", _evs(ds), "app_open", "do_tay")["ket"] == "KHOP"


def test_error_domain_vang_khong_sai_oan():
    f = _evs([_ev("ad_load", 1, load_status="failed", error_code="3", error_code_name="ERROR_CODE_NO_FILL")])
    assert A.tat_ca(f, f)[3]["ket"] == "KHOP"


def test_offline_loc_dung_loai_va_dung_app():
    tester = "x 7000 7000 E FOR_TESTER_LOAD_FAILURE: INTERSTITIAL - 123 - no net"
    # dong FOR_TESTER cua inter khong lam banner Khop
    assert C.loi_offline("EV-21", "x", [], tester, ("banner",), [], False)["ket"] == "DO_TAY"
    assert C.loi_offline("EV-24", "x", [], tester, ("interstitial",), [], False)["ket"] == "KHOP"
    # "no internet" cua he thong khong phai app chan request
    he_thong = PROC + "\n10-24 18:00:02.000  1000  1100 I ConnectivityService: no internet validated"
    assert not E.chan_khi_offline(he_thong, PKG)
    assert E.chan_khi_offline(PROC + "\n" + _app("AperoAdmob", "MobileAds ready but no internet"), PKG)
    assert C.loi_offline("EV-24", "x", [], "", ("interstitial",), ["FATAL EXCEPTION"], True)["ket"] == "SAI"
    assert C.loi_offline("EV-24", "x", [], "", ("interstitial",), [], True, mang_that_tat=False)["ket"] == "DO_TAY"


# ---------- muc 1 ----------

def test_thu_tu_khoi_tao():
    lan = lambda *ds: "\n".join(["10-24 18:00:00.000  5  5 I RCR_SDK : lan", PROC] + [_app("AperoAdmob", d) for d in ds])
    q, r = "runWhenReady: MobileAds initializing, queued (2)", "MobileAds ready, run 2 pending ad requests"
    assert B.muc13(lan(q, r) + "\n" + lan(r), PKG)["ket"] == "KHOP"
    assert B.muc13(lan(r, q), PKG)["ket"] == "SAI"
    assert B.muc13(lan(q, r, "UninitializedPropertyAccessException"), PKG)["ket"] == "SAI"
    assert B.muc13(lan(q), PKG)["ket"] == "DO_TAY"          # queued ma chua ready trong 10 s: cham hay treo?
    other = lan(q, r).replace("  7000  7000 D", "  9999  9999 D")  # app Apero khac tren may
    assert B.muc13(other, PKG)["ket"] == "DO_TAY"


def test_adapter_meta_theo_description_khi_khong_co_state():
    meta = "Adapter name: com.google.ads.mediation.facebook.FacebookMediationAdapter"
    assert B.muc15(PROC + "\n" + _app("AperoAdmob", meta + ", Description: , Latency: 120"), PKG)["ket"] == "KHOP"
    assert B.muc15(PROC + "\n" + _app("AperoAdmob", meta + ", Description: Initialization failed., Latency: 9"), PKG)["ket"] == "SAI"
    assert B.muc15(PROC + "\n" + _app("AperoAdmob", meta + ", State: COMPLETE"), PKG)["ket"] == "KHOP"


def test_loi_cua_app_khac_va_anr_cu_khong_tinh():
    log = PROC + "\n10-24 18:00:01.000  9999  9999 E AndroidRuntime: java.lang.NoClassDefFoundError: com.other.Foo"
    assert B.muc11(["ads-mobile-sdk.properties"], log, PKG)["ket"] == "KHOP"
    assert E.crash("10-24 18:00:01.000  1  1 I am_anr  : [0,7000,com.other.app,1,x]", PKG) == []
    assert E.crash(f"10-24 18:00:01.000  1  1 I am_anr  : [0,7000,{PKG},1,x]", PKG)


def test_preload_native_khong_lay_native_man_sau_cho_adactivity():
    # doi request 9424989134 len truoc screen_view AdActivity 111 ms (reviewer tai hien Sai gia)
    fo = FO.replace("18:08:51.911", "18:08:51.800")
    assert B.muc17(fo)["ket"] == "KHOP"


def test_sdk_cu_trong_apk_la_sai_min_sdk_chi_cham_lib():
    assert B.muc11(["META-INF/play-services-ads.properties"], "", PKG)["ket"] == "SAI"
    assert B.muc12({"com.apero.moduleads": 24, "com.apero.tutorialsdk.sample": 24})["ket"] == "KHOP"
    assert B.muc12({"com.apero.moduleads": 21, "com.apero.tutorialsdk.sample": 24})["ket"] == "SAI"
    assert B.muc12({"com.apero.moduleads": None, "com.apero.tutorialsdk.sample": 24})["ket"] == "DO_TAY"


# ---------- muc 4 ----------

def test_kt01_mat_mang():
    sau = "\n".join(_chuoi(30))
    assert M.kt01({"offline_roi_splash_s": 3.5, "offline_man": "LanguageActivity"}, "x", sau, PKG)["ket"] == "KHOP"
    assert M.kt01({"offline_roi_splash_s": None, "offline_man": "SplashActivity"}, "x", sau, PKG)["ket"] == "SAI"
    assert M.kt01({"offline_mang_that_tat": False}, "x", sau, PKG)["ket"] == "DO_TAY"
    assert M.kt01({"offline_roi_splash_s": 3.5}, "x", "", PKG)["ket"] == "DO_TAY"


def test_kt02_mang_cham_theo_timeout():
    assert M.kt02({"cham_roi_splash_s": 31.0, "cham_timeout_s": 30, "cham_timeout_key": "splash_timeout"}, "", PKG)["ket"] == "KHOP"
    assert M.kt02({"cham_roi_splash_s": 40.0, "cham_timeout_s": 30}, "", PKG)["ket"] == "SAI"
    assert M.kt02({"cham_roi_splash_s": 58.0}, "", PKG)["ket"] == "KHOP"   # khong khai timeout -> 60 s
    assert M.kt02({"cham_roi_splash_s": None}, "", PKG)["ket"] == "SAI"
    assert M.kt02({}, None, PKG)["ket"] == "DO_TAY"


def test_ump_khong_form_la_ngoai_pham_vi_ev31_lech_nguon_la_sai():
    log = PROC + "\n" + _app("AdsConsentManager", "3: Publisher misconfiguration: no form(s) configured")
    assert {r["ket"] for r in M.kt05_06(log, PKG)} == {"KHONG_AP_DUNG"}
    ds = [d.replace(", ad_source=AdMob", ", ad_source=Meta") if "paid_ad_impression" in d else d for d in _chuoi()]
    assert M.ev31(_evs(ds))["ket"] == "SAI"


def test_hv02_app_open_ngay_sau_inter_la_sai():
    ds = _chuoi() + [_ev("ad_show", 10, "222", "app_open", show_status="success")]
    assert M.hv02("\n".join(sorted(ds)))["ket"] == "SAI"


# ---------- thu muc + cham tay + report ----------

def _thu_muc(tmp_path, muc=("1", "2", "3", "4")):
    (tmp_path / "bang-chung.json").write_text(json.dumps(
        {"package": PKG, "serial": "S1", "muc": list(muc), "apk_files": ["ads-mobile-sdk.properties"], "debuggable": True,
         "demo_min_sdk": {"com.apero.moduleads": 24, "com.apero.tutorialsdk.sample": 24}, "mo_lai_ms": [500, 700],
         "ad_click": {"log-fo.txt": 0}}), "utf-8")
    (tmp_path / "log-fo.txt").write_text(FO, "utf-8")
    (tmp_path / "log-khoi-dong.txt").write_text(KHOI_DONG, "utf-8")
    return tmp_path


def test_cham_thu_muc_cham_tay_cham_lai_va_report(tmp_path):
    d = _thu_muc(tmp_path)
    data = sdk_nextgen_cham.cham_thu_muc(d)
    assert data["ket_qua"] == sdk_nextgen_cham.cham_thu_muc(d)["ket_qua"]
    assert {r["ma"][:2] for r in data["ket_qua"]} >= {"1.", "HT", "EV", "KT", "ME", "CM", "HV", "RG"}
    sdk_nextgen_cham.cham_tay(data, "EV-07", "KHOP", "bấm native test ở OB1: 1 event_user_click_ads …3003051013")
    r = _ket(data["ket_qua"], "EV-07")
    assert r["ket"] == "KHOP" and r["ket_code"] == "DO_TAY" and "đo tay" in r["cham_boi"]
    # cham lai tu log khong xoa dong do tay
    lai = sdk_nextgen_cham.giu_cham_tay(sdk_nextgen_cham.cham_thu_muc(d), data)
    assert _ket(lai["ket_qua"], "EV-07")["ket"] == "KHOP"
    with pytest.raises(RcError):
        sdk_nextgen_cham.cham_tay(data, "EV-07", "PASS", "x")
    with pytest.raises(RcError):
        sdk_nextgen_cham.cham_tay(data, "EV-99", "KHOP", "x")
    html = sdk_nextgen_report.render(data)
    assert "<title>SDK Next-Gen check</title>" in html and 'data-v="todo"' in html and "Mục 4" in html


def test_lai_fo_loi_thi_sai_thanh_do_tay(tmp_path):
    d = _thu_muc(tmp_path, ("3",))
    bc = json.loads((d / "bang-chung.json").read_text("utf-8"))
    (d / "log-fo.txt").write_text("\n".join(_chuoi(paid=0)), "utf-8")
    bc["fo_loi"] = "drive-fo-to-home không tới Home"
    (d / "bang-chung.json").write_text(json.dumps(bc), "utf-8")
    assert all(r["ket"] != "SAI" for r in sdk_nextgen_cham.cham_thu_muc(d)["ket_qua"])


def test_dem_event_quang_cao_trong_log_mo_lanh(tmp_path):
    """RC tat ads (AIP920 1.6.0, 28/10/2026): 10 lan mo lanh khong co event quang cao -> bo luot FO."""
    from rcr import sdk_nextgen_thu_log as T
    co = tmp_path / "co.txt"
    co.write_text("V FA-SVC  : Logging event: origin=app,name=track_ad_request,params=Bundle[{adunitid=1/2}]\n"
                  "V FA-SVC  : Logging event: origin=app,name=ad_load,params=Bundle[{ad_unit_id=1/2}]\n"
                  "V FA-SVC  : Logging event: origin=app,name=adjust_id,params=Bundle[{x=1}]\n", "utf-8")
    khong = tmp_path / "khong.txt"
    khong.write_text("V FA-SVC  : Logging event: origin=app,name=tracking_install_adjust,params=Bundle[{x=1}]\n", "utf-8")
    assert T.dem_ads(co) == 2 and T.dem_ads(khong) == 0
    assert T.dem_ads(tmp_path / "khong-co.txt") == -1          # khong doc duoc -> khong bo FO


def test_bo_luot_fo_thi_dong_dua_vao_fo_thanh_do_tay():
    from rcr.sdk_nextgen_ket import DO_TAY, KHONG_AP_DUNG, KHOP, SAI
    ket = [{"ma": "EV-07", "ket": KHOP, "ly_do": "khong ban trung"},     # Khop vi log FO rong -> khong tin
           {"ma": "HT-03", "ket": SAI, "ly_do": "thieu event"},
           {"ma": "EV-24", "ket": KHOP, "ly_do": "tu luot mat mang"},
           {"ma": "1.1", "ket": KHOP, "ly_do": "tu log mo lanh"},
           {"ma": "EV-12", "ket": KHONG_AP_DUNG, "ly_do": "app khong co"}]
    ra = {r["ma"]: r for r in sdk_nextgen_cham.bo_qua_fo(ket, "bỏ lượt FO")}
    assert ra["EV-07"]["ket"] == DO_TAY and ra["HT-03"]["ket"] == DO_TAY and "bỏ lượt FO" in ra["HT-03"]["ly_do"]
    assert ra["EV-24"]["ket"] == KHOP and ra["1.1"]["ket"] == KHOP and ra["EV-12"]["ket"] == KHONG_AP_DUNG
