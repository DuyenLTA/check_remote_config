"""Test cham tung dong Expected. Fixture la Expected THAT trong bo TC chung.

Diem phai gac:
  - cham TUNG DONG, verdict case = dong xau nhat
  - case ads cham o tang request/load, KHONG doi nhin thay ad
  - unit co request ma khong fill -> PASS kem ghi chu, KHONG phai FAIL
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


# --- khong duoc doi PASS/FAIL khi khong quy duoc trach nhiem ----------------

def test_cau_phu_dinh_co_chu_alternate_khong_phai_cau_ta_thu_tu_preload():
    """"high1: Requests = 0 (OFF khong duoc goi ke ca trong alternate)" - la phu dinh."""
    ads = {"units": {"native:*****394": dict(ADS_NO_FILL["units"]["native:*****394"])}}
    out = check("303-onb3-n-native-high1: Requests = 0 (OFF không được gọi kể cả trong alternate)",
                ads=ads)
    assert out["verdict"] != a.FAIL
    assert "không quy được cho vị trí" in out["reason"]


def test_phu_dinh_ma_unit_map_duoc_ve_key_thi_moi_FAIL():
    ads = {"units": {"interstitial:*****588": dict(
        ADS_BANNER["units"]["interstitial:*****588"], rc_keys=["splash_inter_high_n_id"])}}
    out = check("App KHÔNG request/load inter ad", ads=ads)
    assert out["verdict"] == a.FAIL


def test_phu_dinh_ma_khong_map_duoc_unit_thi_khong_ket_toi_app():
    """Native cua man khac dang preload - khong phai native cua man trong cau."""
    ads = {"units": {"native:*****394": dict(ADS_NO_FILL["units"]["native:*****394"], rc_keys=[])}}
    out = check("App KHÔNG request/load native ad (AdMob Requests = 0)", ads=ads)
    assert out["verdict"] == a.NOT_VERIFIABLE


def test_da_lai_toi_dung_man_thi_cham_that_chu_khong_bao_can_nguoi():
    """Case onboarding khong co buoc tap nao, nhung tool da lai toi dung man."""
    drive = {"walked": True, "steps": [
        {"n": 0, "action": {"kind": "walk"}, "activity": "OnboardingActivity",
         "dump": "<node text='Swipe to Next'/>"}]}
    out = check('Hiển thị chữ "Swipe to Next"', drive=drive)
    assert out["verdict"] == a.PASS


def test_dong_TC_tu_danh_dau_chua_co_spec_thi_khong_cham():
    """"[TBD - spec chua neu]" - cham la cham voi ky vong do nguoi viet TC doan."""
    for line in ("[TBD — spec chưa nêu]: vùng ad hiển thị gì khi cả ad và swipe đều tắt",
                 "Fallback về UI cũ. [Assume — theo pattern config sai]",
                 "Title hiển thị màu default. [Inferred — spec không định nghĩa]"):
        out = check(line)
        assert out["verdict"] == a.NOT_VERIFIABLE and "chưa có spec" in out["reason"]


# --- quy trach nhiem phai DUNG vi tri, khong phai "map duoc ve key bat ky" ---
# Do that 2026-09-25 tren `photoshoot` (bo TC 3.5.0, case #16): unit native duy
# nhat map duoc la `id_301_onb1_n_native` - native cua Onboarding 1 dang preload.
# Tinh no cho `303-onb3-n-native-high1` la bao FAIL cho mot bug khong ton tai.

CAU_303 = "303-onb3-n-native-high1: Requests = 0 (OFF không được gọi kể cả trong alternate/waterfall)."


def _native(rc_keys):
    return {"units": {"native:*****989": dict(
        ADS_NO_FILL["units"]["native:*****394"], unit="*****989", rc_keys=rc_keys)}}


def test_request_cua_vi_tri_KHAC_thi_khong_ket_toi_vi_tri_trong_cau():
    out = check(CAU_303, ads=_native(["id_301_onb1_n_native"]))
    assert out["verdict"] == a.NOT_VERIFIABLE
    assert "id_301_onb1_n_native" in out["reason"]


def test_request_cua_DUNG_vi_tri_trong_cau_thi_FAIL():
    out = check(CAU_303, ads=_native(["id_303_onb3_n_native_high1"]))
    assert out["verdict"] == a.FAIL


def test_high_khong_bi_tinh_nham_cho_high1():
    """`id_303_onb3_n_native_high` khong phai `..._high1` - khac unit, khac ky vong."""
    out = check(CAU_303, ads=_native(["id_303_onb3_n_native_high"]))
    assert out["verdict"] == a.NOT_VERIFIABLE


def test_high1_khong_bi_tinh_nham_cho_high():
    """Chieu nguoc lai: cau noi ve `_high`, unit la `_high1` - van la unit khac."""
    cau = "303-onb3-n-native-high: Requests = 0 (OFF không được gọi)."
    out = check(cau, ads=_native(["id_303_onb3_n_native_high1"]))
    assert out["verdict"] == a.NOT_VERIFIABLE


# --- dong impression phai theo vi tri cua case ------------------------------
# Do that 2026-09-28, case #2/#3/#4 cua bo TC SDK 3.5.0 ban key ro.

EXPECTS_MOT_UNIT = (
    "Ad Native của unit 201-lfo1-n-native-high1 KHÔNG hiển thị tại màn Language 1.",
    "AdMob console: Requests = 0 và Bid requests = 0 cho unit 201-lfo1-n-native-high1.",
    "Impressions = 0 (Impressions > 0 = lỗi nặng, ưu tiên fix).",
    "Luồng FO không bị block, không crash.",
)
# Tren may: unit CO impression deu la vi tri khac, khong unit nao map ve 201.
ADS_VI_TRI_KHAC = {"units": {
    "native:*****271": {"type": "native", "unit": "*****271", "requested": 3, "loaded": 1,
                        "load_failed": 0, "shown": 1, "impressions": 2, "errors": [], "rc_keys": []},
    "interstitial:*****595": {"type": "interstitial", "unit": "*****595", "requested": 1,
                              "loaded": 1, "load_failed": 0, "shown": 1, "impressions": 1,
                              "errors": [], "rc_keys": ["id_102_spl_n_inter_high"]},
}}


def test_dong_impression_khong_dem_impression_cua_vi_tri_khac():
    """Tat MOT unit khong lam ca app het quang cao.

    Cau "Impressions = 0" khong tu nhac ten unit - ten no o dong Expected phia
    tren. Lay vi tri cua ca case thi day dem impression cua moi unit, va mot vi
    tri khac show ad la case bi bao FAIL cho mot bug khong ton tai.
    """
    res = a.check_all(EXPECTS_MOT_UNIT, ADS_VI_TRI_KHAC, NO_DRIVE, OK_CRASH)
    dong = res["lines"][2]
    assert dong["verdict"] == a.NOT_VERIFIABLE
    assert "201_lfo1_n_native_high1" in dong["reason"]
    assert res["verdict"] != a.FAIL


def test_dong_impression_van_FAIL_khi_dung_vi_tri_do_ban():
    """Map dung vi tri cau noi thi van phai FAIL - khong noi long thanh bo qua."""
    ads = {"units": {"native:*****271": dict(
        ADS_VI_TRI_KHAC["units"]["native:*****271"],
        rc_keys=["id_201_lfo1_n_native_high1"])}}
    res = a.check_all(EXPECTS_MOT_UNIT, ads, NO_DRIVE, OK_CRASH)
    assert res["lines"][2]["verdict"] == a.FAIL
    assert res["verdict"] == a.FAIL


def test_case_noi_ve_nhieu_vi_tri_thi_khong_thu_hep_dong_impression():
    """Nhieu vi tri thi lay cai nao cung la doan -> giu cach dem cu."""
    expects = ("Native 201-lfo1-n-native-high1 không hiển thị.",
               "Native 303-onb3-n-native-high2 không hiển thị.",
               "Impressions = 0.")
    res = a.check_all(expects, ADS_VI_TRI_KHAC, NO_DRIVE, OK_CRASH)
    assert res["lines"][2]["verdict"] == a.FAIL


# --- biet ID vi tri thi vang mat la mot ket luan, khong phai mu tit ----------
# Do that 2026-09-28: nap checklist ID ads xong, case tat unit phai ra PASS.

ADS_BIET_ID = {
    "units": ADS_VI_TRI_KHAC["units"],
    # ID cua chinh vi tri dang test CO trong bang -> vang mat la ket luan duoc.
    "positions": ["201_lfo1_n_native_high1", "305_onb5_n_native_high"],
}


def test_vi_tri_da_biet_ID_ma_log_khong_co_unit_nao_thi_la_PASS():
    """Tat unit roi, log khong thay ID do -> dung la 0 request. Ket luan duoc.

    Truoc day van tra NOT_VERIFIABLE vi khong biet ID vi tri nao la vi tri nao,
    nen mot request khong quy duoc VAN CO THE la cua vi tri dang test.
    """
    res = a.check_all(EXPECTS_MOT_UNIT, ADS_BIET_ID, NO_DRIVE, OK_CRASH)
    assert res["lines"][0]["verdict"] == a.PASS       # dong "KHONG hien thi"
    assert res["lines"][2]["verdict"] == a.PASS       # dong "Impressions = 0"
    assert res["verdict"] == a.PASS


def test_khong_biet_ID_vi_tri_thi_van_khong_ket_luan():
    """Khong co `positions` -> giu nguyen NOT_VERIFIABLE, khong doan thanh PASS."""
    res = a.check_all(EXPECTS_MOT_UNIT, ADS_VI_TRI_KHAC, NO_DRIVE, OK_CRASH)
    assert res["lines"][0]["verdict"] == a.NOT_VERIFIABLE
    assert res["lines"][2]["verdict"] == a.NOT_VERIFIABLE


def test_biet_ID_ma_vi_tri_do_van_chay_thi_FAIL():
    """Noi long de bot FAIL oan ma lam tool ngung bat loi that thi con te hon."""
    ads = {"units": {"native:*****684": {
        "type": "native", "unit": "*****684", "requested": 2, "loaded": 1,
        "load_failed": 0, "shown": 1, "impressions": 1, "errors": [],
        "rc_keys": ["id_201_lfo1_n_native_high1"]}},
        "positions": ["201_lfo1_n_native_high1"]}
    res = a.check_all(EXPECTS_MOT_UNIT, ads, NO_DRIVE, OK_CRASH)
    assert res["lines"][0]["verdict"] == a.FAIL
    assert res["verdict"] == a.FAIL


def test_dong_AdMob_console_khong_tinh_la_can_nguoi():
    """Tester khong vao duoc AdMob console - do la viec cua PO.

    Gop chung vao con so "can nguoi" la bao tester di lam mot viec ho khong co
    quyen lam (user chot 28/09/2026).
    """
    res = a.check_all(EXPECTS_MOT_UNIT, ADS_BIET_ID, NO_DRIVE, OK_CRASH)
    console = res["lines"][1]
    assert console["scope"] == "po"
    assert "PO đối soát" in console["reason"]
    assert res["po"] == 1 and res["pending"] == 0
