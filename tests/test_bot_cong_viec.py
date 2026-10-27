"""Soan tin + goi rcr-cai-build cua bot. Khong can Discord / may."""

from __future__ import annotations

import pytest

from rcr import bot_cong_viec as v

CASE = {"ma": "AIP882", "ten": "AI-Video", "version": "4.3.0 (40)",
        "package": "com.aivideogenerator.aiphotoeditor.beautyeditor.imagetoimage",
        "loai_ban": "debug", "link_tin": "https://discord.com/channels/1/2/3"}


@pytest.mark.parametrize("loai, chu", [("debug", "note `debug`"), ("release", "bản release")])
def test_tin_hoi_co_link_tin_goc_va_loai_ban(loai, chu):
    t = v.tin_hoi({**CASE, "loai_ban": loai})
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
