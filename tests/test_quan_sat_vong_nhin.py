"""Vong nhin lien tuc (quan_sat.theo_doi): hai nguon khung khong duoc chan nhau.

Do 10/10/2026 Sorapix OB3X-001/004/005: `dumpsys activity top` treo ca cua so,
uiautomator chi duoc goi lai sau moi khung nhanh nen cung dung -> OB3 8,6s chi
co 1-2 khung, nut X "khong hien" -> FAIL oan.
"""

from __future__ import annotations

import asyncio

from rcr import quan_sat
from rcr.adb_parsers import AdbError


def _gia(monkeypatch, nhanh):
    async def screen_size(client, serial):
        return (1080, 2400)

    async def mot_khung(client, serial, package):
        await asyncio.sleep(0.05)
        return {"t": asyncio.get_running_loop().time(), "x": False, "dem": "", "trang": 0,
                "nguon": "uia"}, []

    monkeypatch.setattr(quan_sat.device_app, "screen_size", screen_size)
    monkeypatch.setattr(quan_sat, "mot_khung", mot_khung)
    monkeypatch.setattr(quan_sat, "khung_nhanh", nhanh)
    monkeypatch.setattr(quan_sat, "GIUA_HAI_UIA", 0.1)


def test_dumpsys_treo_thi_uiautomator_van_nhin_tiep(monkeypatch):
    async def nhanh_treo(client, serial, package, rong):
        await asyncio.sleep(5)              # treo qua ca cua so
        return None, None

    _gia(monkeypatch, nhanh_treo)
    khung: list = []
    asyncio.run(quan_sat.theo_doi(None, "s", "pkg", 0.6, khung))
    assert sum(k["nguon"] == "uia" for k in khung) >= 4


def test_dung_som_khi_uiautomator_thay_node(monkeypatch):
    async def nhanh(client, serial, package, rong):
        await asyncio.sleep(0.02)
        return {"t": 0.0, "x": False, "dem": "", "trang": 0, "nguon": "nhanh"}, None

    _gia(monkeypatch, nhanh)
    khung: list = []
    nodes = asyncio.run(quan_sat.theo_doi(None, "s", "pkg", 5.0, khung, dung_khi=lambda ns: True))
    assert nodes == [] and len(khung) < 20


def test_khung_nhanh_bo_khung_khi_dumpsys_qua_gio(monkeypatch):
    async def gio_may(client, serial):
        return 1.0

    async def read(client, serial, package, timeout=None):
        assert timeout == quan_sat.NHANH_TOI_DA
        raise AdbError("adb shell dumpsys activity top qua thoi gian cho")

    monkeypatch.setattr(quan_sat, "gio_may", gio_may)
    monkeypatch.setattr(quan_sat.view_hierarchy_fast, "read", read)
    assert asyncio.run(quan_sat.khung_nhanh(None, "s", "pkg", 1080)) == (None, None)


def test_cho_nut_x_dumpsys_treo_thi_uiautomator_tim_x(monkeypatch):
    """Sorapix OB3X-002/004 (23/10/2026): dumpsys qua gio moi lan, uiautomator van thay X."""
    from rcr.ui_dump import parse_dump

    xml = ('<hierarchy><node package="pkg" resource-id="pkg:id/btnSkip" text="" '
           'content-desc="" visible-to-user="true" bounds="[900,100][1000,200]"/></hierarchy>')

    async def nhanh_treo(client, serial, package, rong):
        await asyncio.sleep(5)
        return None, None

    async def mot_khung(client, serial, package):
        await asyncio.sleep(0.05)
        return {"t": 1.0, "x": True, "dem": "", "trang": 0, "nguon": "uia"}, parse_dump(xml)

    async def screen_size(client, serial):
        return (1080, 2400)

    monkeypatch.setattr(quan_sat.device_app, "screen_size", screen_size)
    monkeypatch.setattr(quan_sat, "khung_nhanh", nhanh_treo)
    monkeypatch.setattr(quan_sat, "mot_khung", mot_khung)
    bat_dau = asyncio.run(_do_gio(quan_sat.cho_nut_x(None, "s", "pkg", 10.0, [])))
    tam, giay = bat_dau
    assert tam == (950, 150) and giay < 1.0      # khong cho dumpsys treo xong


async def _do_gio(coro):
    import time
    t = time.monotonic()
    kq = await coro
    return kq, time.monotonic() - t
