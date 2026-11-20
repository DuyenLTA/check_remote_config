"""Report Next-Gen tach dong 'khong ap dung' (app khong co) khoi dong 'tool khong lam duoc' (QA con phai lam)."""

from rcr.sdk_nextgen_ket import KHONG_AP_DUNG, KHOP, kq, khong_lam_duoc
from rcr import sdk_nextgen_report as rp


def test_phan_loai_theo_ly_do():
    assert khong_lam_duoc(kq("KT-05", "UMP", KHONG_AP_DUNG, "Không đo được trên bản release, không phải bug."))
    assert khong_lam_duoc(kq("CMP-01", "so bản", KHONG_AP_DUNG, "Bỏ theo yêu cầu (user chốt 15/10/2026): cần APK bản cũ"))
    assert khong_lam_duoc(kq("EV-26", "x", KHONG_AP_DUNG, "Chưa đo được (không phải bug): kho không fill native"))
    assert not khong_lam_duoc(kq("HT-08", "native list", KHONG_AP_DUNG, "Native danh sách chỉ có trong app"))
    assert not khong_lam_duoc(kq("KT-06", "UMP", KHONG_AP_DUNG, "Tài khoản AdMob chưa cấu hình form UMP"))
    assert not khong_lam_duoc(kq("HT-01", "banner", KHOP, "không đo được"))     # chi xet dong KHONG_AP_DUNG


def test_report_ghi_rieng_hai_so():
    data = {"meta": {"package": "a.b", "sdk": "3.7.2"}, "ket_qua": [
        kq("HT-01", "Banner", KHOP, "ok"),
        kq("HT-08", "Native list", KHONG_AP_DUNG, "Native danh sách chỉ có trong app"),
        kq("HV-09", "Collapsible", KHONG_AP_DUNG, "Không có collapsible banner trong luồng"),
        kq("KT-05", "UMP", KHONG_AP_DUNG, "Máy ở VN, không tạo được form EEA")]}
    h = rp.render(data)
    assert "<b>2</b> không áp dụng" in h and "<b>1</b> tool không làm được" in h
    assert h.index("Tool không làm được — QA còn phải tự làm (1)") < h.index("Không áp dụng — app không có (2)")
