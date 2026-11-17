"""Case dau chuoi tool dung giua chung -> case 'Tiep noi' khong lai nua (AIP892 checkin 16/11/2026)."""

from rcr import run_batch as rb


def test_dau_chuoi_dung_giua_chung_thi_bo_ca_chuoi():
    kq = {"verdict": "NEEDS_HUMAN", "runs": [{"assert": {"lines": [
        {"verdict": "NEEDS_HUMAN", "reason": "tool dừng ở bước daily checkin: không vào được sheet unlock"}]}}]}
    assert rb.dung_giua_chung(kq)
    assert not rb.dung_giua_chung({"verdict": "FAIL", "runs": kq["runs"]})
    sau = {"precondition": "1. Tiếp nối CHECKIN-R01-04 (cùng lượt, không clear data)."}
    assert "dừng giữa chừng" in rb.ly_do_dau_chuoi_hong(sau, {"daily checkin#CHECKIN-R01-04"})
    assert rb.ly_do_dau_chuoi_hong(sau, set()) == ""
