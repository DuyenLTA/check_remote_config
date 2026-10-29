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


def test_luot_tay_tao_duoc_dieu_kien_thi_bo_precondition_thieu():
    ra = cham_tay.cham({**REC, "precondition_thieu": ["chặn ad server"]}, [1, 4], "PASS", "ok",
                       dieu_kien="chặn domain ad bằng Private DNS")
    assert ra["verdict"] == "PASS" and ra["precondition_thieu"] == []
    assert "Private DNS" in ra["ep_ad_fail"]


def test_record_cu_ghi_cham_tay_true_van_cham_duoc():
    ra = cham_tay.cham({**REC, "cham_tay": True}, [1, 4], "PASS", "ok")
    assert [c["dong"] for c in ra["cham_tay"]] == [1, 4]


def test_dieu_kien_dat_khong_go_ad_click():
    ra = cham_tay.cham({**REC, "ad_click": 2}, [1, 4], "PASS", "ok", dieu_kien="x")
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


def test_cham_tay_kem_anh_va_report_tach_ly_do(tmp_path):
    """29/10/2026: report kho nhin - case cham tay phai co anh + ket luan do tay o tren."""
    import io

    from PIL import Image

    from rcr import report_row
    f = tmp_path / "A_ob2.png"
    b = io.BytesIO()
    Image.new("RGB", (1080, 2400), "white").save(b, "PNG")
    f.write_bytes(b.getvalue())
    anh = cham_tay.doc_anh(str(f))
    assert anh[0]["ten"] == "A_ob2" and anh[0]["src"].startswith("data:image/jpeg;base64,")
    rec = {"key": "3.6.1#X-1", "verdict": "NEEDS_HUMAN", "actual": "lái 1 bước, dừng ở bước 1",
           "lines": [{"e": "OB2 'FR - OB2 title'", "v": "NEEDS_HUMAN", "r": "tool không dịch được bước"}]}
    moi = cham_tay.cham(rec, [1], "PASS", "lượt A: OB2 'FR - OB2 title'", anh=anh)
    moi = cham_tay.cham(moi, [1], "PASS", "lượt A lại", anh=anh)          # trung ten anh -> giu 1
    assert moi["verdict"] == "PASS" and len(moi["anh_tay"]) == 1
    d = report_row.build(moi)
    assert d["tay"] and d["anh_tay"][0]["ten"] == "A_ob2"
    assert d["lines"][0] == {"s": d["lines"][0]["s"], "v": "PASS", "r": "lượt A lại", "tay": "Claude"}
    assert report_row.build(rec)["lines"][0]["tay"] == "" and not report_row.build(rec)["tay"]


def test_anh_khong_ton_tai_thi_bao_loi(tmp_path):
    with pytest.raises(RcError, match="không thấy file ảnh"):
        cham_tay.doc_anh(str(tmp_path / "khong-co.png"))
