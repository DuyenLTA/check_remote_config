"""`cai`: dev day lai cung version -> may dang cai lan day cu van phai cai lan moi nhat."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from rcr import app_tester_ui as ui


class _Client:
    def __init__(self):
        self.lenh = []

    async def shell(self, serial, *a):
        self.lenh.append(a)


def _ban(nut, ngay, note):
    return {"version": "2.2.0 (13)", "loai": "debug", "ngay": ngay, "note": note,
            "mo_rong": True, "nut": nut, "node_nut": object(), "node_mo": object()}


@pytest.fixture
def gia(monkeypatch):
    st = {"bam": [], "cac": []}

    async def mo_chi_tiet(*a):
        return []

    async def doc_cac_ban(*a):
        return st["cac"]

    async def toi_ban(client, serial, dich):
        return dich

    async def ban_dang_cai(*a):
        return {"version": "2.2.0 (13)", "debuggable": True}

    async def bam(client, serial, node, nghi=0):
        st["bam"].append(node)

    async def cho_cai_xong(*a):
        return {"da_cai": True}

    for ten, f in [("mo_chi_tiet", mo_chi_tiet), ("doc_cac_ban", doc_cac_ban), ("_toi_ban", toi_ban),
                   ("ban_dang_cai", ban_dang_cai), ("_bam", bam), ("_cho_cai_xong", cho_cai_xong)]:
        monkeypatch.setattr(ui, ten, f)
    return st


def test_may_dang_cai_lan_day_cu_thi_cai_lan_moi_nhat(gia):
    moi = _ban("tai", "Oct 9, 2026 at 4:40 PM", "debug r2")
    gia["cac"] = [moi, _ban("dang_cai", "Oct 9, 2026 at 9:05 AM", "debug r1")]
    kq = asyncio.run(ui.cai(_Client(), "S1", "pkg.a", "2.2.0 (13)", "debug", Path(".")))
    assert kq == {"da_cai": True} and gia["bam"] == [moi["node_nut"]]


def test_lan_moi_nhat_dang_cai_roi_thi_bo_qua(gia):
    gia["cac"] = [_ban("dang_cai", "Oct 9, 2026 at 4:40 PM", "debug r2"), _ban("tai", "Oct 9, 2026 at 9:05 AM", "r1")]
    kq = asyncio.run(ui.cai(_Client(), "S1", "pkg.a", "2.2.0 (13)", "debug", Path(".")))
    assert kq["da_cai"] is False and gia["bam"] == []


def _goi_cuon(monkeypatch, man_hinh):
    """Gia lap man hinh: `man_hinh` la danh sach release dang hien (khong doi khi cuon)."""
    cuon = []

    async def nodes(client, serial):
        return []

    async def cuon_(client, serial, huong, lan=1):
        cuon.append((huong, lan))

    async def bam(client, serial, node, nghi=0):
        pass
    monkeypatch.setattr(ui, "_nodes", nodes)
    monkeypatch.setattr(ui, "_cuon", cuon_)
    monkeypatch.setattr(ui, "_bam", bam)
    monkeypatch.setattr(ui.s, "cac_ban", lambda n: man_hinh)
    return cuon


def test_ban_dang_hien_truoc_mat_thi_khong_cuon(monkeypatch):
    dich = _ban("tai", "Oct 9, 2026 at 4:40 PM", "r2")
    cuon = _goi_cuon(monkeypatch, [dich])
    assert asyncio.run(ui._toi_ban(_Client(), "S1", dich)) is dich and cuon == []
    # release duy nhat cua danh sach: doc mot man, cuon mot lan thay khong co gi moi thi dung
    assert asyncio.run(ui.doc_cac_ban(_Client(), "S1", [], "2.2.0 (13)")) == [dich] and len(cuon) == 1


def test_app_dang_hien_tren_danh_sach_thi_bam_luon(monkeypatch):
    cuon = _goi_cuon(monkeypatch, [])
    da_bam = []

    async def bam(client, serial, node, nghi=0):
        da_bam.append(node)

    async def khong(*a, **k):
        return None
    monkeypatch.setattr(ui, "_bam", bam)
    monkeypatch.setattr(ui.device_app, "launch", khong)
    monkeypatch.setattr(ui.asyncio, "sleep", khong)
    monkeypatch.setattr(ui.s, "man", lambda n: "chi_tiet" if da_bam else "danh_sach")
    dong = object()
    monkeypatch.setattr(ui.s, "dong_app", lambda n, p: dong)
    monkeypatch.setattr(ui.s, "_co", lambda n, *a, **k: object())
    asyncio.run(ui.mo_chi_tiet(_Client(), "S1", "pkg.a", Path(".")))
    assert da_bam == [dong] and cuon == []
