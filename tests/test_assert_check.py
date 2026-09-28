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


def test_dong_console_co_ky_vong_do_duoc_thi_cham_bang_log():
    """"Requests = 0 cho unit X" la thu tool dem duoc trong log.

    So request trong log chinh la so AdMob dem, nen day sang cho nguoi la bo
    mot dong cham duoc (user chot 28/09/2026: phai tu verify het).
    """
    res = a.check_all(EXPECTS_MOT_UNIT, ADS_BIET_ID, NO_DRIVE, OK_CRASH)
    console = res["lines"][1]
    assert console["verdict"] == a.PASS
    assert res["po"] == 0


def test_cau_console_khong_neu_ky_vong_do_duoc_thi_van_la_viec_cua_PO():
    """"Mo console xem doanh thu" khong co con so nao de doi chieu."""
    res = a.check("Mở AdMob console xem báo cáo doanh thu.", ADS_BIET_ID, NO_DRIVE, OK_CRASH)
    assert res["scope"] == "po"


# --- cau phu dinh chung chung -> xet cac vi tri CHINH CASE tat ---------------
# Do that 2026-09-28, case 20: tat 302 va 202, nhung 301/303 van preload cho
# man sau -> luat cu bao FAIL cho mot bug khong ton tai.

EXPECTS_CHUNG = ("App KHÔNG request/load native ad (AdMob Requests = 0).",)
OV_TAT_302 = {"show_302_onb2_n_native_high": "false", "show_302_onb2_n_native": "false",
              "enable_onb2_screen": "true", "swipe_onb2": "true"}


def _ads(keys, positions):
    return {"units": {"native:*****765": {
        "type": "native", "unit": "*****765", "requested": 1, "loaded": 0,
        "load_failed": 1, "shown": 0, "impressions": 0, "errors": [], "rc_keys": keys}},
        "positions": positions}


def test_request_cua_vi_tri_KHAC_khong_lam_case_FAIL():
    """301/303 preload cho man sau la thiet ke, khong phai loi cua case tat 302."""
    ads = _ads(["id_303_onb3_n_native_high"],
               ["302_onb2_n_native_high", "302_onb2_n_native", "303_onb3_n_native_high"])
    res = a.check_all(EXPECTS_CHUNG, ads, NO_DRIVE, OK_CRASH, overrides=OV_TAT_302)
    assert res["lines"][0]["verdict"] == a.PASS
    assert "302_onb2_n_native" in res["lines"][0]["reason"]


def test_request_dung_vi_tri_case_tat_thi_van_FAIL():
    ads = _ads(["id_302_onb2_n_native_high"],
               ["302_onb2_n_native_high", "302_onb2_n_native"])
    res = a.check_all(EXPECTS_CHUNG, ads, NO_DRIVE, OK_CRASH, overrides=OV_TAT_302)
    assert res["lines"][0]["verdict"] == a.FAIL


def test_chua_biet_ID_vi_tri_case_tat_thi_khong_ket_luan():
    ads = _ads(["id_303_onb3_n_native_high"], ["303_onb3_n_native_high"])
    res = a.check_all(EXPECTS_CHUNG, ads, NO_DRIVE, OK_CRASH, overrides=OV_TAT_302)
    assert res["lines"][0]["verdict"] == a.NOT_VERIFIABLE


def test_key_khong_phai_vi_tri_ads_thi_bo_qua():
    """`swipe_onb2`, `enable_onb2_screen` khong co ma 3 so -> khong phai vi tri."""
    from rcr import assert_ads

    assert assert_ads.vi_tri_cua_case(OV_TAT_302) == (
        "302_onb2_n_native", "302_onb2_n_native_high")


# --- dong "chuyen sang man X" do duoc bang activity -------------------------
# Do that 2026-09-28, case 21: truoc day bi xep vao "phai nhin mat" trong khi
# so activity sau buoc cuoi la ra ngay.

def _drive_ket(activity, page=0):
    return {"steps": [{"n": 1, "action": {"kind": "swipe"}}],
            "final": {"activity": activity, "page": page}}


def test_chuyen_sang_man_dung_thi_PASS():
    res = a.check("Chuyển sang màn Onboarding 3.", {}, _drive_ket(
        "aiphoto/VslTemplate4OnboardingActivity", page=3), OK_CRASH)
    assert res["verdict"] == a.PASS and "trang 3" in res["reason"]


def test_dung_o_trang_khac_thi_FAIL():
    res = a.check("Chuyển sang màn Onboarding 3.", {}, _drive_ket(
        "aiphoto/VslTemplate4OnboardingActivity", page=2), OK_CRASH)
    assert res["verdict"] == a.FAIL and "kỳ vọng trang 3" in res["reason"]


def test_dung_o_man_khac_han_thi_FAIL():
    res = a.check("Vào màn Home.", {}, _drive_ket("aiphoto/VslTemplate4OnboardingActivity"), OK_CRASH)
    assert res["verdict"] == a.FAIL


def test_chua_chup_duoc_man_ket_thi_khong_ket_luan():
    res = a.check("Chuyển sang màn Onboarding 3.", {}, {"steps": []}, OK_CRASH)
    assert res["verdict"] == a.NEEDS_HUMAN


def test_dong_ta_phan_tu_UI_khong_bi_cham_thanh_man_hinh():
    """"Icon SWIPE hien thi" o man OB2 van la dong ve ICON, khong phai ve man."""
    drive = {"steps": [{"n": 1, "dump": "<hierarchy />", "action": {"kind": "noop"}}],
             "final": {"activity": "x/VslTemplate4OnboardingActivity", "page": 2}}
    res = a.check("Vùng ad hiển thị icon SWIPE (animated).", {}, drive, OK_CRASH)
    assert "trang" not in res["reason"]


# --- dong doi animation: do bang cach so cac khung da chup ------------------
# Do that 2026-09-28 tren `ob2Bb2SwipeLottie` cua Piclux: khung 1 va khung 3
# trung khit nhau -> chu ky ~1,05 giay.

def _drive_anim(ket):
    return {"steps": [{"n": 1, "dump": '<node resource-id="x:id/ob2Bb2SwipeLottie" />',
                       "anim": {"ob2Bb2SwipeLottie": ket}, "action": {"kind": "noop"}}]}


def test_icon_chuyen_dong_khong_dung_thi_PASS():
    """Animation lap = KHONG dung lai. Khung trung khit nhau la doi hoi sai:

    do that tren may (10 khung cach 0,30s) cap giong nhau nhat van lech 5,5/255
    vi vung crop chua ca anh nen dang doi.
    """
    res = a.check("Icon là animation lặp, gợi ý rõ hướng vuốt ngang.", {},
                  _drive_anim({"doi": True, "lap": True, "lech_max": 19.4,
                               "lech_cuoi": 17.0, "so_khung": 10}), OK_CRASH)
    assert res["verdict"] == a.PASS and "không dừng lại" in res["reason"]


def test_icon_dung_yen_thi_FAIL():
    res = a.check("Icon là animation lặp.", {},
                  _drive_anim({"doi": False, "lap": False, "lech_max": 0.2}), OK_CRASH)
    assert res["verdict"] == a.FAIL and "đứng yên" in res["reason"]


def test_chay_mot_lan_roi_dung_thi_FAIL():
    res = a.check("Icon là animation lặp.", {},
                  _drive_anim({"doi": True, "lap": False, "lech_max": 12.0,
                               "lech_cuoi": 0.3, "so_khung": 10}), OK_CRASH)
    assert res["verdict"] == a.FAIL and "dừng hẳn" in res["reason"]


def test_dong_khong_doi_animation_thi_cham_nhu_phan_tu_thuong():
    """"Icon SWIPE hien thi" chi hoi CO tren man khong, khong hoi no co dong."""
    res = a.check("Icon SWIPE hiển thị.", {},
                  _drive_anim({"doi": False, "lap": False, "lech_max": 0.1}), OK_CRASH)
    assert "đứng yên" not in res["reason"]


# --- dong doi mot event Firebase -------------------------------------------

EV = [{"name": "complete_ob2", "origin": "app", "params": {"engagement_time": "1234"}},
      {"name": "screen_view", "origin": "auto", "params": {}}]


def test_event_co_ban_va_du_param_thi_PASS():
    res = a.check("Log event complete_ob2 (có engagement_time) theo spec nền.",
                  {}, NO_DRIVE, OK_CRASH, events=EV)
    assert res["verdict"] == a.PASS and "complete_ob2" in res["reason"]


def test_event_khong_ban_thi_FAIL_kem_danh_sach_da_ban():
    res = a.check("Log event complete_ob3.", {}, NO_DRIVE, OK_CRASH, events=EV)
    assert res["verdict"] == a.FAIL and "screen_view" in res["reason"]


def test_event_co_ban_nhung_thieu_param_thi_FAIL():
    ev = [{"name": "complete_ob2", "origin": "app", "params": {"ga_event_origin": "app"}}]
    res = a.check("Log event complete_ob2 (có engagement_time).", {}, NO_DRIVE, OK_CRASH, events=ev)
    assert res["verdict"] == a.FAIL and "thiếu param engagement_time" in res["reason"]


def test_khong_co_dong_FA_nao_thi_noi_ro_chu_khong_bao_FAIL():
    """Build tat Analytics thi vang event KHONG phai loi cua app."""
    res = a.check("Log event complete_ob2.", {}, NO_DRIVE, OK_CRASH, events=[])
    assert res["verdict"] == a.NEEDS_HUMAN and "FA-SVC" in res["reason"]


# --- dong "user co the vuot sang man ke" -> chung minh bang cu vuot that -----

def test_vuot_lam_man_doi_thi_PASS():
    drive = {"steps": [], "thu_vuot": {"doi": True, "trang_truoc": 2, "trang_sau": 3}}
    res = a.check("User có thể vuốt sang màn kế tiếp.", {}, drive, OK_CRASH)
    assert res["verdict"] == a.PASS and "trang 2 → 3" in res["reason"]


def test_vuot_ma_man_khong_doi_thi_FAIL():
    drive = {"steps": [], "thu_vuot": {"doi": False, "trang_truoc": 2, "trang_sau": 2}}
    res = a.check("User có thể vuốt sang màn kế tiếp.", {}, drive, OK_CRASH)
    assert res["verdict"] == a.FAIL and "không đổi" in res["reason"]


def test_man_doi_nhung_khong_tien_len_thi_FAIL():
    """Vuot ra man khac ma trang lui lai hoac dung yen -> khong phai "sang man ke"."""
    drive = {"steps": [], "thu_vuot": {"doi": True, "trang_truoc": 3, "trang_sau": 2}}
    res = a.check("User có thể vuốt sang màn kế tiếp.", {}, drive, OK_CRASH)
    assert res["verdict"] == a.FAIL
