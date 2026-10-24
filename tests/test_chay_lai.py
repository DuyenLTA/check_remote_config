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
