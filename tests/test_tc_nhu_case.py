"""Test Data "key = ... (nhu R01)" -> gia tri that cua nhom R01 (AIP936 RG10-01 03/11/2026)."""

from __future__ import annotations

from rcr import rc_extract, tc_nhu_case
from rcr.models import Case

JSON_FR = '[{"language_code":"fr","onb1":{"title":"FR - OB1 title"}}]'
WL = {"onboard_config_content_new", "language_code", "pass_lfo_criteria", "enable_all_ads"}


def _c(n, td):
    return Case(n=n, feature="", description="", sub_scenario="", precondition="1. Clear data.", test_data=td)


PAIRS = [("3.6.1", _c("SDK361-R01-01", f"enable_all_ads=true\n onboard_config_content_new={JSON_FR}")),
         ("3.6.1", _c("SDK361-RG10-01", "enable_all_ads=true\n pass_lfo_criteria=true\n"
                                        " onboard_config_content_new = JSON có khối language_code=fr (như R01)"))]


def test_lay_gia_tri_cua_nhom_duoc_nhac():
    rg10 = tc_nhu_case.thay_nhu(PAIRS, WL)[1][1]
    d = rc_extract.extract(rg10, WL)
    assert d.runnable and d.overrides["onboard_config_content_new"] == JSON_FR
    assert d.overrides["pass_lfo_criteria"] == "true"


def test_khong_tim_thay_nhom_thi_giu_nguyen_va_case_van_dung():
    chi_rg10 = tc_nhu_case.thay_nhu(PAIRS[1:], WL)
    assert not rc_extract.extract(chi_rg10[0][1], WL).runnable


def test_nhu_khong_ngoac_cung_lay_gia_tri():
    """TC 3.6.2: "ob_question_config=JSON như R01 (có khối en-US)" - khong ngoac quanh "nhu R01"."""
    pairs = [PAIRS[0], ("3.6.2", _c("SDK362-R02-01", "enable_all_ads=true\n"
                                    "onboard_config_content_new=JSON như R01 (có khối en-US)"))]
    d = rc_extract.extract(tc_nhu_case.thay_nhu(pairs, WL)[1][1], WL)
    assert d.runnable and d.overrides["onboard_config_content_new"] == JSON_FR
