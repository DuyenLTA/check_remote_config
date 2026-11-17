"""Cot Ad description co key RC (ngoai show_*) -> case IAA-ii-05 doi gia tri tung key de check app an key.

Vu AIP921 17/11/2026: free_scan_nutrition_limit_per_day... chi nam trong Expected, tool khong doi nen khong ai check.
"""

from __future__ import annotations

from rcr.tc_iaa_key_mo_ta import gia_tri_khac, key_trong_mo_ta
from rcr.tc_iaa_tu_sheet_kt import Tang, ViTri, tao_case

MO_TA = ("- Hiển thị reward khi user hết lượt free tại màn AI Scan\n"
         "- Remote config: free_scan_nutrition_limit_per_day = 3 (số lượt free/ngày), "
         "reward_scan_nutrition_ads_per_claim = 3, reward_scan_nutrition_amount = 2, "
         "enable_scan_nutrition: true, show_reward_nutrition = true, scan_mode = fast")


def _vi_tri(mo_ta=MO_TA):
    return ViTri(goc="reward_nutrition", man="AI Scan", loai="Reward", mo_ta=mo_ta,
                 high=Tang("reward_nutrition_high", "ca-app-pub-1/1", "show_reward_nutrition_high"),
                 thuong=Tang("reward_nutrition", "ca-app-pub-1/2", "show_reward_nutrition"))


def test_gia_tri_khac():
    assert gia_tri_khac("3") == "4" and gia_tri_khac("0.5") == "1.5"
    assert gia_tri_khac("true") == "false" and gia_tri_khac("False") == "true"
    assert gia_tri_khac("fast") is None


def test_key_trong_mo_ta_bo_key_show_cua_vi_tri():
    ds = key_trong_mo_ta(MO_TA, {"show_reward_nutrition", "show_reward_nutrition_high"})
    assert [k for k, *_ in ds] == ["free_scan_nutrition_limit_per_day", "reward_scan_nutrition_ads_per_claim",
                                   "reward_scan_nutrition_amount", "enable_scan_nutrition", "scan_mode"]
    assert ds[0] == ("free_scan_nutrition_limit_per_day", "3", "4")


def test_tao_case_them_case_05_doi_key():
    cases = tao_case([_vi_tri()])
    c = next(c for c in cases if c.n == "IAA-01-05")
    dat = dict(d.split("=", 1) for d in c.test_data.splitlines())
    assert dat["show_reward_nutrition"] == dat["show_reward_nutrition_high"] == "true"      # vi tri van bat
    assert dat["free_scan_nutrition_limit_per_day"] == "4" and dat["reward_scan_nutrition_amount"] == "3"
    assert dat["enable_scan_nutrition"] == "false" and "scan_mode" not in dat
    assert any("free_scan_nutrition_limit_per_day" in e and "3 → 4" in e for e in c.expects)
    assert any("scan_mode" in e and "đổi tay" in e for e in c.expects)


def test_mo_ta_khong_co_key_thi_khong_them_case():
    cases = tao_case([_vi_tri("- Preload khi vào màn, show khi bấm Scan")])
    assert [c.n for c in cases] == ["IAA-01-01", "IAA-01-02", "IAA-01-03", "IAA-01-04"]
