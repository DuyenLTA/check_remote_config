"""Mo thang trang app trong App Tester bang deep link (khong cuon ~93 app tim bundle)."""
from __future__ import annotations

import asyncio
import types

from rcr import app_tester_link as L

PKG = "com.aiphotogenearator.aivideogenerator.photogallery"
APP_ID = "1:431901144142:android:6a83356982c018d0067f1f"


def test_cache_ghi_doc_va_bo_gia_tri_la(tmp_path):
    f = tmp_path / "ids.json"
    assert L.doc(PKG, f) == ""
    L.ghi(PKG, APP_ID, f)
    L.ghi("com.khac", "khong-phai-app-id", f)
    assert L.doc(PKG, f) == APP_ID and L.doc("com.khac", f) == ""


def _node(rid, text=""):
    return types.SimpleNamespace(resource_id=rid, text=text)


class _Adb:
    def __init__(self):
        self.lenh = []

    async def shell(self, serial, *args):
        self.lenh.append(" ".join(args))
        return "", "", 0


def _chay(man_lan_luot, monkeypatch, app_id=APP_ID):
    monkeypatch.setattr(L, "guard", lambda *a: None)
    monkeypatch.setattr(L, "CHO_MO_S", 0)
    hang = list(man_lan_luot)

    async def doc_man(client, serial):
        return hang.pop(0) if len(hang) > 1 else hang[0]
    adb = _Adb()
    ra = asyncio.run(L.mo(adb, "S", PKG, app_id, doc_man, lambda n: n[0].text if n else ""))
    return ra, adb


def test_link_mo_dung_trang_app(monkeypatch):
    trang = [_node("man", "chi_tiet"), _node("bundle_id", PKG)]
    ra, adb = _chay([[_node("man", "danh_sach")], trang], monkeypatch)
    assert ra is trang
    assert adb.lenh[0] == ("am start -a android.intent.action.VIEW -d "
                           f"https://appdistribution.firebase.google.com/testerapps/{APP_ID} dev.firebase.appdistribution")


def test_link_ra_trang_app_khac_thi_tra_none_de_cuon_tim(monkeypatch):
    ra, _ = _chay([[_node("man", "chi_tiet"), _node("bundle_id", "com.khac")]], monkeypatch)
    assert ra is None


def test_man_consent_cua_app_moi_van_nhan(monkeypatch):
    consent = [_node("man", "consent")]
    assert _chay([consent], monkeypatch)[0] is consent


def test_khong_biet_app_id_thi_khong_mo_link(monkeypatch):
    ra, adb = _chay([[_node("man", "chi_tiet")]], monkeypatch, app_id="")
    assert ra is None and adb.lenh == []
