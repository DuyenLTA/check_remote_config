"""Ghi ket qua cham tay vao record cua file luot."""

from __future__ import annotations

import pytest

from rcr import cham_tay
from rcr.models import RcError

REC = {"key": "3.4.0#UI-001", "verdict": "NEEDS_HUMAN", "pending": 2, "lines": [
    {"v": "NEEDS_HUMAN", "e": "Ảnh full-screen", "r": "chưa lái tới"},
    {"v": "PASS", "e": "Title đúng", "r": "thấy title"},
    {"v": "NOT_VERIFIABLE", "e": "Requests trên console", "r": "PO", "scope": "po"},
    {"v": "NOT_VERIFIABLE", "e": "Progress mượt", "r": "nhìn mắt"},
]}


def test_cham_het_dong_con_mo_thi_case_pass_va_giu_dau_vet():
    ra = cham_tay.cham(REC, [1, 4], "PASS", "screencap: ảnh phủ kín 1080x2400")
    assert ra["verdict"] == "PASS" and ra["pending"] == 0
    assert ra["lines"][0]["r"].startswith("Claude chấm tay: screencap")
    assert [c["dong"] for c in ra["cham_tay"]] == [1, 4]
    assert REC["lines"][0]["v"] == "NEEDS_HUMAN"          # khong sua record goc


def test_mot_dong_fail_thi_case_fail_dong_po_khong_tinh():
    ra = cham_tay.cham(REC, [1], "FAIL", "progress ở giữa màn, y=1200")
    assert ra["verdict"] == "FAIL"


def test_con_dong_chua_cham_thi_case_chua_pass():
    ra = cham_tay.cham(REC, [1], "PASS", "ok")
    assert ra["verdict"] == "NOT_VERIFIABLE" and ra["pending"] == 1


def test_precondition_khong_dat_thi_van_blocked():
    ra = cham_tay.cham({**REC, "precondition_thieu": ["throttle"]}, [1, 4], "PASS", "ok")
    assert ra["verdict"] == "BLOCKED"


@pytest.mark.parametrize("dong,ket,ly_do,loi", [
    ([9], "PASS", "x", "chỉ có 4 dòng"),
    ([1], "OK", "x", "--ket"),
    ([1], "PASS", "  ", "--ly-do"),
])
def test_tham_so_sai_thi_bao_ro(dong, ket, ly_do, loi):
    with pytest.raises(RcError, match=loi):
        cham_tay.cham(REC, dong, ket, ly_do)


def test_so_dong():
    assert cham_tay.so_dong("1, 3") == [1, 3]
    with pytest.raises(RcError):
        cham_tay.so_dong("0")
    with pytest.raises(RcError):
        cham_tay.so_dong("a")
