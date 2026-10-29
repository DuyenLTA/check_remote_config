"""Cai build debug tu link Google Drive QA gui: urlopen / adb gia, khong cham mang that."""

from __future__ import annotations

import asyncio
import io
import zipfile
from datetime import datetime
from pathlib import Path

import pytest

from rcr import app_tester_ui
from rcr import cai_apk_tu_drive as d

ID = "1AbCdEfGhIjKlMnOpQrStUvWxYz"


@pytest.mark.parametrize("chu, link", [
    (f"bản debug đây <https://drive.google.com/file/d/{ID}/view?usp=sharing>",
     f"https://drive.google.com/file/d/{ID}/view?usp=sharing"),
    (f"https://drive.google.com/open?id={ID}", f"https://drive.google.com/open?id={ID}"),
    ("không có link", ""), ("https://drive.google.com/drive/folders", ""),
])
def test_tim_link(chu, link):
    assert d.tim_link(chu) == link
    if link:
        assert d.file_id(link) == ID


def _apk_bytes(manifest=True) -> bytes:
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        z.writestr("AndroidManifest.xml" if manifest else "x.txt", "m")
        z.writestr("pad.bin", b"\0" * (d.CO_TOI_THIEU + 10))
    return b.getvalue()


class _Resp(io.BytesIO):
    def __init__(self, data, loai="application/vnd.android.package-archive"):
        super().__init__(data)
        self.headers = {"Content-Type": loai}

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_tai_apk_hop_le(tmp_path, monkeypatch):
    goi = []
    monkeypatch.setattr(d.urllib.request, "urlopen", lambda req, timeout: goi.append(req.full_url) or _Resp(_apk_bytes()))
    f = d.tai(f"https://drive.google.com/file/d/{ID}/view", tmp_path)
    assert f.name == f"drive-{ID}.apk" and ID in goi[0] and "confirm=t" in goi[0]


@pytest.mark.parametrize("resp, loi", [
    (_Resp(b"<html>", "text/html; charset=utf-8"), "Ai có link"),
    (_Resp(b"PK nho"), "không phải APK"),
])
def test_tai_loi_ro_rang(tmp_path, monkeypatch, resp, loi):
    monkeypatch.setattr(d.urllib.request, "urlopen", lambda req, timeout: resp)
    with pytest.raises(d.LoiDrive, match=loi):
        d.tai(f"https://drive.google.com/file/d/{ID}/view", tmp_path)


def test_zip_khong_co_manifest_khong_phai_apk(tmp_path, monkeypatch):
    monkeypatch.setattr(d.urllib.request, "urlopen", lambda req, timeout: _Resp(_apk_bytes(manifest=False)))
    with pytest.raises(d.LoiDrive, match="AndroidManifest"):
        d.tai(f"https://drive.google.com/file/d/{ID}/view", tmp_path)


class _Adb:
    def __init__(self, ket_qua):
        self.ket_qua, self.lenh = list(ket_qua), []

    async def _run(self, *a, timeout=None):
        self.lenh.append(a)
        return self.ket_qua.pop(0), "", 0

    async def shell(self, serial, *a):
        self.lenh.append(a)
        return "", "", 0


def _gia(monkeypatch, cac_ban):
    monkeypatch.setattr(d, "tai", lambda link, thu_muc: Path("x.apk"))
    trang_thai = list(cac_ban)

    async def ban_dang_cai(*a):
        return trang_thai.pop(0)
    monkeypatch.setattr(d, "ban_dang_cai", ban_dang_cai)


CU = {"version": "3.7.0 (30)", "debuggable": False, "cai_luc": datetime(2026, 10, 28, 18, 38)}
MOI = {"version": "3.7.0 (30)", "debuggable": True, "cai_luc": datetime(2026, 10, 29, 16, 30)}


def test_cai_de_ban_cu_khac_chu_ky_thi_go_roi_cai_lai(monkeypatch):
    _gia(monkeypatch, [CU, MOI])
    adb = _Adb(["Failure [INSTALL_FAILED_UPDATE_INCOMPATIBLE: signatures do not match]", "Success"])
    kq = asyncio.run(d.cai(adb, "S1", "pkg.a", "3.7.0 (30)", "link", Path(".")))
    assert ("pm", "uninstall", "pkg.a") in adb.lenh and kq["go_ban_cu"] and kq["debuggable"] and kq["nguon"] == "drive"


def test_apk_sai_version_thi_dung(monkeypatch):
    _gia(monkeypatch, [CU, {**MOI, "version": "3.6.0 (29)"}])
    with pytest.raises(app_tester_ui.LoiCai, match="APK trên Drive là 3.6.0 \\(29\\), tin build là 3.7.0 \\(30\\)"):
        asyncio.run(d.cai(_Adb(["Success"]), "S1", "pkg.a", "3.7.0 (30)", "link", Path(".")))


def test_apk_khac_package_thi_may_van_ban_cu_va_dung(monkeypatch):
    _gia(monkeypatch, [CU, CU])                                        # cai xong pkg.a khong doi
    with pytest.raises(app_tester_ui.LoiCai, match="không phải package pkg.a"):
        asyncio.run(d.cai(_Adb(["Success"]), "S1", "pkg.a", "3.7.0 (30)", "link", Path(".")))


def test_loi_tai_drive_thanh_loi_cai(monkeypatch):
    def hong(link, thu_muc):
        raise d.LoiDrive("Drive trả HTTP 404")
    monkeypatch.setattr(d, "tai", hong)
    with pytest.raises(app_tester_ui.LoiCai, match="HTTP 404"):
        asyncio.run(d.cai(_Adb([]), "S1", "pkg.a", "3.7.0 (30)", "link", Path(".")))
