"""Doi ngay may o man Cai dat > Ngay va gio tieng Viet (vivo V2143): nhan dung chu cong tac / muc ngay / thang sau."""

import re

from rcr import checkin_may


def test_nhan_chu_cai_dat_ngay_gio_tieng_viet():
    assert checkin_may.TU_DONG_RE.search("Tự động đặt giờ")
    assert not checkin_may.TU_DONG_RE.search("Tự động đặt múi giờ")
    assert re.search(checkin_may.NGAY_RE, "Ngày", re.I)
    assert not re.search(checkin_may.NGAY_RE, "Ngày và giờ", re.I)
    assert re.search(checkin_may.THANG_SAU_RE, "Tháng sau", re.I)
    assert re.search(checkin_may.NGAY_RE, "Date", re.I)
