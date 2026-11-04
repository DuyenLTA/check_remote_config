"""Cham dong ad resume (501 AOA / 502 native full / 503 inter) - du lieu theo log that AIP936 1.9.0 (11) 03/11/2026."""

from __future__ import annotations

from rcr import assert_check, assert_resume


def _u(unit, keys, req=1, shown=0):
    return {"type": "?", "unit": unit, "requested": req, "loaded": shown, "shown": shown, "rc_keys": keys}


AOA_SHOW = {"units": {"a": _u("*****440", ["id_501_aoa_high"], shown=1),
                      "n": _u("*****814", ["id_201_lfo1_n_native_high"], req=3)}}
INTER_NOFILL = {"units": {"h": _u("*****397", ["id_503_inter_high"]), "t": _u("*****927", ["id_503_inter"])}}
KHONG_GI = {"units": {"n": _u("*****658", ["id_301_onb1_n_native_high"])}}
RA_NEN = {"steps": [{"step": "Bấm Home hệ thống → mở lại từ Recent."}],
          "final": {"activity": "com.visionlab.tutorial.vsltemplate4.language.language1.VslTemplate4Language14Activity"}}


def test_aoa_resume_hien_thi():
    r = assert_resume.cham("Sau khi mở lại: ad resume AOA 501_aoa_high hiển thị (resume_type=aoa).", AOA_SHOW, RA_NEN)
    assert r["verdict"] == "PASS" and "…440" in r["reason"]


def test_inter_resume_khong_fill_request_dung_la_dat():
    r = assert_resume.cham("Tại OB1 sau khi mở lại: inter resume 503_inter_high hiển thị.", INTER_NOFILL, RA_NEN)
    assert r["verdict"] == "PASS" and "không fill" in r["reason"]


def test_khong_show_ad_resume():
    assert assert_resume.cham("Không show ad resume 501.", KHONG_GI, RA_NEN)["verdict"] == "PASS"
    sai = assert_resume.cham("Không show ad resume 501 chồng lên inter.", AOA_SHOW, RA_NEN)
    assert sai["verdict"] == "FAIL" and "…440" in sai["reason"]


def test_chua_ra_nen_thi_chua_cham_co_ra_nen_ma_khong_request_la_fail():
    assert assert_resume.cham("Ad resume AOA 501_aoa_high hiển thị.", KHONG_GI, {"steps": []})["verdict"] == "NEEDS_HUMAN"
    assert assert_resume.cham("Ad resume AOA 501_aoa_high hiển thị.", KHONG_GI, RA_NEN)["verdict"] == "FAIL"


def test_dong_ad_resume_ve_dung_man_va_native_co_request():
    r = assert_resume.cham("Đóng ad resume → về đúng LFO1, reload 201-lfo1-n-native-high (reload OK → ad mới, "
                           "fail → giữ ad cũ).", AOA_SHOW, RA_NEN)
    assert r["verdict"] == "PASS" and "3 lần" in r["reason"]
    sai_man = dict(RA_NEN, final={"activity": "x.MainActivity"})
    assert assert_resume.cham("Đóng ad resume → về đúng LFO1, reload 201-lfo1-n-native-high.", AOA_SHOW,
                              sai_man)["verdict"] == "FAIL"


def test_dong_khong_phai_resume_khong_dung_luat_nay():
    assert assert_resume.cham("Native 201-lfo1-n-native-high hiển thị (resume_type=aoa).", AOA_SHOW, RA_NEN) is None
    # "Trong luc inter resume dang hien thi: khong co log show 201" la cau ve 201 -> assert_trong_luc cham truoc
    kq = assert_check.check_all(["Trong lúc inter resume 503_inter_high đang hiển thị: logcat KHÔNG có log show "
                                 "201-lfo1-n-native-high."], INTER_NOFILL, RA_NEN, {})
    assert "ad resume 503 được request" not in kq["lines"][0]["reason"]


def test_check_all_khong_con_roi_xuong_nhin_mat():
    kq = assert_check.check_all(["Sau khi mở lại: ad resume AOA 501_aoa_high hiển thị (resume_type=aoa)."],
                                AOA_SHOW, RA_NEN, {})
    assert kq["lines"][0]["verdict"] == "PASS"


def test_case_splash_cho_qua_splash_roi_moi_doc_log(monkeypatch):
    """RG01-02/03, OG01-01: doc log luc con o Splash -> inter chua request -> NEEDS_HUMAN oan."""
    import asyncio
    from rcr import case_run
    man = iter([("p", "x.SplashActivity"), ("p", "x.SplashActivity"), ("p", "com.google.android.gms.ads.AdActivity")])

    async def focus(client, serial):
        return next(man)

    async def ngu(s):
        return None
    monkeypatch.setattr(case_run.device_app, "focus", focus)
    monkeypatch.setattr(case_run.asyncio, "sleep", ngu)
    log = []

    class B:
        serial = "S"
    asyncio.run(case_run._cho_qua_splash(None, B(), log.append))
    assert "AdActivity" in log[-1]
    assert case_run.SPLASH_ADS_RE.search("Inter 102-spl-n-inter-high hiển thị.")
    assert case_run.SPLASH_ADS_RE.search("Logcat load tại Splash: 105-spl-n-native-high")
    assert not case_run.SPLASH_ADS_RE.search("Native 301-onb1-n-native-high hiển thị.")


def test_ve_dung_man_cham_theo_man_sau_khi_dong_ad_va_khong_nham_onb():
    """Pixel 6 03/11: man cuoi chup luc AOA con che; 've dung Question, reload 305-onb5' bi doc nham Onboarding."""
    d = {"steps": [{"step": "Bấm Home hệ thống → mở lại từ Recent."}],
         "final": {"activity": "com.google.android.gms.ads.AdActivity"},
         "final_sau_dong": {"activity": "x.onboarding.question.VslTemplate4QuestionActivity"}}
    ads = {"units": {"n": _u("*****669", ["id_305_onb5_n_native_high"], req=2)}}
    r = assert_resume.cham("Đóng ad resume → về đúng Question, reload 305-onb5-n-native-high (reload OK → ad mới, "
                           "fail → giữ ad cũ).", ads, d)
    assert r["verdict"] == "PASS" and "QuestionActivity" in r["reason"]


def test_dong_progress_cho_inter_cung_cho_qua_splash():
    from rcr import case_run
    assert case_run.SPLASH_ADS_RE.search("Progress chạy 0 → 95% trong ~10s, giữ 95% chờ inter; inter sẵn sàng → "
                                         "fill 100% rồi show inter.")
