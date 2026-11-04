"""Dong "... giu nguyen" - dump that man Question AIP936 1.9.0 Pixel 6 (04/11/2026, da chon 'Scandinavian Minimal')."""

from __future__ import annotations

from pathlib import Path

from rcr import assert_check, assert_giu_nguyen

CHON = (Path(__file__).parent / "fixtures" / "question_chon_item_aip936.xml").read_text(encoding="utf-8")
CHUA_CHON = CHON.replace("ivQuestionTick", "ivKhongCo")
Q = "x.question.VslTemplate4QuestionActivity"
ITEM = "Item đã chọn giữ nguyên."


def _drive(truoc, sau, qua_ad=True):
    cuoi = {"activity": Q, "dump": sau}
    d = {"steps": [{"activity": Q, "dump": truoc}], "final": cuoi}
    if qua_ad:
        d["final"] = {"activity": "com.google.android.gms.ads.AdActivity", "dump": ""}
        d["final_sau_dong"] = cuoi
    return d


def test_doc_dung_item_co_tick():
    assert assert_giu_nguyen._item_chon(CHON) == ["Scandinavian Minimal"]
    assert assert_giu_nguyen._item_chon(CHUA_CHON) == []


def test_item_giu_nguyen_sau_khi_dong_ad_resume():
    assert assert_giu_nguyen.cham(ITEM, [], _drive(CHON, CHON))["verdict"] == "PASS"


def test_mat_lua_chon_la_fail():
    ket = assert_giu_nguyen.cham(ITEM, [], _drive(CHON, CHUA_CHON))
    assert ket["verdict"] == "FAIL" and "không còn item" in ket["reason"]


def test_truoc_do_chua_chon_thi_khong_ket_luan():
    # Chay le case (khong noi tu case chon item): khong co gi de so -> de nguoi xem, khong PASS gia.
    assert assert_giu_nguyen.cham(ITEM, [], _drive(CHUA_CHON, CHUA_CHON)) is None


def test_man_cuoi_khong_phai_question_thi_khong_ket_luan():
    d = _drive(CHON, CHON, qua_ad=False)
    d["final"]["activity"] = "com.google.android.gms.ads.AdActivity"
    assert assert_giu_nguyen.cham(ITEM, [], d) is None


def _u(unit, keys, req=1, shown=0):
    return {"unit": unit, "requested": req, "shown": shown, "rc_keys": keys}


RELOAD = "Native 201-lfo1-n-native-high giữ nguyên, không reload."


def test_native_khong_reload_khi_moi_unit_request_mot_lan():
    u = [_u("*****111", ["id_201_lfo1_n_native_high"], shown=1), _u("*****222", ["id_202_lfo2_n_native_high"], 3)]
    assert assert_giu_nguyen.cham(RELOAD, u, {})["verdict"] == "PASS"


def test_request_hai_lan_khong_biet_truoc_hay_sau_thao_tac_thi_de_nguoi_xem():
    u = [_u("*****111", ["id_201_lfo1_n_native_high"], req=2, shown=1)]
    assert assert_giu_nguyen.cham(RELOAD, u, {}) is None


def test_khong_fill_la_blocked_khong_co_request_thi_khong_ket_luan():
    # Pixel 6 04/11: 303 request 8 lan, load 0 -> khong co ad de kiem "giu nguyen" -> BLOCKED (thieu dieu kien).
    ket = assert_giu_nguyen.cham(RELOAD, [_u("*****111", ["id_201_lfo1_n_native_high"], req=3)], {})
    assert ket["verdict"] == "BLOCKED" and "không fill" in ket["reason"]
    assert assert_giu_nguyen.cham(RELOAD, [], {}) is None


def test_van_o_ob3_gop_ca_man_va_reload():
    dong = "Vẫn ở OB3, native full 303-onb3-n-native-high giữ nguyên, không reload."
    u = [_u("*****333", ["id_303_onb3_n_native_high"], shown=1)]
    ob3 = {"final": {"activity": "x.VslTemplate4OnboardingActivity", "page": 3}}
    assert assert_giu_nguyen.cham(dong, u, ob3)["verdict"] == "PASS"
    lfo = {"final": {"activity": "x.Language14Activity"}}
    assert assert_giu_nguyen.cham(dong, u, lfo)["verdict"] == "FAIL"


def test_noi_vao_assert_check():
    ket = assert_check.check(ITEM, {"units": {}}, _drive(CHON, CHON), {})
    assert ket["verdict"] == "PASS"


def test_chuoi_cham_khong_reload_theo_lich_su_ca_chuoi():
    # Log rieng case (chuoi) khong co lan load dau tien cua 201; log don co -> cham theo log don.
    don = {"a": _u("*****111", ["id_201_lfo1_n_native_high"], shown=1)}
    ket = assert_check.check(RELOAD, {"units": {}, "units_don": don}, {}, {})
    assert ket["verdict"] == "PASS"
