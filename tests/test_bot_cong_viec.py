"""Soan tin + goi rcr-cai-build cua bot. Khong can Discord / may."""

from __future__ import annotations

import pytest

from rcr import bot_cong_viec as v

CASE = {"ma": "AIP882", "ten": "AI-Video", "version": "4.3.0 (40)",
        "package": "com.aivideogenerator.aiphotoeditor.beautyeditor.imagetoimage",
        "loai_ban": "debug", "link_tin": "https://discord.com/channels/1/2/3"}


@pytest.mark.parametrize("them, chu", [({"loai_ban": "debug"}, "note `debug`"),
                                       ({"loai_ban": "release", "next_gen": True}, "checklist Next-Gen"),
                                       ({"loai_ban": "release", "tutorial": "3.6.1"}, "testvsl")])
def test_tin_hoi_co_link_tin_goc_va_loai_ban(them, chu):
    t = v.tin_hoi({**CASE, **them})
    assert "AIP882" in t and "4.3.0 (40)" in t and chu in t and "channels/1/2/3" in t


def test_tin_ket_qua():
    t = v.tin_ket_qua(CASE, {"trang_thai": "XONG", "tom_tat": "12 PASS / 1 FAIL",
                             "link": "https://claude.ai/artifact/x", "phut": 31.5, "chi_phi": 4.2})
    assert t.startswith("✅") and "12 PASS" in t and "artifact/x" in t and "$4.20" in t


def test_co_link_artifact_thi_chi_gan_link_khong_dinh_kem(tmp_path):
    (tmp_path / "run.html").write_text("<html>", "utf-8")
    kq = {"trang_thai": "XONG", "link": "https://claude.ai/artifact/x"}
    assert v.file_report(kq, tmp_path) is None
    assert "Report: https://claude.ai/artifact/x" in v.tin_ket_qua(CASE, kq)


def test_khong_co_artifact_thi_dinh_kem_html_trong_out(tmp_path):
    f = tmp_path / "run-pkg.html"
    f.write_text("<html>", "utf-8")
    kq = {"trang_thai": "XONG", "link": str(f)}
    assert v.file_report(kq, tmp_path) == f.resolve()
    assert "run-pkg.html` đính kèm" in v.tin_ket_qua(CASE, kq, f)


def test_khong_dinh_kem_file_ngoai_out_hay_khong_phai_html(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    (tmp_path / "bi-mat.html").write_text("x", "utf-8")
    (out / "ket-qua.json").write_text("{}", "utf-8")
    for link in (str(tmp_path / "bi-mat.html"), str(out / "ket-qua.json"), str(out / "khong-co.html"), ""):
        assert v.file_report({"link": link}, out) is None, link


def test_cli_loi_lay_dong_LOI(monkeypatch):
    class P:
        returncode, stdout = 1, ""
        stderr = "May: x\nLOI: 4.3.0 (40) chưa có bản debug (mới có: release)\n"
    goi = {}
    monkeypatch.setattr(v.subprocess, "run", lambda cmd, **k: goi.setdefault("cmd", cmd) and P)
    assert v.cai("pkg.a", "4.3.0 (40)", "debug", "SER1") == {"loi": "4.3.0 (40) chưa có bản debug (mới có: release)"}
    assert goi["cmd"][-2:] == ["--serial", "SER1"]                   # dung may bot da chon


def test_duong_dan_tuong_doi_tinh_tu_repo(tmp_path, monkeypatch):
    """Luot AIP920: Claude ghi "out/sdk-.../report.html" (tuong doi), bot chay o thu muc khac van tim ra."""
    out = tmp_path / "repo" / "out"
    (out / "sdk-x").mkdir(parents=True)
    (out / "sdk-x" / "report.html").write_text("<html>", "utf-8")
    monkeypatch.chdir(tmp_path)
    f = v.file_report({"link": "out/sdk-x/report.html"}, out)
    assert f == (out / "sdk-x" / "report.html").resolve()
    assert v.file_report({"link": "out/../../bi-mat.html"}, out) is None


BUGS = [{"case": f"6.4.0#{i}", "tieu_de": "t" * 200, "precondition": "", "buoc": "", "expected": "e" * 300,
         "thuc_te": "a" * 300, "muc_do": "High"} for i in range(25)]


def test_lua_chon_bug_vua_gioi_han_discord():
    ds = v.lua_chon_bug(BUGS)
    assert [gt for gt, _, _ in ds] == [str(i) for i in range(25)]
    assert all(len(n) <= 100 and len(m) <= 100 for _, n, m in ds) and ds[0][1].startswith("6.4.0#0 · ")


def test_tin_bug_danh_dau_bug_da_tick_va_khong_qua_2000_ky_tu():
    t = v.tin_bug(BUGS[:2], [1])
    assert "☐ **1. " in t and "☑ **2. " in t and "> Case: `6.4.0#1`" in t and "Log Jira" in t
    assert len(v.tin_bug(BUGS)) <= 2000


def test_tin_bug_co_app_va_link_report_https():
    c = {"ma": "AIP938", "ten": "", "version": "2.2.0 (13)", "package": "pkg.a",
         "link_report": "https://claude.ai/artifact/x"}
    t = v.tin_bug(BUGS[:1], None, c)
    assert "**AIP938**" in t and "📄 [Mở report](https://claude.ai/artifact/x)" in t
    t = v.tin_bug(BUGS[:1], None, {**c, "link_report": "C:\\\\Users\\\\x\\\\report.html"})
    assert "Mở report" not in t                     # duong dan file tren may: khong dan len Discord
    assert "`report.html` đính kèm" in t and "Users" not in t   # bot dinh kem file, chi ghi ten file
    assert "đính kèm" not in v.tin_bug(BUGS[:1], None, {**c, "link_report": ""})
    assert len(v.tin_bug(BUGS, None, c)) <= 2000 and "Mở report" in v.tin_bug(BUGS, None, c)


def test_tin_jira_liet_ke_issue_va_loi():
    t = v.tin_jira({"issues": [{"case": "6.4.0#3", "key": "AIP920-7", "link": "https://j/AIP920-7",
                                "ghi_chu": "tạo mới"}], "loi": "bug 6.4.0#4: thiếu sprint", "chi_phi": 0.5}, 2)
    assert t.startswith("⚠️ Đã log 1/2 bug lên Jira") and "6.4.0#3 → AIP920-7" in t
    assert "(tạo mới)" in t and "⛔ Lỗi: bug 6.4.0#4: thiếu sprint" in t and "Chi phí: $0.50" in t


def test_tin_jira_lu_y_khong_hien_nhu_loi():
    t = v.tin_jira({"issues": [{"case": "TEST#1", "key": "AIP920-13", "link": "https://j/AIP920-13",
                                "ghi_chu": "tạo mới"}], "luu_y": "Board không có sprint active", "loi": ""}, 1)
    assert t.startswith("✅ Đã log 1/1 bug") and "Lưu ý: Board không có sprint active" in t and "⛔" not in t


def test_tin_bao_dev_co_project_va_link_jira():
    kq = {"issues": [{"case": "6.4.0#0", "key": "AIP882-7", "link": "https://j/AIP882-7", "ghi_chu": "tạo mới"},
                     {"case": "6.4.0#1", "key": "", "link": "", "ghi_chu": "bỏ qua: thiếu field"}]}
    t = v.tin_bao_dev({**CASE, "link_report": "https://claude.ai/artifact/x"}, kq, BUGS[:2])
    assert "bản build **AIP882---AI-Video v4.3.0 (40)**" in t
    assert "Đã log 1 bug lên Jira: AIP882-7" in t and "6.4.0#1" not in t
    assert "•" not in t and t.count("\n") == 1          # tong ket cuoi luot, khong liet ke tung bug
    # Link report chi bao o kenh QA, dev khong can.
    assert "claude.ai/artifact/x" not in t and "xác nhận" not in t and "Fix xong" not in t and len(t) <= 2000


def test_tin_bao_dev_khong_gui_khi_khong_co_issue():
    assert v.tin_bao_dev(CASE, {"issues": [{"case": "a", "key": "", "link": ""}]}, []) is None


def test_tin_da_cai_bao_nguon_va_may():
    c = {"ma": "AIP882", "ten": "AI-Video", "version": "4.4.0 (41)", "package": "p", "loai_ban": "debug"}
    t = v.tin_da_cai(c, "Pixel_7 (06K7)", "/rc-check")
    assert "App Tester" in t and "Pixel_7 (06K7)" in t and "/rc-check" in t and "debug" in t
    assert "link Drive" in v.tin_da_cai({**c, "drive": "https://drive"}, "x", "verify bug")
