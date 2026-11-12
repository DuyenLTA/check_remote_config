"""walk_to cho theo trang thai (activity focus) thay vi ngu cung, va khong dump UI truoc buoc CHO."""

from __future__ import annotations

import asyncio

from rcr import device_app, fo_flow

PKG = "com.ai.app"
OB = f"{PKG}.VslTemplate4OnboardingActivity"
NUT = ("<?xml version='1.0' encoding='UTF-8'?><hierarchy rotation=\"0\">"
       f'<node index="0" class="android.widget.TextView" package="{PKG}" resource-id="{PKG}:id/tv" '
       'text="Title" content-desc="" bounds="[0,0][100,100]" clickable="false" enabled="true" /></hierarchy>')


def _gia(monkeypatch, man: list[str]):
    """focus tra lan luot `man` (het thi giu man cuoi); ghi lai dump + giay ngu."""
    ghi = {"dump": 0, "ngu": [], "focus": 0}

    async def focus(client, serial):
        ghi["focus"] += 1
        return PKG, man[min(ghi["focus"] - 1, len(man) - 1)]

    async def dump(client, serial):
        ghi["dump"] += 1
        return NUT

    async def ngu(giay, *a):
        ghi["ngu"].append(round(giay, 2))

    async def khong(*a, **k):
        return None

    monkeypatch.setattr(device_app, "focus", focus)
    async def co_man(*a):
        return 1080, 2400

    monkeypatch.setattr(device_app, "swipe", khong)
    monkeypatch.setattr(device_app, "screen_size", co_man)
    monkeypatch.setattr(fo_flow.ui_dump, "dump", dump)
    monkeypatch.setattr(fo_flow.asyncio, "sleep", ngu)
    monkeypatch.setattr(fo_flow, "guard", lambda *a: None)
    return ghi


def test_cho_man_doi_ve_som_khi_activity_doi(monkeypatch):
    ghi = _gia(monkeypatch, ["A", "B"])
    asyncio.run(fo_flow.cho_man_doi(None, "S", "A", 1.0))
    # nhip 0,25 (doc A) -> nhip 0,25 (doc B: doi) -> cho them SAU_KHI_DOI roi ve, khong ngu du 1s
    assert ghi["ngu"] == [0.25, 0.25, 0.5] and ghi["focus"] == 2


def test_cho_man_doi_khong_doi_thi_cho_du_nhu_cu(monkeypatch):
    ghi = _gia(monkeypatch, ["A"])
    asyncio.run(fo_flow.cho_man_doi(None, "S", "A", 1.0))
    assert sum(ghi["ngu"]) == 1.0 and ghi["focus"] == 3


def test_buoc_cho_khong_dump_ui(monkeypatch):
    """Luat OnboardingActivity: wait 2 -> swipe. Buoc wait lam ngay khong dump; dump chi o buoc vuot."""
    ghi = _gia(monkeypatch, [OB] * 400)
    out = asyncio.run(fo_flow.walk_to(None, "S", PKG, "MainActivity", timeout=3))
    lam = [t["did"] for t in out["trail"]]
    assert lam[:2] == ["cho 2s", "vuot sang left"]
    assert 2 in ghi["ngu"]                            # thoi gian cho cua luat giu nguyen
    assert ghi["dump"] == sum(1 for d in lam if not d.startswith("cho "))
