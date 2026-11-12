"""Cham dong Expected ghi thang ID ads (bo case IAA dung tu sheet KT)."""

from rcr import assert_ad_theo_id as t
from rcr.assert_check import check_all

H = "ca-app-pub-4584260126367940/5560105865"
T = "ca-app-pub-4584260126367940/6465993422"
XONG = {"status": "DONE", "walked": True}
DUNG = {"status": "NEEDS_HUMAN", "stopped_at": 1, "walked": True}


def u(unit, typ="native", req=1, load=0, show=0):
    return {"unit": unit, "type": typ, "requested": req, "loaded": load, "shown": show, "rc_keys": []}


OB1 = u("*****849", load=1)  # native OB1 cua luong FO - khong phai unit Loading


def test_khang_dinh_kem_dieu_kien_khong_bi_doc_thanh_phu_dinh():
    dong = f"Request ads đúng unit high {H} trước; high không fill thì gọi unit thường {T}."
    assert t._vai(dong) == {"5560105865": "bat_buoc", "6465993422": "tuy"}
    assert t.cham(dong, [OB1, u("*****865")], XONG)["verdict"] == "PASS"
    # Chi co request cua man khac + tool dung giua chung -> chua ket luan, khong FAIL "van co request"
    assert t.cham(dong, [OB1], DUNG)["verdict"] == "NEEDS_HUMAN"
    assert t.cham(dong, [OB1], XONG)["verdict"] == "FAIL"


def test_chi_thuong_cam_high():
    dong = f"Chỉ request unit thường {T}, không request unit high {H}."
    assert t.cham(dong, [u("*****422")], XONG)["verdict"] == "PASS"
    assert t.cham(dong, [u("*****422"), u("*****865")], XONG)["verdict"] == "FAIL"
    assert t.cham(dong, [OB1], XONG)["verdict"] == "FAIL"


def test_tat_remote_ca_hai_trong_ngoac():
    dong = f"Không request unit nào của vị trí ({H}, {T})."
    assert t._vai(dong) == {"5560105865": "cam", "6465993422": "cam"}
    assert t.cham(dong, [OB1], XONG)["verdict"] == "PASS"
    assert t.cham(dong, [OB1], DUNG)["verdict"] == "NEEDS_HUMAN"
    assert t.cham(dong, [u("*****422")], XONG)["verdict"] == "FAIL"


def test_dong_hien_thi_chi_tinh_unit_cua_case():
    expects = [f"Chỉ request unit high {H}, không request unit thường {T}.",
               "Có fill thì Native vẫn hiển thị tại Loading."]
    ads = {"units": {"a": OB1}}
    kq = check_all(expects, ads, DUNG, {})
    # Truoc day: dong 1 FAIL "van co request", dong 2 PASS nho native OB1.
    assert [r["verdict"] for r in kq["lines"]] == ["NEEDS_HUMAN", "NEEDS_HUMAN"]
    ads = {"units": {"a": OB1, "b": u("*****865", show=1)}}
    kq = check_all(expects, ads, XONG, {})
    assert [r["verdict"] for r in kq["lines"]] == ["PASS", "PASS"]


def test_dong_khong_hien_thi_cua_case_tat():
    expects = [f"Không request unit nào của vị trí ({H}, {T}).",
               "Không preload, không hiển thị Native tại Loading."]
    kq = check_all(expects, {"units": {"a": OB1}}, XONG, {})
    assert [r["verdict"] for r in kq["lines"]] == ["PASS", "PASS"]
    kq = check_all(expects, {"units": {"a": OB1, "b": u("*****865")}}, XONG, {})
    assert [r["verdict"] for r in kq["lines"]] == ["FAIL", "FAIL"]
