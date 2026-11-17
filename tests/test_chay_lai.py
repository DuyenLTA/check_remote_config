"""Khi nao case chua ra PASS/FAIL thi khong chay lai nua."""

from __future__ import annotations

from rcr import chay_lai


def _kq(*lines, verdict="NOT_VERIFIABLE", run_verdict="NOT_VERIFIABLE"):
    return {"verdict": verdict,
            "runs": [{"verdict": run_verdict, "assert": {"lines": [
                {"n": i, **l} for i, l in enumerate(lines, 1)]}}]}


MAT = {"verdict": "NOT_VERIFIABLE", "reason": "phải nhìn mắt", "tinh": True}
CHUA_TOI = {"verdict": "NEEDS_HUMAN", "reason": "chưa lái tới màn"}
DAT = {"verdict": "PASS", "reason": "ok"}
PO = {"verdict": "NOT_VERIFIABLE", "reason": "console", "scope": "po"}


def test_chi_con_dong_nhin_mat_thi_khong_chay_lai():
    """Piclux SPLA-002 24/10/2026: 2 dong nhin mat, chay 2 lan ra y het."""
    assert "câu chữ" in chay_lai.ly_do_khong_chay_lai(_kq(DAT, MAT, PO), None)


def test_con_dong_do_duoc_thi_lan_dau_van_chay_lai():
    assert chay_lai.ly_do_khong_chay_lai(_kq(MAT, CHUA_TOI, verdict="NEEDS_HUMAN"), None) == ""


def test_hai_lan_y_het_thi_dung():
    kq = _kq(MAT, CHUA_TOI, verdict="NEEDS_HUMAN")
    assert "y hệt" in chay_lai.ly_do_khong_chay_lai(kq, chay_lai.dau_van(kq))


def test_lan_sau_khac_lan_truoc_thi_chay_tiep():
    truoc = chay_lai.dau_van(_kq(CHUA_TOI, verdict="NEEDS_HUMAN"))
    sau = _kq({**CHUA_TOI, "reason": "chưa lái tới màn OB2"}, verdict="NEEDS_HUMAN")
    assert chay_lai.ly_do_khong_chay_lai(sau, truoc) == ""


def test_blocked_vi_dieu_kien_lan_chay_thi_van_chay_lai():
    """Config bi fetch de: lan sau co the khac du dong y het."""
    kq = _kq(MAT, verdict="NOT_VERIFIABLE", run_verdict="BLOCKED")
    assert chay_lai.ly_do_khong_chay_lai(kq, chay_lai.dau_van(kq)) == ""
    assert chay_lai.ly_do_khong_chay_lai(_kq(MAT, verdict="BLOCKED"), None) == ""


def test_ly_do_tat_dinh_thi_khong_chay_lai_ngay_lan_1():
    """16/11/2026: 'khong co shortcut', 'chua co cong thuc', man Result khong dump... lan 2 luon y het -> bo ngay."""
    from rcr import chay_lai
    kq = {"verdict": "NEEDS_HUMAN", "runs": [{"verdict": "NEEDS_HUMAN", "assert": {"lines": [
        {"n": 1, "verdict": "PASS", "reason": "ok"},
        {"n": 2, "verdict": "NEEDS_HUMAN", "reason": "tool dừng ở bước rating: app không có shortcut Rating để mở"}]}}]}
    assert "lặp chắc chắn" in chay_lai.ly_do_khong_chay_lai(kq, None)
    kq["runs"][0]["assert"]["lines"][1]["reason"] = "chưa chụp được màn sau bước cuối"
    assert chay_lai.ly_do_khong_chay_lai(kq, None) == ""


def test_ly_do_do_duoc_chua_tung_doi_ket_qua_thi_khong_chay_lai():
    """Do 13-17/11/2026: cac ly do nay chay lai 60+ lan khong lan nao ra PASS/FAIL."""
    for ly_do in ("chưa thấy popup Add Widget ở màn nào trước đó — không có gì để đối chiếu",
                  "tool dừng ở bước rating: gen anh không tới được result: bấm Confirm; hết giờ",
                  "khung chụp đầu tiên (3s sau popup) đã có X — chụp bắt đầu trễ, chưa đo",
                  "tool dừng ở bước 1 (chưa làm được thao tác), chưa tới màn cần chấm"):
        kq = _kq(DAT, {"verdict": "NEEDS_HUMAN", "reason": ly_do}, verdict="NEEDS_HUMAN")
        assert "lặp chắc chắn" in chay_lai.ly_do_khong_chay_lai(kq, None), ly_do


def test_khong_thay_popup_rating_van_chay_lai():
    """Ly do nay chay lai ra PASS/FAIL 7/20 lan -> giu chay lai."""
    kq = _kq({"verdict": "NEEDS_HUMAN", "reason": "tool dừng ở bước rating: không thấy popup/màn Rating để chọn sao"},
             verdict="NEEDS_HUMAN")
    assert chay_lai.ly_do_khong_chay_lai(kq, None) == ""
