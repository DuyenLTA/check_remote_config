"""Logic thuan cua luot verify bug Reviewing."""

from __future__ import annotations

from rcr import bot_verify_jira as v


def _tin():
    bug = {"case": "3.6.1#1", "expected": "Hien inter", "thuc_te": "khong hien"}
    return {
        "1": {"ma": "AIP920", "loai_ban": "debug", "bugs": [bug, {"case": "HT-03"}], "jira": {"issues": [
            {"case": "3.6.1#1", "key": "AIP920-13", "link": "https://j/AIP920-13", "ghi_chu": "tao moi"},
            {"case": "HT-03", "key": "AIP920-14", "link": "", "ghi_chu": "tạo mới"},
            {"case": "3.6.1#2", "key": "AIP920-15", "ghi_chu": "trùng, đã cập nhật"},
            {"case": "3.6.1#3", "key": "", "ghi_chu": "bỏ qua: khong phai bug"}]}},
        "2": {"ma": "AIP920", "loai_ban": "release", "jira": {"issues": [
            {"case": "daily checkin#4", "key": "AIP920-16", "ghi_chu": "Tạo mới"},
            {"case": "3.6.1#1", "key": "AIP920-13", "ghi_chu": "tao moi"}]}},
        "3": {"ma": "AIP886", "jira": {"issues": [{"case": "a#1", "key": "AIP886-1", "ghi_chu": "tao moi"}]}},
        "4": {"ma": "AIP920", "jira": None},
    }


def test_ung_vien_chi_issue_bot_tao_moi_cung_ma():
    uv = {u["key"]: u for u in v.ung_vien(_tin(), "AIP920")}
    assert sorted(uv) == ["AIP920-13", "AIP920-14", "AIP920-16"]
    assert uv["AIP920-16"]["loai_ban_goc"] == "release"


def test_phan_loai():
    uv = [{"key": "A-1", "case": "3.6.1#SDK361-SPL-001", "loai_ban_goc": "debug"},
          {"key": "A-2", "case": "", "loai_ban_goc": ""},
          {"key": "A-3", "case": "daily checkin#4", "loai_ban_goc": "debug"},
          {"key": "A-4", "case": "SDK350-OB3X-013", "loai_ban_goc": "release"},
          {"key": "A-5", "case": "x y z", "loai_ban_goc": "debug"},
          {"key": "A-6", "case": "a#1", "loai_ban_goc": "debug", "package": "pkg.khac"}]
    chay, bo = v.phan_loai(uv, "debug", "pkg.a")
    assert [u["key"] for u in chay] == ["A-1", "A-3"]
    assert [(u["key"], ly) for u, ly in bo][0] == ("A-2", v.LY_DO_THIEU_MARKER)
    assert [u["key"] for u, _ in bo] == ["A-2", "A-4", "A-5", "A-6"]
    assert "release" in bo[1][1] and "package" in bo[3][1]


def test_checklist_chay_duoc_va_chi_mot_nhom_moi_luot():
    for ma in ("EV-07", "HT-03", "KT-02", "MED-02", "HV-01", "RG-01", "CMP-02", "1.7"):
        assert v.loai_case(ma) == "checklist", ma
    for xau in ("ev-07", "EV-07\n", "EV07", "HT-03; rm", "1.7.2", "", "EV-1234"):
        assert v.loai_case(xau) is None, xau
    assert v.loai_case("daily checkin#4") == "tc" and v.loai_case("SDK350-OB3X-013") == "tc"
    ck = lambda k, c: {"key": k, "case": c, "loai_ban_goc": "debug"}
    chay, bo = v.phan_loai([ck("A-1", "EV-07"), ck("A-2", "HT-03"), ck("A-3", "a#1")], "debug")
    assert [u["key"] for u in chay] == ["A-1", "A-2"] and [u["key"] for u, _ in bo] == ["A-3"]
    chay, bo = v.phan_loai([ck("A-1", "EV-07"), ck("A-3", "a#1")], "debug")     # hoa -> TC
    assert [u["key"] for u in chay] == ["A-3"] and "Verify bug Jira" in bo[0][1]
    # Bug tu ban debug verify duoc tren ban release (doi RC qua Firebase testvsl, 31/10/2026); nguoc lai thi khong.
    chay, bo = v.phan_loai([ck("A-1", "EV-07")], "release")
    assert [u["key"] for u in chay] == ["A-1"] and bo == []
    chay, bo = v.phan_loai([{**ck("A-1", "EV-07"), "loai_ban_goc": "release"}], "debug")
    assert chay == [] and "release" in bo[0][1]


def test_ket_luan_checklist_khop_sai_do_tay():
    u = {"case": "EV-07"}
    xong = lambda vd: {"trang_thai": "XONG", "cases": [{"case": "EV-07", "verdict": vd}]}
    assert v.ket_luan(xong("PASS"), u) == "PASS" and v.ket_luan(xong("KHOP"), u) == "PASS"
    assert v.ket_luan(xong("FAIL"), u) == "FAIL" and v.ket_luan(xong("SAI"), u) == "FAIL"
    for vd in ("DO_TAY", "KHONG_AP_DUNG", "NEEDS_HUMAN", ""):
        assert v.ket_luan(xong(vd), u) is None
    assert v.ket_luan({"trang_thai": "DUNG", "cases": xong("KHOP")["cases"]}, u) is None
    tc = {"trang_thai": "XONG", "cases": [{"case": "a#1", "verdict": "KHOP"}]}
    assert v.ket_luan(tc, {"case": "a#1"}) is None                  # KHOP chi doi cho dong checklist


def test_ket_luan_chi_khi_xong_va_verdict_dung():
    u = {"case": "a#1"}
    assert v.ket_luan({"trang_thai": "XONG", "cases": [{"case": "a#1", "verdict": "PASS"}]}, u) == "PASS"
    assert v.ket_luan({"trang_thai": "XONG", "cases": [{"case": "a#1", "verdict": "FAIL"}]}, u) == "FAIL"
    assert v.ket_luan({"trang_thai": "DUNG", "cases": [{"case": "a#1", "verdict": "PASS"}]}, u) is None
    assert v.ket_luan({"trang_thai": "XONG", "cases": [{"case": "a#1", "verdict": "pass"}]}, u) is None
    assert v.ket_luan({"trang_thai": "XONG", "cases": [{"case": "a#1", "verdict": "KHONG_ON_DINH"}]}, u) is None
    assert v.ket_luan({"trang_thai": "XONG", "cases": []}, u) is None


def test_comment_va_tin_cat_ngan():
    u = {"key": "AIP920-13", "link": "https://j/AIP920-13", "case": "a#1", "bug": {"expected": "x" * 5000}}
    job = {"ma": "AIP920", "version": "1.6.0 (8)", "loai_ban": "debug"}
    kq = {"link": "https://claude.ai/artifact/r", "cases": [{"case": "a#1", "thuc_te": "ok"}]}
    cm = v.noi_dung_comment(u, "PASS", job, kq, "Pixel 7")
    assert "PASS trên build 1.6.0 (8)" in cm and "Report: https://claude.ai/artifact/r" in cm and len(cm) < 1000
    dong = [("done", u, "")] + [("bo", {**u, "key": f"AIP920-{i}"}, "y" * 300) for i in range(30)]
    tin = v.tin_ket_qua(job, dong)
    assert len(tin) <= v.MAX_TIN and tin.startswith("🔁 **Verify bug Reviewing** — **AIP920**")


def test_tin_bao_dev_chi_bug_keo_to_do():
    u = {"key": "AIP920-14", "link": "https://j/AIP920-14", "case": "a#2", "bug": {"tieu_de": "Inter khong hien"}}
    job = {"ma": "AIP882", "ten": "AI-Video", "version": "4.3.0 (40)"}
    assert v.tin_bao_dev_fail(job, [("done", u, "")]) is None
    t = v.tin_bao_dev_fail(job, [("done", u, ""), ("todo", u, "")])
    assert "**AIP882---AI-Video v4.3.0 (40)**" in t and "Có 1 bug cần check trên Jira: AIP920-14" in t and t.startswith("🐞 **Nhờ dev check bug**")
    assert "Inter khong hien" not in t and "•" not in t
    u2 = {**u, "link": "https://jira.apero.vn/browse/AIP920-14"}
    assert t.replace("AIP920-14", "<https://jira.apero.vn/browse/AIP920>") == v.tin_bao_dev_fail(job, [("todo", u2, "")])


def test_tin_tom_tat_verify_chi_bug_dang_verify():
    """29/10/2026: tin duoi ghi so ca checklist ('1 Sai (EV-11)') -> QA tuong bug van FAIL du da Done."""
    job = {"verify": [{"key": "AIP922-106", "case": "MED-01", "bug": {}}]}
    kq = {"trang_thai": "XONG", "tom_tat": "24 Khớp, 1 Sai (EV-11), 19 Đo tay",
          "cases": [{"case": "MED-01", "verdict": "KHOP", "thuc_te": "4 adapter COMPLETE 10/10 lần mở lạnh"}]}
    t = v.tin_tom_tat_verify(job, kq)
    assert t == "• **AIP922-106** `MED-01`: **PASS** — 4 adapter COMPLETE 10/10 lần mở lạnh"
    assert "EV-11" not in t and "Đo tay" not in t
    dung = v.tin_tom_tat_verify(job, {"trang_thai": "DUNG", "tom_tat": "máy khoá", "cases": []})
    assert "chưa kết luận" in dung and "Lượt dừng: máy khoá" in dung
