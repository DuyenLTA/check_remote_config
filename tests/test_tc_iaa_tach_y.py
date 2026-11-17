"""Moi y cua cot Ad description thanh mot dong Expected rieng (user chot 17/11/2026, mo ta AIP921 / AIP935)."""

from __future__ import annotations

from rcr.tc_iaa_tach_y import dong_expected, y_cua_dong


def test_danh_sach_man_tach_moi_man_mot_dong():
    d = "- Preload ads tại màn Tập luyện · Home, Dinh dưỡng · AI Scan, Thực đơn gợi ý, Công thức món"
    assert y_cua_dong(d) == ["↳ - Preload ads tại màn Tập luyện · Home", "↳ - Preload ads tại màn Dinh dưỡng · AI Scan",
                             "↳ - Preload ads tại màn Thực đơn gợi ý", "↳ - Preload ads tại màn Công thức món"]


def test_ngoac_khong_bi_cat_va_tu_dan_trong_ngoac_khong_tinh():
    d = ("- Hiển thị ads khi user click bất kỳ button nào ở Home (bấm Xem tất cả; hub, mở màn danh sách), "
         "AI Scan (bấm Scan), Công thức món")
    assert y_cua_dong(d) == ["↳ - Hiển thị ads khi user click bất kỳ button nào ở Home (bấm Xem tất cả; hub, mở màn danh sách)",
                             "↳ - Hiển thị ads khi user click bất kỳ button nào ở AI Scan (bấm Scan)",
                             "↳ - Hiển thị ads khi user click bất kỳ button nào ở Công thức món"]


def test_su_kien_reload_tach_ca_hoac():
    assert y_cua_dong("Reload khi user hide app, click vào ad hoặc trở về từ màn ads") == [
        "↳ Reload khi user hide app", "↳ Reload khi click vào ad", "↳ Reload khi trở về từ màn ads"]


def test_key_remote_config_tach_tung_key():
    d = "- Remote config: a_b = 3 (lượt free), c_d = 2 (số ads)"
    assert y_cua_dong(d) == ["↳ - Remote config: a_b = 3 (lượt free)", "↳ - Remote config: c_d = 2 (số ads)"]


def test_cau_van_nhieu_ve_khong_doan_tien_to_ma_nhac_du_ve():
    d = "*Reload logic: Tại màn why do u uninstall, reload khi user click chọn lý do xóa app"
    assert y_cua_dong(d) == []
    ra = dong_expected(d)
    assert ra[0] == d and ra[1].startswith("↳ Đủ từng vế")
    assert "Tại màn why do u uninstall | reload khi user click chọn lý do xóa app" in ra[1]


def test_dong_mot_y_giu_nguyen():
    assert dong_expected("- Reload mỗi 10s\n\n- Khoảng cách giữa các ads inter: 30s") == [
        "- Reload mỗi 10s", "- Khoảng cách giữa các ads inter: 30s"]
