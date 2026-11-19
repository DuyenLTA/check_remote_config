"""Bam Watch Ads 2 lan khong mo AdActivity -> dung, bao khong fill (khong cho het 150-300s) - 17/11/2026."""

import asyncio

from rcr import rating_cong_thuc as rc
from rcr.ui_dump import Bounds, DeviceNode

P = "com.x"


def test_bam_hai_lan_khong_mo_ad_thi_dung(monkeypatch):
    nut = DeviceNode("0", "", "android.widget.Button", "Watch Ads (0/2)", "", Bounds(0, 0, 100, 100),
                     True, True, True, P, None, 0)
    bam = []

    async def act(c, s):
        return P, "x.PhotoSelectActivity"

    async def nodes(c, s, p):
        return [nut]

    async def bam_(c, s, n):
        bam.append(n.text)

    async def ngu(*a):
        return None
    monkeypatch.setattr(rc.device_app, "focus", act)
    monkeypatch.setattr(rc, "_nodes", nodes)
    monkeypatch.setattr(rc, "_bam", bam_)
    monkeypatch.setattr(rc.asyncio, "sleep", ngu)
    log = []
    ok = asyncio.run(rc._mot_buoc(None, "s", P, {"xem_ads": "^Watch Ads", "toi": "Processing", "toi_da": 300}, log))
    assert ok is False and len(bam) == 2 and "không fill" in log[-1]


def test_bam_lai_cho_bam_them_truoc_khi_ket_luan_khong_fill(monkeypatch):
    nut = DeviceNode("0", "", "android.widget.Button", "Watch ad for +1 today (4/5)", "", Bounds(0, 0, 100, 100),
                     True, True, True, P, None, 0)
    bam = []

    async def act(c, s):
        return P, "x.SelectPhotoActivity"

    async def nodes(c, s, p):
        return [nut]

    async def bam_(c, s, n):
        bam.append(n.text)

    async def ngu(*a):
        return None
    monkeypatch.setattr(rc.device_app, "focus", act)
    monkeypatch.setattr(rc, "_nodes", nodes)
    monkeypatch.setattr(rc, "_bam", bam_)
    monkeypatch.setattr(rc.asyncio, "sleep", ngu)
    log = []
    buoc = {"xem_ads": "^Watch ad for", "toi": "Generating", "toi_da": 300, "bam_lai": 6}
    ok = asyncio.run(rc._mot_buoc(None, "s", P, buoc, log))
    assert ok is False and len(bam) == 6 and "không fill" in log[-1]
