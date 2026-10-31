"""Precondition doi hang may / doi ad no-fill (bo TC 3.6.1, AIP886 31/10/2026)."""

from __future__ import annotations

from rcr import precond_guards as p


def test_thiet_bi_oppo_ma_chay_tren_pixel_thi_thieu_dieu_kien():
    assert p.thieu_may("1. Thiết bị OPPO.  2. Clear data.", "google", "Pixel 6") == [
        "cần máy OPPO, máy đang chạy là google Pixel 6"]


def test_dung_hang_may_hoac_khong_doi_hang_thi_khong_thieu():
    assert p.thieu_may("1. Thiết bị OPPO.", "OPPO", "CPH2375") == []
    assert p.thieu_may("Máy Pixel", "google", "Pixel 6") == []
    assert p.thieu_may("1. Clear data.", "google", "Pixel 6") == []
    # "may test" khong phai ten hang
    assert p.thieu_may("Máy test đã đăng ký AdMob", "google", "Pixel 6") == []


def test_lam_303_no_fill_la_dieu_kien_ep_duoc():
    pre = "1. Clear data.  2. Làm 303 no-fill (ID test no-fill hoặc chặn ad request 303) trước khi vào OB3."
    assert p.ep_duoc(pre) == ["ép ad không fill"]
