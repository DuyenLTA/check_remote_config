"""Cau "(khong kill app)" la dieu kien, khong phai buoc kill (AIP892 RATING-R01-08 16/11/2026)."""

from rcr.act_compound import thao_tac_he_thong
from rcr.act_types import KillMoLai


def test_khong_kill_app_khong_lai_thanh_force_stop():
    assert thao_tac_he_thong("Sang màn khác rồi quay lại Home (không kill app).") is None
    assert isinstance(thao_tac_he_thong("Kill app, mở lại (session 2), vào Home."), KillMoLai)
