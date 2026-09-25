"""Test cham tung dong Expected. Fixture la Expected THAT trong bo TC chung.

Diem phai gac:
  - cham TUNG DONG, verdict case = dong xau nhat
  - case ads cham o tang request/load, KHONG doi nhin thay ad
  - unit co request ma khong fill -> BLOCKED_NO_FILL, KHONG phai FAIL
  - dong khong do duoc -> NOT_VERIFIABLE, khong doan bua thanh PASS
"""

from __future__ import annotations

import pytest

from rcr import assert_check as a

# Do that tren may: case bat banner -> 2 unit request, 1 unit fail No fill
ADS_BANNER = {"units": {
    "banner:*****495": {"type": "banner", "unit": "*****495", "requested": 1,
                        "loaded": 1, "load_failed": 0, "shown": 0, "impressions": 0, "errors": []},
    "banner:*****825": {"type": "banner", "unit": "*****825", "requested": 1,
                        "loaded": 0, "load_failed": 1, "shown": 0, "impressions": 0, "errors": ["No fill."]},
    "interstitial:*****588": {"type": "interstitial", "unit": "*****588", "requested": 1,
                              "loaded": 1, "load_failed": 0, "shown": 1, "impressions": 1, "errors": []},
}}
ADS_NO_BANNER = {"units": {
    "interstitial:*****588": ADS_BANNER["units"]["interstitial:*****588"],
}}
ADS_NO_FILL = {"units": {
    "native:*****394": {"type": "native", "unit": "*****394", "requested": 1,
                        "loaded": 0, "load_failed": 1, "shown": 0, "impressions": 0, "errors": ["No fill."]},
}}
OK_CRASH = {"crashed": False, "lines": []}
NO_DRIVE = {"steps": []}


def check(line, ads=ADS_BANNER, drive=NO_DRIVE, crash=OK_CRASH):
    return a.check(line, ads, drive, crash)


# --- khong crash -------------------------------------------------------------

@pytest.mark.parametrize("line", ["Không crash", "App không crash.", "Luồng FO không bị block, không crash."])
def test_khong_crash_khi_app_khong_crash(line):
    assert check(line)["verdict"] == a.PASS


def test_app_crash_that_thi_FAIL_kem_dong_log():
    out = check("Không crash", crash={"crashed": True, "lines": ["FATAL EXCEPTION: main"]})
    assert out["verdict"] == a.FAIL and "FATAL" in out["actual"][0]


# --- ads: phu dinh -----------------------------------------------------------

def test_khong_load_banner_nao_ma_that_su_khong_co_request():
    """Expected that cua case #4 trong TC SDK 6.4.0."""
    out = check("Không load bất kỳ banner nào", ads=ADS_NO_BANNER)
    assert out["verdict"] == a.PASS and out["actual"]["requested"] == []


def test_khong_load_banner_ma_van_co_request_thi_FAIL_kem_actual():
    out = check("Không load bất kỳ banner nào", ads=ADS_BANNER)
    assert out["verdict"] == a.FAIL
    assert sorted(out["actual"]["requested"]) == ["*****495", "*****825"]


# --- ads: khang dinh ---------------------------------------------------------

def test_inter_show_duoc_thi_PASS():
    assert check("Interstitial hiển thị")["verdict"] == a.PASS


def test_banner_load_duoc_nhung_chua_kip_show_van_PASS():
    """User chot: inter de len truoc khi kip nhin banner - co log load la du."""
    out = check("Banner 101-spl-a-banner-high hiển thị ở bottom Splash")
    assert out["verdict"] == a.PASS and "tầng load" in out["reason"]


def test_co_request_ma_khong_fill_van_tinh_dat():
    """User chot: khong fill la chuyen cua kho quang cao, logic app van dung."""
    out = check("Native 105-spl-n-native hiển thị trên Splash", ads=ADS_NO_FILL)
    assert out["verdict"] == a.PASS and "không trả ad" in out["reason"]


DA_TAP = {"steps": [{"n": 1, "action": {"kind": "tap"}, "activity": "HomeActivity", "dump": ""}]}


def test_khong_co_request_nao_thi_FAIL_khi_da_lai_toi_man():
    out = check("Native hiển thị trên Splash", ads=ADS_NO_BANNER, drive=DA_TAP)
    assert out["verdict"] == a.FAIL


def test_chua_lai_toi_man_nao_thi_khong_ket_toi_app_thieu_ads():
    """Case man Widget: tool van dung o splash -> ads cua man do tat nhien chua request."""
    out = check("Khu vực Ads Banner hiển thị ở dưới chân màn", ads=ADS_NO_BANNER,
                drive={"steps": [{"n": 1, "action": {"kind": "noop"}, "activity": "SplashActivity"}]})
    assert out["verdict"] == a.NEEDS_HUMAN and "chưa lái tới màn nào khác" in out["reason"]


def test_chua_lai_toi_man_nao_thi_khong_ket_toi_app_thieu_nut():
    out = check('Button "Add Widget Now" hiển thị', 
                drive={"steps": [{"n": 1, "action": {"kind": "noop"}, "activity": "SplashActivity",
                                  "dump": "<node text='Splash'/>"}]})
    assert out["verdict"] == a.NEEDS_HUMAN


def test_ma_vi_tri_tra_ra_loai_ad_tu_ten_key_that_cua_app():
    """'Không preload/show 202' - cau khong co chu 'native', tra tu key RC."""
    rc = ("show_202_lfo2_n_native_high", "show_202_lfo2_n_native", "enable_onb3_screen")
    assert a.assert_ads.type_from_position("Không preload/show 202", rc) == "native"
    assert a.assert_ads.type_from_position("Priority 1: 202-high unshown", rc) == "native"
    assert a.assert_ads.type_from_position("App → language_2_4", rc) == ""


# --- chu tren man hinh -------------------------------------------------------

def test_tim_chu_trong_dump_da_chup():
    drive = {"steps": [{"n": 1, "dump": "<node text='Chào mừng'/>", "activity": "Main"}]}
    assert check('Hiển thị chữ "Chào mừng"', drive=drive)["verdict"] == a.PASS


def test_khong_thay_chu_vi_quang_cao_che_thi_de_nguoi_xem_lai():
    drive = {"steps": [{"n": 1, "dump": "<node text='Ad'/>"}], "blocked_steps": [1]}
    out = check('Hiển thị chữ "Chào mừng"', drive=drive)
    assert out["verdict"] == a.NEEDS_HUMAN and "đóng quảng cáo" in out["reason"]


# --- khong do duoc -----------------------------------------------------------

def test_dong_doi_nhin_mat_thi_NOT_VERIFIABLE():
    assert check("UI native ad đúng Design layout1")["verdict"] == a.NOT_VERIFIABLE


def test_ky_vong_khong_co_impression_ma_that_su_khong_co():
    ads = {"units": {"native:*****394": dict(ADS_NO_FILL["units"]["native:*****394"])}}
    out = check("Impressions = 0 (Impressions > 0 = lỗi nặng, ưu tiên fix).", ads=ads)
    assert out["verdict"] == a.PASS


def test_ky_vong_0_impression_ma_van_ban_la_FAIL():
    out = check("Impressions = 0 (Impressions > 0 = lỗi nặng).")
    assert out["verdict"] == a.FAIL


def test_cham_ca_case_lay_dong_xau_nhat():
    out = a.check_all(
        ["Không crash", "Không load bất kỳ banner nào"], ADS_BANNER, NO_DRIVE, OK_CRASH
    )
    assert [l["verdict"] for l in out["lines"]] == [a.PASS, a.FAIL]
    assert out["verdict"] == a.FAIL


# --- khong duoc bao oan khi khong map duoc unit -----------------------------

ADS_NATIVE_KHAC_MAN = {"units": {
    "native:*****394": {"type": "native", "unit": "*****394", "requested": 1, "loaded": 0,
                        "load_failed": 1, "shown": 0, "impressions": 0, "errors": ["No fill."], "rc_keys": []},
}}


def test_phu_dinh_theo_vi_tri_ma_khong_map_duoc_unit_thi_khong_FAIL():
    """Native của màn SAU đang preload, không phải native splash - FAIL là oan."""
    out = check("Không hiển thị native ad trên splash", ads=ADS_NATIVE_KHAC_MAN)
    assert out["verdict"] == a.NOT_VERIFIABLE
    assert "không quy được cho vị trí" in out["reason"]


def test_phu_dinh_BAT_KY_thi_van_FAIL():
    """'Không load bất kỳ banner nào' không giới hạn vị trí - mọi request đều sai."""
    out = check("Không load bất kỳ banner nào", ads=ADS_BANNER)
    assert out["verdict"] == a.FAIL


# --- do them duoc nho log: impression va thu tu preload --------------------

def test_dem_impression_tu_log():
    """"Impression fire dung 1 lan" - dem dong `occurred for ad unit` trong log."""
    out = check("Impression fire đúng 1 lần khi ad show")
    assert out["verdict"] == a.PASS and "1 lần" in out["reason"]


def test_impression_ban_nhieu_lan_la_FAIL():
    ads = {"units": {k: dict(v) for k, v in ADS_BANNER["units"].items()}}
    ads["units"]["interstitial:*****588"]["impressions"] = 3
    out = check("Impression fire đúng 1 lần khi ad show", ads=ads)
    assert out["verdict"] == a.FAIL and "3 lần" in out["reason"]


def test_thu_tu_preload_alternate_doc_tu_log():
    out = check("SDK preload banner 101 theo alternate: high trước, thường sau")
    assert out["verdict"] == a.PASS and "→" in out["reason"]


def test_chi_mot_unit_request_ma_no_cung_khong_fill_la_thieu_alternate():
    """Unit dau khong fill ma SDK khong goi alternate -> sai thiet ke waterfall."""
    ads = {"units": {"banner:*****825": ADS_BANNER["units"]["banner:*****825"]}}
    out = check("SDK preload banner theo alternate: high trước, thường sau", ads=ads)
    assert out["verdict"] == a.FAIL and "không có alternate" in out["reason"]


def test_dong_doi_mo_console_admob_thi_noi_thang_la_ngoai_tam():
    out = check("AdMob console: Requests > 0 cho unit này.")
    assert out["verdict"] == a.NOT_VERIFIABLE and "console" in out["reason"]


def test_dong_ta_UI_man_chua_toi_thi_la_can_nguoi_chu_khong_phai_khong_do_duoc():
    """"Popup Add Widget hien thi" - do duoc, chi la tool chua lai toi man do."""
    drive = {"steps": [{"n": 1, "action": {"kind": "noop"}, "activity": "SplashActivity", "dump": ""}]}
    out = check("Pop-up Add Widget hiển thị", drive=drive)
    assert out["verdict"] == a.NEEDS_HUMAN and "màn cần lái tới" in out["reason"]


def test_ad_khong_show_thi_0_impression_la_dung():
    """"Impression fire dung 1 lan khi ad show" ma ad khong fill -> khong phai loi app."""
    out = check("Impression fire đúng 1 lần khi ad show.", ads=ADS_NO_FILL)
    assert out["verdict"] == a.PASS and "không fill" in out["reason"]


def test_unit_dau_fill_luon_thi_khong_can_alternate():
    ads = {"units": {"banner:*****495": ADS_BANNER["units"]["banner:*****495"]}}
    out = check("SDK preload banner theo alternate: high trước, thường sau", ads=ads)
    assert out["verdict"] == a.PASS and "fill luôn" in out["reason"]


def test_verdict_case_chi_tinh_cac_dong_DO_DUOC():
    """Dong "can nguoi" noi ve gioi han cua tool, khong noi gi ve app."""
    out = a.check_all(
        ["Không crash", "Pop-up Add Widget hiển thị"], ADS_BANNER, NO_DRIVE, OK_CRASH
    )
    assert [l["verdict"] for l in out["lines"]] == [a.PASS, a.NEEDS_HUMAN]
    assert out["verdict"] == a.PASS and out["pending"] == 1


def test_con_FAIL_thi_van_la_FAIL():
    out = a.check_all(
        ["Không load bất kỳ banner nào", "Pop-up Add Widget hiển thị"], ADS_BANNER, NO_DRIVE, OK_CRASH
    )
    assert out["verdict"] == a.FAIL


def test_khong_dong_nao_do_duoc_thi_giu_nguyen_muc_xau_nhat():
    out = a.check_all(["Pop-up Add Widget hiển thị"], ADS_BANNER, NO_DRIVE, OK_CRASH)
    assert out["verdict"] == a.NEEDS_HUMAN and out["measured"] == 0
