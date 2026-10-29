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


def test_trang_chi_tiet_load_cham_thi_doi_them(monkeypatch):
    """AIP805 29/10/2026: dump ngay sau khi bam chua co trang chi tiet, vai giay sau moi hien."""
    _goi_cuon(monkeypatch, [])
    da_bam, lan_doc = [], []

    async def bam(client, serial, node, nghi=0):
        da_bam.append(node)

    async def khong(*a, **k):
        return None

    def man(n):
        if not da_bam:
            return "danh_sach"
        lan_doc.append(1)
        return "chi_tiet" if len(lan_doc) > 4 else "khac"     # 2 nhip dau trang chua load
    monkeypatch.setattr(ui, "_bam", bam)
    monkeypatch.setattr(ui.device_app, "launch", khong)
    monkeypatch.setattr(ui.asyncio, "sleep", khong)
    monkeypatch.setattr(ui.s, "man", man)
    monkeypatch.setattr(ui.s, "nut_chu", lambda n, text, package: None)    # khong co man loi Retry
    monkeypatch.setattr(ui.s, "dong_app", lambda n, p: object())
    monkeypatch.setattr(ui.s, "_co", lambda n, *a, **k: object())
    asyncio.run(ui.mo_chi_tiet(_Client(), "S1", "pkg.a", Path(".")))   # khong raise
    assert len(da_bam) == 1


def test_cai_xong_co_debuggable_sai_loai_thi_bao_ngay(monkeypatch):
    """Note khong ghi loai: cai xong adb bao release ma can debug -> loi ngay, khong cho het TIMEOUT_CAI."""
    async def ban_dang_cai(*a):
        return {"version": "1.4.0 (14)", "debuggable": False}
    monkeypatch.setattr(ui, "ban_dang_cai", ban_dang_cai)
    c = _Client()
    with pytest.raises(ui.LoiCai, match="cờ debuggable bằng adb: là bản release, không phải debug"):
        asyncio.run(ui._cho_cai_xong(c, "S1", "pkg.a", "1.4.0 (14)", "debug", True, Path(".")))
    assert c.lenh == [("input", "keyevent", "KEYCODE_HOME")]


def test_app_tester_loi_tai_trang_thi_bam_retry(monkeypatch):
    """Mang chap chon: App Tester hien "Error fetching the app details" + Retry -> bam Retry, doi tiep."""
    _goi_cuon(monkeypatch, [])
    dong, retry = object(), object()
    da_bam = []

    async def bam(client, serial, node, nghi=0):
        da_bam.append(node)

    async def khong(*a, **k):
        return None
    monkeypatch.setattr(ui, "_bam", bam)
    monkeypatch.setattr(ui.device_app, "launch", khong)
    monkeypatch.setattr(ui.asyncio, "sleep", khong)
    # Sau khi bam app: man loi cho toi khi bam Retry, roi moi ra trang chi tiet.
    monkeypatch.setattr(ui.s, "man", lambda n: "danh_sach" if not da_bam else ("chi_tiet" if retry in da_bam else "khac"))
    monkeypatch.setattr(ui.s, "nut_chu", lambda n, text, package: retry if retry not in da_bam else None)
    monkeypatch.setattr(ui.s, "dong_app", lambda n, p: dong)
    monkeypatch.setattr(ui.s, "_co", lambda n, *a, **k: object())
    asyncio.run(ui.mo_chi_tiet(_Client(), "S1", "pkg.a", Path(".")))
    assert da_bam == [dong, retry]
