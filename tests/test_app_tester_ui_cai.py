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
