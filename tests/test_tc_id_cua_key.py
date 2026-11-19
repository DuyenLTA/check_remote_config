"""Test Data `key=<ID other_key>` (tab TC SDK 3.7.3) -> ID that cua key do, khong bi bo nhu cho trong."""

from rcr import rc_extract, tc_id_cua_key
from rcr.models import Case

DANG_CHAY = {
    "splash_inter_high_n_id": "ca-app-pub-1/588",
    "splash_inter_n_id": "ca-app-pub-1/854",
    "question_inter_high_n_id": "",
    "question_inter_n_id": "",
    "question_inter_high_o_id": "",
    "splash_inter_high_o_id": "ca-app-pub-1/358",
    "enable_all_ads": "true",
}


def _case(td: str) -> Case:
    return Case(n="SDK373-N01-01", feature="N01", description="N01", sub_scenario="Splash", user_state="new_user",
                test_data=td, precondition="", actions=("Mở app.",), expects=("Inter hiển thị.",))


def test_thay_id_cua_key_bang_gia_tri_dang_chay():
    td = "enable_all_ads=true\nquestion_inter_high_n_id=<ID splash_inter_high_n_id>\nquestion_inter_n_id=\"\""
    assert "question_inter_high_n_id=ca-app-pub-1/588" in tc_id_cua_key.thay_chuoi(td, DANG_CHAY)


def test_id_inter_test_khac_thanh_unit_test_google():
    out = tc_id_cua_key.thay_chuoi("question_inter_high_o_id=<ID inter test khác (không preload)>", DANG_CHAY)
    assert out == f"question_inter_high_o_id={tc_id_cua_key.INTER_TEST_GOOGLE}"


def test_key_khong_co_gia_tri_thi_giu_nguyen():
    assert tc_id_cua_key.thay_chuoi("a=<ID khong_co_key>", DANG_CHAY) == "a=<ID khong_co_key>"
    assert tc_id_cua_key.thay_chuoi("a=<ID question_inter_n_id>", DANG_CHAY) == "a=<ID question_inter_n_id>"


def test_extract_giu_key_sau_khi_thay():
    td = ("enable_all_ads=true\nquestion_inter_high_n_id=<ID splash_inter_high_n_id>\n"
          "splash_inter_high_o_id=<ID splash_inter_high_n_id>\nquestion_inter_high_o_id=<ID inter test khác (không preload)>")
    [(_, c)] = tc_id_cua_key.thay([("3.7.3", _case(td))], DANG_CHAY)
    d = rc_extract.extract(c, set(DANG_CHAY))
    assert d.overrides["question_inter_high_n_id"] == "ca-app-pub-1/588"
    assert d.overrides["splash_inter_high_o_id"] == "ca-app-pub-1/588"
    assert d.overrides["question_inter_high_o_id"] == tc_id_cua_key.INTER_TEST_GOOGLE


def test_khong_doi_gi_thi_tra_nguyen_case():
    c = _case("enable_all_ads=true")
    [(_, c2)] = tc_id_cua_key.thay([("3.7.3", c)], DANG_CHAY)
    assert c2 is c
