"""Tab tinh nang (rating / widget / daily checkin / IAA / gen ngam) lai vao Home truoc; tab SDK FO test o tutorial."""

from rcr.run_batch import la_tab_tinh_nang


def test_tab_tinh_nang_la_tab_khong_mang_so_phien_ban():
    for key in ("rating#RATING-R01-01", "widget#WG-R01-01", "daily checkin#DC-01", "Test Cases#IAA-01-01",
                "TC Gen ngầm#GEN-R01-01"):
        assert la_tab_tinh_nang(key), key


def test_tab_sdk_fo_va_key_khong_tab_khong_tinh():
    for key in ("3.6.1#SDK361-R02-03", "SDK 3.5.4#OB2-001", "TC SDK 3.7.2#X-01", "RATING-R01-01", "#R01"):
        assert not la_tab_tinh_nang(key), key
