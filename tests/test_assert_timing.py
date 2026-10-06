"""Test cham dong thoi gian OB3. Thuan du lieu, khong can may.

Diem phai gac:
  - "tu chuyen sau Ns" do tu t0 = ad show (khong phai luc vao trang), +-1s
  - ad khong fill ma dong doi "ad show" -> KHONG cham theo t0 gia
  - man roi ngay sau cu vuot/bam cua TOOL -> khong tinh la app tu chuyen
  - nut X: kiem trong khoang giua khung cuoi chua thay va khung dau thay
"""

from __future__ import annotations

from rcr import assert_timing as at
from rcr import ob3_log

V0 = 1000.0


def luot(roi=None, show=None, fail=None):
    events = [(V0, "vao")]
    if show:
        events.append((V0 + show, "show"))
    if fail:
        events.append((V0 + fail, "fail"))
    if roi:
        events.append((V0 + roi, "roi"))
    return ob3_log.luot_ghe(sorted(events))


def tl(roi=None, show=None, fail=None, khung=(), thao_tac=()):
    return {"luot": luot(roi, show, fail), "khung": list(khung),
            "thao_tac": [V0 + t for t in thao_tac]}


def v(res):
    return res["verdict"]


def test_tu_chuyen_dung_timer_tinh_tu_ad_show():
    r = at.cham("App tự chuyển màn tại ~t0+5s.", tl(roi=6.2, show=1.0), {"timer_auto_swipe": "5"})
    assert v(r) == "PASS" and "5.2s" in r["reason"]


def test_tu_chuyen_lech_timer_la_FAIL():
    r = at.cham("App tự chuyển màn tại ~t0+4s.", tl(roi=7.5, show=1.0), {"timer_auto_swipe": "4"})
    assert v(r) == "FAIL"


def test_khong_fill_thi_timer_do_tu_luc_ad_fail():
    """ID 303 nam cung trong app, khong ep fill duoc: khong ad thi SDK dem timer tu luc fail."""
    r = at.cham("Đúng ~5s kể từ t0 (khi ad show): app tự chuyển", tl(roi=9.0, fail=4.0),
                {"timer_auto_swipe": "5"})
    assert v(r) == "PASS" and "ad fail" in r["reason"]


def test_khong_ad_thi_timer_tinh_tu_luc_ad_fail():
    """Do that 06/10: fail +3.46s, roi +13.49s, timer 10 -> 10.03s."""
    r = at.cham("Hết timer: app tự chuyển sang màn kế tiếp (OB4).", tl(roi=13.49, fail=3.46),
                {"timer_auto_swipe": "10"})
    assert v(r) == "PASS"


def test_khong_tu_chuyen_ma_van_roi_la_FAIL():
    r = at.cham("App KHÔNG tự chuyển màn dù quá timer.", tl(roi=6.0, show=1.0),
                {"timer_auto_swipe": "5"})
    assert v(r) == "FAIL"


def test_dung_yen_qua_timer_roi_tool_vuot_thi_PASS():
    r = at.cham("App KHÔNG tự chuyển màn dù quá timer.", tl(roi=13.0, show=1.0, thao_tac=[12.5]),
                {"timer_auto_swipe": "5"})
    assert v(r) == "PASS"


def test_man_roi_do_tool_khong_tinh_la_app_tu_chuyen():
    r = at.cham("App tự chuyển màn tại ~t0+5s.", tl(roi=3.0, show=1.0, thao_tac=[2.5]),
                {"timer_auto_swipe": "5"})
    assert v(r) != "PASS"


def test_bam_x_thi_chuyen_ngay():
    r = at.cham("Bấm X → chuyển màn ngay.", tl(roi=4.2, show=1.0, thao_tac=[3.6]), {})
    assert v(r) == "PASS"


def test_chuyen_man_hai_lan_la_FAIL():
    t = tl(roi=6.0, show=1.0)
    t["luot"] += ob3_log.luot_ghe([(V0 + 6.5, "vao"), (V0 + 7.0, "roi")])
    assert v(at.cham("Chỉ chuyển màn đúng 1 lần.", t, {})) == "FAIL"


def khung(*cap):
    return [{"t": V0 + t, "x": x, "dem": d, "trang": 0} for t, x, d in cap]


def test_nut_x_hien_dung_timer():
    k = khung((2.0, False, "4"), (4.5, False, "1"), (6.5, True, ""))
    r = at.cham("Button X hiển thị tại ~t0+5s.", tl(roi=12, show=1.0, khung=k),
                {"timer_button_x": "5"})
    assert v(r) == "PASS"


def test_khong_hien_x_va_dem_nguoc_khi_tat_skip():
    k = khung((2.0, False, ""), (4.0, False, ""), (7.0, False, ""))
    r = at.cham("KHÔNG hiển thị số đếm ngược, KHÔNG hiển thị button X", tl(roi=12, show=1.0, khung=k),
                {"ob3_show_button_skip": "false"})
    assert v(r) == "PASS"


def test_x_khi_ad_khong_fill_ma_request_dung_303_thi_dat():
    k = khung((2.0, False, ""), (5.0, False, ""))
    r = at.cham("Button X hiển thị tại ~t0+5s.", tl(roi=12, fail=1.0, khung=k), {}, ["*****765"])
    assert v(r) == "PASS" and "*****765" in r["reason"]


def test_x_khi_khong_co_request_303_nao_la_FAIL():
    k = khung((2.0, False, ""), (5.0, False, ""))
    assert v(at.cham("Button X hiển thị tại ~t0+5s.", tl(roi=12, fail=1.0, khung=k), {})) == "FAIL"


def test_khong_fill_ma_x_van_hien_la_FAIL():
    k = khung((2.0, False, ""), (5.0, True, ""))
    assert v(at.cham("Button X hiển thị tại ~t0+5s.", tl(roi=12, fail=1.0, khung=k), {})) == "FAIL"


def test_dong_khong_ve_thoi_gian_thi_bo_qua():
    assert at.cham("Không crash.", tl(roi=6, show=1), {}) is None


def test_cua_so_theo_timer_lon_nhat():
    giay, nhin = at.cach_quan_sat({"timer_auto_swipe": "10", "timer_button_x": "2"},
                                  ["Button X hiển thị tại ~t0+2s."])
    assert giay == 15.0 and nhin


def test_auto_chuyen_du_x_chua_kip_hien_cham_theo_log():
    r = at.cham("Tại ~t0+3s: app AUTO CHUYỂN MÀN NGAY dù button X chưa kịp hiện (2 timer độc lập).",
                tl(roi=6.1, fail=3.0), {"timer_auto_swipe": "3", "timer_button_x": "5"})
    assert v(r) == "PASS" and "3.1s" in r["reason"]


def test_khong_hien_x_o_man_ke_soi_khung_sau_luc_roi():
    k = khung((2.0, False, "4"), (7.0, False, ""), (8.5, False, ""))
    r = at.cham("Countdown X bị hủy khi rời màn — không hiện X/không crash ở màn kế.",
                tl(roi=6.0, show=1.0, khung=k), {})
    assert v(r) == "PASS" and "2 khung" in r["reason"]


def test_bam_x_ma_ad_khong_fill_request_dung_thi_dat():
    r = at.cham("Bấm X → chuyển màn ngay.", tl(roi=6.0, fail=1.0), {}, ["*****989"])
    assert v(r) == "PASS" and "không fill" in r["reason"]


def test_o_lai_ob3_la_khong_tu_chuyen():
    r = at.cham("User ở lại OB3 cho đến khi tự thao tác.", tl(roi=16.0, fail=1.0, thao_tac=[15.6]),
                {"timer_auto_swipe": "5"})
    assert v(r) == "PASS"


def test_get_theo_timer_remote_la_dong_tu_chuyen():
    r = at.cham("Vẫn get theo giá trị remote config timer_auto_swipe.", tl(roi=6.0, fail=1.0),
                {"timer_auto_swipe": "5"})
    assert v(r) == "PASS"


def test_ad_moi_cham_o_lan_vao_ob3_sau():
    t = tl(roi=6.0, fail=1.0, khung=khung((20.0, False, "4"), (24.5, False, "1"), (26.4, True, "")))
    t["luot"] += ob3_log.luot_ghe([(V0 + 19.0, "vao"), (V0 + 20.5, "show"), (V0 + 40.0, "roi")])
    r = at.cham("X xuất hiện sau đủ 5s tính từ lúc ad mới show.", t, {"timer_button_x": "5"})
    assert v(r) == "PASS"


def test_ad_moi_khong_fill_request_dung_thi_dat():
    t = tl(roi=6.0, fail=1.0)
    t["luot"] += ob3_log.luot_ghe([(V0 + 19.0, "vao"), (V0 + 22.0, "fail")])
    r = at.cham("X xuất hiện sau đủ 5s tính từ lúc ad mới show.", t, {"timer_button_x": "5"},
                ["*****765"])
    assert v(r) == "PASS" and "không fill" in r["reason"]


def test_x_hien_ngay_co_ve_khong_dem_nguoc_khong_phai_cau_phu_dinh():
    """Do 2026-10-06 OB3X-004: cau khang dinh X hien bi doc thanh phu dinh -> PASS sai."""
    k = khung((1.5, False, ""), (3.0, False, ""))
    r = at.cham("Button X hiển thị NGAY từ đầu (không có số đếm ngược).", tl(roi=12, show=1.0, khung=k),
                {"timer_button_x": "0"})
    assert v(r) == "FAIL"
