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
          {"key": "A-2", "case": "HT-03", "loai_ban_goc": "debug"},
          {"key": "A-3", "case": "daily checkin#4", "loai_ban_goc": "debug"},
          {"key": "A-4", "case": "SDK350-OB3X-013", "loai_ban_goc": "release"}]
    chay, bo = v.phan_loai(uv, "debug")
    assert [u["key"] for u in chay] == ["A-1", "A-3"]
    assert [(u["key"], "Next-Gen" in ly or "release" in ly) for u, ly in bo] == [("A-2", True), ("A-4", True)]


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
    assert "**AIP882---AI-Video v4.3.0 (40)**" in t and "**AIP920-14** — Inter khong hien" in t and "<https://j/AIP920-14>" in t
