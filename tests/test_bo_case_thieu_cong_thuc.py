"""Tab rating: case dau bao app chua co cong thuc gen -> cac case sau can gen cung loai bo qua, khong chay."""
from rcr import bo_case_thieu_cong_thuc as t

KQ_THIEU = {"verdict": "NEEDS_HUMAN", "runs": [{"drive": {"status": "NEEDS_HUMAN", "steps": [
    {"action": {"reason": "tool dừng ở bước rating: app chưa có công thức gen anh trong data/rating_gen.yaml"}}]}}]}


def test_doc_loai_thieu_tu_ket_qua_case():
    assert t.loai_thieu(KQ_THIEU) == {"anh"}
    assert t.loai_thieu({"verdict": "PASS"}) == set() and t.loai_thieu(None) == set()


def test_case_can_gen_cung_loai_thi_bo():
    gen_anh = {"actions": ["Mở app vào Home", "Gen ảnh, chờ popup."], "precondition": ""}
    gen_video = {"actions": ["Gen video, chờ popup."], "precondition": ""}
    home = {"actions": ["Mở app vào Home", "Bấm back trên Home"], "precondition": ""}
    assert "chưa có công thức gen anh" in t.ly_do_bo(gen_anh, {"anh"}, set())
    assert t.ly_do_bo(gen_video, {"anh"}, set()) == ""        # loai khac chua biet thieu -> van chay
    assert t.ly_do_bo(home, {"anh"}, set()) == ""             # case khong gen -> van chay


def test_case_tiep_noi_case_da_bo_cung_bo():
    noi = {"actions": ["Chọn 3 sao"], "precondition": "Tiếp nối RATING-R01-02"}
    assert "tiếp nối RATING-R01-02" in t.ly_do_bo(noi, {"anh"}, {"rating#RATING-R01-02"})
    assert t.ly_do_bo(noi, {"anh"}, set()) == ""


def test_record_bo_qua_giu_du_dong_expected_cho_do_tay():
    rec = t.record_bo_qua("rating#R01-03", {"label": "#R01-03 Result — chọn sao"},
                          {"expects": ["Popup hiện", "X sau 2s"]}, "app chưa có công thức gen anh")
    assert rec["verdict"] == "NEEDS_HUMAN" and len(rec["lines"]) == 2
    assert rec["actual"].startswith("không chạy")
