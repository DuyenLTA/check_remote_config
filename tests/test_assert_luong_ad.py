"""Luong man quanh quang cao - du lieu theo chay thu AIP936 1.9.0 Pixel 6 03/11/2026 (RG01 / RG08)."""

from __future__ import annotations

from pathlib import Path

from rcr import assert_check, assert_luong_ad


def _u(unit, keys, req=1, shown=0):
    return {"unit": unit, "requested": req, "shown": shown, "rc_keys": keys}


LFO1 = {"activity": "x.language.language1.VslTemplate4Language14Activity"}
SPLASH_SHOW = [_u("*****809", ["id_102_spl_n_inter"], shown=1), _u("*****186", ["id_102_spl_n_inter_high"])]


def test_khong_inter_splash_2_cham_bang_show_khong_bang_request():
    dong = "Sau khi bấm tick: KHÔNG hiển thị Inter Splash 2 (102-spl-n-inter-high)."
    assert assert_luong_ad.cham(dong, SPLASH_SHOW, {})["verdict"] == "PASS"
    hai = SPLASH_SHOW + [_u("*****538", ["id_102_spl_n_inter_high1"], shown=1)]
    assert assert_luong_ad.cham(dong, hai, {})["verdict"] == "FAIL"


def test_sang_inter_splash_va_dong_inter_sang_lfo1():
    assert assert_luong_ad.cham("Splash chạy tiếp, luồng sang Inter Splash bình thường.", SPLASH_SHOW,
                                {})["verdict"] == "PASS"
    d = {"final": {"activity": "com.google.android.gms.ads.AdActivity"}, "final_sau_dong": LFO1}
    assert assert_luong_ad.cham("Đóng inter → sang LFO1 bình thường.", [], d)["verdict"] == "PASS"


def test_chay_lai_tu_splash_hien_lai_lfo1():
    dong = "App chạy lại từ Splash, hiện lại LFO1 (pass_lfo_criteria=false, chưa pass OB)."
    ev = [{"name": "splash_view"}]
    assert assert_luong_ad.cham(dong, [], {"final": LFO1}, ev)["verdict"] == "PASS"
    assert assert_luong_ad.cham(dong, [], {"final": LFO1}, [])["verdict"] == "FAIL"


def test_question_chua_chon_an_cta_co_ban_tay():
    xml = ('<?xml version="1.0"?><hierarchy><node index="0" text="" resource-id="p:id/lottieQuestion" '
           'class="android.widget.ImageView" package="p" content-desc="" clickable="false" enabled="true" '
           'bounds="[100,500][300,700]" /></hierarchy>')
    d = {"steps": [{"activity": "x.question.VslTemplate4QuestionActivity", "dump": xml}]}
    r = assert_luong_ad.cham("Chưa chọn: ẩn nút CTA, có bàn tay hint tap vào card đầu.", [], d)
    assert r["verdict"] == "PASS" and "bàn tay hint có" in r["reason"]


def test_check_all_dung_luat_moi():
    kq = assert_check.check_all(["Đóng inter → sang LFO1 bình thường."], {"units": {}}, {"final": LFO1}, {})
    assert kq["lines"][0]["verdict"] == "PASS"
