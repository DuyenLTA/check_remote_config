"""Thoi gian chay tren report."""

from rcr import report_row, thoi_gian


def test_dinh_dang_ngan():
    assert thoi_gian.ngan(75) == "1:15" and thoi_gian.ngan(3725) == "1:02:05"
    assert thoi_gian.ngan(None) == "" and thoi_gian.ngan(0) == "0:00"


def test_tong_luot_tinh_ca_case_cu_chua_do():
    recs = [{"thoi_gian_s": 300}, {"thoi_gian_s": 420}, {}]
    assert thoi_gian.tong_luot(recs) == "12:00 · TB 6:00/case (2 case) · 1 case từ lượt cũ chưa đo"
    assert thoi_gian.tong_luot([{}]) == "—"


def test_the_case_tren_report_co_thoi_gian():
    assert report_row.build({"key": "3.6.1#SDK361-R01-01", "thoi_gian_s": 372})["tg"] == "6:12"
    assert report_row.build({"key": "3.6.1#SDK361-R01-01"})["tg"] == ""
