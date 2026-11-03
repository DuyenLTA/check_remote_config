"""Dong Expected ads nhieu vi tri / ca ve khang dinh lan phu dinh - bo TC 3.6.1 tren AIP936 1.9.0
(02/11/2026). Truoc day ve phu dinh bi ap len vi tri dau cau -> FAIL oan."""

from __future__ import annotations

from rcr import assert_check as a
from rcr.assert_ad_nhieu_ve import ma_vi_tri

OK_CRASH = {"crashed": False, "lines": []}
DRIVE = {"walked": True, "steps": [{"n": 1, "dump": "", "activity": "OnboardingActivity"}]}


def _u(duoi, *keys, req=1, load=0, show=0, kind="native"):
    return {"unit": f"*****{duoi}", "type": kind, "requested": req, "loaded": load, "shown": show,
            "impressions": 0, "rc_keys": list(keys)}


def _ads(*units):
    return {"units": {u["unit"]: u for u in units},
            "positions": sorted({k[3:] for u in units for k in u["rc_keys"]})}


def _check(line, ads, cfg=None):
    return a.check(line, ads, DRIVE, OK_CRASH, (), "", (), (), cfg or {})


LUONG = _ads(_u("658", "id_301_onb1_n_native_high", req=2),
             _u("546", "id_202_lfo2_n_native_high", req=3),
             _u("633", "id_301_onb1_o_native_high", "id_302_onb2_n_native_high"),
             _u("475", "id_105_spl_n_native_high"),
             _u("186", "id_102_spl_n_inter_high", kind="interstitial"),
             _u("814", "id_201_lfo1_n_native_high"),
             _u("440", "id_501_aoa_high", req=0, load=1, show=1, kind="app_open"))


def test_mo_duoi_viet_tat():
    assert ma_vi_tri("301-onb1-n-native-high/high1/high2/native") == [
        "301_onb1_n_native_high", "301_onb1_n_native_high1", "301_onb1_n_native_high2", "301_onb1_n_native"]
    assert ma_vi_tri("fill 100% trong ~10s, không có loadAd 301") == ["301"]


def test_khang_dinh_301_va_phu_dinh_show_202_cham_rieng():
    ket = _check("Native 301-onb1-n-native-high hiển thị, không show 202-lfo2-n-native-high.", LUONG)
    assert ket["verdict"] == a.PASS, ket
    assert "301_onb1_n_native_high" in ket["reason"] and "202_lfo2_n_native_high` không show" in ket["reason"]


def test_phu_dinh_show_cua_vi_tri_dang_bat_chi_xet_show():
    assert _check("Không show 202-lfo2-n-native-high.", LUONG)["verdict"] == a.PASS
    hien = _ads(_u("546", "id_202_lfo2_n_native_high", load=1, show=1), _u("658", "id_301_onb1_n_native_high"))
    assert _check("Không show 202-lfo2-n-native-high.", hien)["verdict"] == a.FAIL


def test_phu_dinh_show_cua_vi_tri_case_tat_van_xet_request():
    tat = {"show_202_lfo2_n_native_high": "false"}
    assert _check("Không show 202-lfo2-n-native-high.", LUONG, tat)["verdict"] == a.FAIL


def test_ve_khong_show_ad_resume_xet_unit_50x():
    ket = _check("Sau khi mở lại: reload 301-onb1-n-native-high đúng vùng native, không show ad resume.", LUONG)
    assert ket["verdict"] == a.FAIL and "501" in ket["reason"]


def test_logcat_load_liet_ke_nhieu_vi_tri():
    line = "Logcat load tại Splash: 105-spl-n-native-high, 102-spl-n-inter-high, 201-lfo1-n-native-high."
    assert _check(line, LUONG)["verdict"] == a.PASS
    thieu = "Logcat load tại Splash: 105-spl-n-native-high, 201-lfo1-n-native-high1."
    ads = _ads(*LUONG["units"].values(), _u("095", "id_201_lfo1_n_native_high1", req=0))
    assert _check(thieu, ads)["verdict"] == a.FAIL


def test_bat_ky_kem_danh_sach_chi_xet_unit_liet_ke():
    line = ("Không có loadAd cho bất kỳ unit high1/high2 nào: 102-spl-n-inter-high1, "
            "201-lfo1-n-native-high1/high2.")
    ads = _ads(*LUONG["units"].values(), _u("095", "id_201_lfo1_n_native_high1", req=0),
               _u("712", "id_201_lfo1_n_native_high2", req=0),
               _u("538", "id_102_spl_n_inter_high1", req=0, kind="interstitial"))
    assert _check(line, ads)["verdict"] == a.PASS
    ads["units"]["*****712"]["requested"] = 1
    assert _check(line, ads)["verdict"] == a.FAIL


def test_man_hai_cham_va_ghi_chu_preload_khong_phai_alternate():
    line = "OB2: native 302-onb2-n-native-high; OB4: native 304-onb4-n-native-high (ghi lại màn preload)."
    ads = _ads(*LUONG["units"].values(), _u("407", "id_304_onb4_n_native_high"))
    assert _check(line, ads)["verdict"] == a.PASS


def test_id_dung_chung_khong_tinh_cho_vi_tri_tat():
    line = "OB1 hiển thị native 202-lfo2-n-native-high (không có loadAd 301 vì đã OFF)."
    ket = _check(line, LUONG, {"show_301_onb1_n_native_high": "false"})
    # ...658 la 301_onb1_n_native_high rieng -> van tinh
    assert ket["verdict"] == a.FAIL
    chi_chung = _ads(*(u for u in LUONG["units"].values() if u["unit"] != "*****658"))
    ket = _check(line, chi_chung, {"show_301_onb1_n_native_high": "false"})
    assert ket["verdict"] == a.PASS and "dùng chung ID" in ket["reason"]


def test_ve_dieu_kien_da_show_khong_cham_nhu_ky_vong():
    line = "Không hiển thị OB5 (303 đã show ở OB3), vào Question."
    assert "303" not in _check(line, LUONG)["reason"]


def test_ma_ngon_ngu_trong_ngoac_khong_phai_chu_tren_man():
    line = ("Nội dung khối 'EN-us' ('EN - OB1 title', 'EN - OB2 title', 'EN - OB4 title', màu #2E7D32) "
            "dù language_code khác hoa/thường với en-US.")
    drive = {"walked": True, "steps": [{"n": 1, "dump": "<node text='EN - OB1 title'/><node text='EN - OB2 title'/>"
                                                       "<node text='EN - OB4 title'/>"}]}
    from rcr import assert_chu
    ket = assert_chu.cham(line, drive)
    assert ket["verdict"] == a.PASS and "EN-us" not in ket["reason"]


def test_case_luong_toi_home_phai_di_het():
    from rcr.luong_toan_bo import can_di_het
    assert can_di_het(["Luồng: LFO1 → LFO2 → OB2 → OB4 → Home."])
    assert can_di_het(["Luồng FO không bị block, không crash."], "#SDK361-RG06-01 Toàn luồng")
    assert can_di_het(["Luồng FO đi bình thường (Splash → LFO1 → LFO2 → OB1 → OB4 → Question → Home)."])
    assert not can_di_het(["Native 304-onb4-n-native-high hiển thị."], "#SDK361-RG01-09 OB4")


def test_khong_hien_thi_nhieu_trang_ob_cham_bang_event_view():
    from rcr import assert_man_khong
    drive = {"steps": [{"activity": "x.VslTemplate4OnboardingActivity"}], "final": {"activity": "x.MainActivity"}}
    ev = [{"name": n} for n in ("lfo1_view", "lfo2_view", "ob2_view", "ob4_view")]
    ket = assert_man_khong.cham("Không hiển thị OB1, OB3, OB5, Question.", drive, ev)
    assert ket["verdict"] == a.PASS, ket
    ev.append({"name": "ob3_view"})
    assert assert_man_khong.cham("Không hiển thị OB1, OB3, OB5, Question.", drive, ev)["verdict"] == a.FAIL


def test_anh_content_bo_vung_lop_phu_khung_chu():
    """AIP936 R01-03: dung OB1.png nhung khung chu ban trong suot ~50% trang che 1/3 duoi -> lech 37,7 > 28."""
    import random
    from types import SimpleNamespace as NS
    from PIL import Image
    from rcr import assert_anh_content as ac
    from rcr.splash_media import _lech
    rnd = random.Random(1)
    goc = Image.new("RGB", (54, 120))
    goc.putdata([(rnd.randrange(256), rnd.randrange(256), rnd.randrange(256)) for _ in range(54 * 120)])
    chup = goc.copy()
    phu = Image.new("RGB", (54, 40), (248, 249, 249))
    chup.paste(Image.blend(goc.crop((0, 70, 54, 110)), phu, 0.5), (0, 70))
    b = NS(left=0, top=0, right=540, bottom=1200, empty=False)
    khung = NS(left=0, top=700, right=540, bottom=1100, empty=False)
    nodes = [NS(visible=True, bounds=khung, resource_id="ctlContent", text=""),
             NS(visible=True, bounds=b, resource_id="", text="")]
    assert _lech(chup, goc, [True] * (54 * 120)) > 15
    na = ac._mat_na(b, ac._lop_phu(nodes, b))
    assert _lech(chup, goc, na) < 1


def test_phan_tram_khong_phai_ma_vi_tri():
    from rcr import ad_positions
    assert ad_positions._position_token("inter sẵn sàng → fill 100% rồi show inter (logic 3.6.0).") == ""
    assert ad_positions._position_token("Không load 302 ở OB2") == "302"


def test_hai_cau_phu_dinh_va_khang_dinh_tach_theo_dau_cham():
    line = ("Không có loadAd cho: 302-onb2-n-native-high/native, 304-onb4-n-native-high/native. "
            "305-onb5-n-native-high vẫn được preload (ghi lại màn preload).")
    ads = _ads(_u("658", "id_301_onb1_n_native_high"), _u("669", "id_305_onb5_n_native_high"),
               _u("407", "id_304_onb4_n_native_high", req=0), _u("418", "id_302_onb2_n_native", req=0),
               _u("633", "id_302_onb2_n_native_high", req=0), _u("781", "id_304_onb4_n_native", req=0))
    ket = _check(line, ads)
    assert ket["verdict"] == a.PASS, ket


def test_buoc_di_tiep_den_ob_va_ra_logcat():
    from rcr import act_cau_fo
    assert act_cau_fo.resolve("Đi tiếp đến OB4.", []).summary["kind"] == "goto"
    assert act_cau_fo.resolve("Rà logcat.", []).summary["kind"] == "noop"
