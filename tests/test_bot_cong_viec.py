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


def test_cli_loi_lay_dong_LOI(monkeypatch):
    class P:
        returncode, stdout = 1, ""
        stderr = "May: x\nLOI: 4.3.0 (40) chưa có bản debug (mới có: release)\n"
    goi = {}
    monkeypatch.setattr(v.subprocess, "run", lambda cmd, **k: goi.setdefault("cmd", cmd) and P)
    assert v.cai("pkg.a", "4.3.0 (40)", "debug", "SER1") == {"loi": "4.3.0 (40) chưa có bản debug (mới có: release)"}
    assert goi["cmd"][-2:] == ["--serial", "SER1"]                   # dung may bot da chon
