"""Cac dong Expected cua bo TC 3.6.1 tung ra PASS / FAIL gia tren AIP886 2.7.0 (31/10/2026)."""

from __future__ import annotations

from rcr import assert_check as a
from rcr import assert_mau

OK_CRASH = {"crashed": False, "lines": []}


def _drive(*dumps, walked=True, **them):
    return {"steps": [{"n": i, "dump": d, "activity": "OnboardingActivity"} for i, d in enumerate(dumps, 1)],
            "walked": walked, **them}


def _check(line, drive, ads=None):
    return a.check(line, ads or {"units": {}}, drive, OK_CRASH)


def test_khong_dung_khoi_en_ma_man_khong_co_EN_ROOT_thi_PASS_chu_khong_tim_chu_en():
    line = "Hiển thị nội dung default của app, KHÔNG dùng khối 'en' ('EN ROOT - ...') vì không lùi về mã gốc."
    ok = _check(line, _drive("<node text='Restyle your look instantly'/>"))
    assert ok["verdict"] == a.PASS and "EN ROOT" in ok["reason"]
    hong = _check(line, _drive("<node text='EN ROOT - OB1 title'/>"))
    assert hong["verdict"] == a.FAIL


def test_cham_moi_chuoi_phu_dinh_trong_dong():
    line = "Nội dung app truyền / chữ mặc định SDK, không có 'EN ROOT - ...', không có 'KEY CU ...'."
    assert _check(line, _drive("<node text='Which style fits your vision?'/>"))["verdict"] == a.PASS
    assert _check(line, _drive("<node text='KEY CU - header'/>"))["verdict"] == a.FAIL


def test_phu_dinh_ma_chua_lai_toi_man_thi_khong_ket_luan():
    line = "Không hiển thị nội dung question_screen_config ('KEY CU ...')."
    assert _check(line, _drive("<node text='Splash'/>", walked=False))["verdict"] == a.NEEDS_HUMAN


def test_gif_chay_mot_lan_khong_pass_chi_nho_thay_chu():
    line = "Nền GIF chạy 1 lần rồi dừng ở frame cuối (video_loop=false), sub_title 'Gif once'."
    ket = _check(line, _drive("<node text='Gif once'/>"))
    assert ket["verdict"] == a.NOT_VERIFIABLE and "GIF" in ket["reason"]


def test_chu_hien_ban_dich_cua_apk_thi_van_PASS():
    drive = _drive("<node text='Balayez pour continuer'/>",
                   ban_dich={"Swipe to next": ["Balayez pour continuer"]})
    ket = _check("Hiển thị icon SWIPE + text 'Swipe to next'.", drive)
    assert ket["verdict"] == a.PASS and "bản dịch" in ket["reason"]


def test_mau_primary_khong_co_so_do_thi_khong_PASS():
    ket = _check("Text 'Swipe to next' đúng màu primary của app.", _drive("<node text='Swipe to next'/>"))
    assert ket["verdict"] == a.NOT_VERIFIABLE
    do = _drive("<node text='Swipe to next'/>", mau_primary={"hex": "#FFA9EA", "khop": True, "pixel": 8501})
    assert _check("Text 'Swipe to next' đúng màu primary của app.", do)["verdict"] == a.PASS


def test_trong_luc_inter_khong_show_thi_khong_PASS_ve_phu_dinh():
    line = ("Trong lúc inter resume 503_inter_high đang hiển thị: logcat KHÔNG có log show "
            "201-lfo1-n-native-high (fix bug).")
    ads = {"units": {"native:*****630": {"type": "native", "unit": "*****630", "requested": 1, "loaded": 0,
                                         "shown": 0, "rc_keys": ["id_201_lfo1_n_native_high"]}}}
    ket = _check(line, _drive("<node/>"), ads)
    assert ket["verdict"] == a.NEEDS_HUMAN and "không xảy ra" in ket["reason"]


def test_inter_full_man_ma_khong_fill_thi_chua_co_gi_de_xem():
    line = "Inter 102-spl-n-inter-high hiển thị full màn, không lộ background device phía sau."
    ads = {"units": {"interstitial:*****708": {"type": "interstitial", "unit": "*****708", "requested": 1,
                                                "loaded": 0, "shown": 0, "rc_keys": ["id_102_spl_n_inter_high"]}}}
    assert _check(line, _drive("<node/>"), ads)["verdict"] == a.NEEDS_HUMAN


def test_mau_lay_dung_chu_trong_ngoac_khong_an_chu_u_cua_mau():
    cap = assert_mau._cap("Dòng 'Preparing your data...' màu #888888 trên progress bar.", {})
    assert cap == [("Preparing your data...", "Preparing your data...", "888888", 1)]
    # "button 'X', slider mau #..." la mau cua slider
    cap = assert_mau._cap("Nền text #F5F5F5, button 'FR - Next', slider màu #1565C0, ảnh content OB1.", {})
    assert [c[0] for c in cap] == [assert_mau.NEN, "slider"]


def test_mau_do_dung_node_theo_chu():
    drive = {"steps": [{"n": 1, "mau": [
        {"text": "Loading", "id": "tvLoading", "dem": {"#888888": [2, 0]}},
        {"text": "Preparing your data...", "id": "tvLoadingText", "dem": {"#888888": [4005, 383]}}]}]}
    ket = assert_mau.cham("Dòng 'Preparing your data...' màu #888888 trên progress bar.", drive, {})
    assert ket["verdict"] == a.PASS and "4005" in ket["reason"]


def test_mau_nen_khong_do_bang_pixel_chu_va_ten_chung_khong_do_bua():
    drive = {"steps": [{"n": 1, "mau": [{"text": "This action may contain ads", "id": "tvText",
                                          "dem": {"#F5F5F5": [0, 0], "#1565C0": [0, 0]}}]}]}
    ket = assert_mau.cham("Nền text #F5F5F5, button 'FR - Next', slider màu #1565C0, ảnh content OB1.", drive, {})
    assert ket["verdict"] != a.FAIL
    assert "màu nền" in ket["reason"]


def test_mau_lay_khung_ro_nhat_va_khung_trong_khong_FAIL():
    drive = {"steps": [
        {"n": 1, "mau": [{"text": "My Super App", "id": "tvTitle", "dem": {"#FFFFFF": [20719, 0]}}]},
        {"n": 2, "mau": [{"text": "My Super App", "id": "tvTitle", "dem": {"#FFFFFF": [0, 0]}}]}]}
    assert assert_mau.cham("Title 'My Super App' màu #FFFFFF", drive, {})["verdict"] == a.PASS


def test_trong_luc_inter_show_thi_cham_vi_tri_ve_sau():
    line = ("Trong lúc inter resume 503_inter_high đang hiển thị: logcat KHÔNG có log show "
            "201-lfo1-n-native-high (fix bug).")
    u503 = {"type": "interstitial", "unit": "*****911", "requested": 1, "loaded": 1, "shown": 1,
            "rc_keys": ["id_503_inter_high"]}
    u201 = {"type": "native", "unit": "*****630", "requested": 2, "loaded": 0, "shown": 0,
            "rc_keys": ["id_201_lfo1_n_native_high"]}
    ket = _check(line, _drive("<node/>"), {"units": {"a": u503, "b": u201}})
    assert ket["verdict"] == a.PASS and "201_lfo1_n_native_high không show" in ket["reason"]
    co_show = {**u201, "shown": 1}
    assert _check(line, _drive("<node/>"), {"units": {"a": u503, "b": co_show}})["verdict"] == a.NEEDS_HUMAN


def test_khong_co_native_cham_vi_tri_case_tat_va_chu():
    cfg = {"show_301_onb1_n_native_high": "true", "show_302_onb2_n_native": "false",
           "show_302_onb2_n_native_high": "false"}
    u301 = {"type": "native", "unit": "*****582", "requested": 1, "loaded": 1, "shown": 1,
            "rc_keys": ["id_301_onb1_n_native_high"]}
    drive = _drive("<node text='Balayez pour continuer'/>", ban_dich={"Swipe to next": ["Balayez pour continuer"]})
    line = "Không có native ad, hiển thị icon SWIPE + text 'Swipe to next'."
    ok = a.check(line, {"units": {"a": u301}}, drive, OK_CRASH, cfg=cfg)
    assert ok["verdict"] == a.PASS and "302" in ok["reason"] and "bản dịch" in ok["reason"]
    u302 = {"type": "native", "unit": "*****941", "requested": 1, "loaded": 0, "shown": 0,
            "rc_keys": ["id_302_onb2_n_native"]}
    assert a.check(line, {"units": {"a": u301, "b": u302}}, drive, OK_CRASH, cfg=cfg)["verdict"] == a.FAIL


def test_chu_swipe_to_next_trong_ngoac_khong_bi_hieu_la_vuot():
    ket = _check("Text 'Swipe to next' đúng màu primary của app.", _drive("<node text='Swipe to next'/>"))
    assert "vuốt" not in ket["reason"]


def test_bam_chu_roi_vao_home_cham_ca_man_dich():
    line = "Bấm 'FR - Go' → vào Home."
    o_billing = {"steps": [{"n": 1, "dump": "<node text='FR - Go'/>"}], "walked": True,
                 "final": {"activity": "x.VslBillingActivity"}}
    assert _check(line, o_billing)["verdict"] == a.FAIL
    o_home = {**o_billing, "final": {"activity": "x.AIP886AIPhotoVideoMakerMainActivity"}}
    assert _check(line, o_home)["verdict"] == a.PASS


def test_khong_co_native_full_khi_303_bat_chi_kiem_show():
    cfg = {"show_303_onb3_n_native_high": "true", "auto_swipe_onb3": "true"}
    req = {"type": "native", "unit": "*****216", "requested": 1, "loaded": 0, "shown": 0,
           "rc_keys": ["id_303_onb3_n_native_high"]}
    assert a.check("Không có native full.", {"units": {"a": req}}, _drive("<node/>"), OK_CRASH,
                   cfg=cfg)["verdict"] == a.PASS
    show = {**req, "loaded": 1, "shown": 1}
    assert a.check("Không có native full.", {"units": {"a": show}}, _drive("<node/>"), OK_CRASH,
                   cfg=cfg)["verdict"] == a.FAIL
