"""Mua sub qua nut sheet xem ads: uu tien weekly, het han goi test thi duoc mua lai."""

from __future__ import annotations

from rcr import rating_cong_thuc as rc


def test_chi_mua_weekly_hoac_monthly():
    assert rc.GOI_SUB_UU_TIEN == ("weekly", "monthly")      # user chot 17/11/2026: khong bao gio yearly


def test_mua_lai_khi_goi_test_het_han():
    rc._DA_MUA_QUA_NUT.clear()
    assert rc.nen_mua_qua_nut("S", "p")
    rc._DA_MUA_QUA_NUT[("S", "p")] = 1000.0
    assert not rc.nen_mua_qua_nut("S", "p", bay_gio=1000.0 + 60)            # vua mua: khong mua lai moi case
    assert rc.nen_mua_qua_nut("S", "p", bay_gio=1000.0 + rc.MUA_LAI_SAU)    # weekly test het han: mua lai
    assert rc.nen_mua_qua_nut("S2", "p", bay_gio=1000.0)                     # may khac chua mua
    rc._DA_MUA_QUA_NUT.clear()
