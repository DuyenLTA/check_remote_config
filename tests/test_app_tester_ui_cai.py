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


def test_ve_dau_danh_sach_vuot_toi_khi_dung_yen(monkeypatch):
    """AIP882 29/10/2026: ~93 app, dang o cuoi danh sach -> vuot co dinh 8 lan chua toi dau."""
    trang = [["z1", "z2"], ["m1", "m2"], ["c1", "c2"], ["a1", "a2"], ["a1", "a2"]]
    da_vuot = []

    class N:
        def __init__(self, t):
            self.text, self.resource_id = t, "bundle_id"

    async def nodes(client, serial):
        return [N(t) for t in trang[len(da_vuot)]]

    async def cuon_(client, serial, huong, lan=1):
        da_vuot.append(huong)
    monkeypatch.setattr(ui, "_nodes", nodes)
    monkeypatch.setattr(ui, "_cuon", cuon_)
    asyncio.run(ui._ve_dau_ds(_Client(), "S1", [N(t) for t in trang[0]]))
    assert da_vuot == ["down"] * 4     # trang a1 lap lai -> dung, khong vuot du MAX_CUON_DS


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


def test_thong_bao_che_nut_all_apps_thi_bam_back(monkeypatch):
    """29/10/2026: heads-up cua Linguza che nut All apps -> cu bam khong ve danh sach; phim Back ve duoc."""
    _goi_cuon(monkeypatch, [])
    da_bam, lenh = [], []

    class Client(_Client):
        async def shell(self, serial, *a):
            lenh.append(a)

    async def bam(client, serial, node, nghi=0):
        da_bam.append(node)

    async def khong(*a, **k):
        return None

    def man(n):
        if any(a[-1] == "KEYCODE_BACK" for a in lenh):
            return "chi_tiet" if len(da_bam) > 1 else "danh_sach"
        return "chi_tiet"                                    # bam All apps bi thong bao che: van o chi tiet
    monkeypatch.setattr(ui, "_bam", bam)
    monkeypatch.setattr(ui.device_app, "launch", khong)
    monkeypatch.setattr(ui.asyncio, "sleep", khong)
    monkeypatch.setattr(ui.s, "man", man)
    monkeypatch.setattr(ui.s, "nut_chu", lambda n, text, package: None)
    monkeypatch.setattr(ui.s, "dong_app", lambda n, p: object())
    monkeypatch.setattr(ui.s, "_co", lambda n, *a, **k: object())
    asyncio.run(ui.mo_chi_tiet(Client(), "S1", "pkg.a", Path(".")))
    assert ("input", "keyevent", "KEYCODE_BACK") in lenh and len(da_bam) == 2   # All apps + dong app


def _cai_cung_version(monkeypatch, cai_luc, nut_sau_go="tai", nut_dau="dang_cai"):
    """May dang cai 2.2.0 (13) debug luc `cai_luc`; App Tester co ban 2.2.0 (13) day 'Oct 29, 2026 at 2:35 PM'
    dang hien nut Open (App Tester so versionCode)."""
    from datetime import datetime
    st = {"bam": [], "lenh": [], "go": False}
    dich = _ban(nut_dau, "Oct 29, 2026 at 2:35 PM", "debug build lai")

    async def mo_chi_tiet(*a):
        st["lenh"].append(("mo_app_tester",))
        return []

    async def doc_cac_ban(*a):
        return [dich]

    async def toi_ban(client, serial, d):
        return _ban(nut_sau_go, d["ngay"], d["note"]) if st["go"] else d

    async def ban_dang_cai(*a):
        return {"version": "2.2.0 (13)", "debuggable": True, "cai_luc": datetime.fromisoformat(cai_luc)}

    async def bam(client, serial, node, nghi=0):
        st["bam"].append(node)

    async def cho_cai_xong(client, serial, package, version, loai, go, out_dir):
        return {"da_cai": True, "go_ban_cu": go}

    class C(_Client):
        async def shell(self, serial, *a):
            st["lenh"].append(a)
            if a[:2] == ("pm", "uninstall"):
                st["go"] = True
    for ten, f in [("mo_chi_tiet", mo_chi_tiet), ("doc_cac_ban", doc_cac_ban), ("_toi_ban", toi_ban),
                   ("ban_dang_cai", ban_dang_cai), ("_bam", bam), ("_cho_cai_xong", cho_cai_xong)]:
        monkeypatch.setattr(ui, ten, f)
    kq = asyncio.run(ui.cai(C(), "S1", "pkg.a", "2.2.0 (13)", "debug", Path(".")))
    return kq, st


def test_dev_day_lai_cung_version_sau_luc_cai_thi_go_va_cai_ban_moi(monkeypatch):
    """AIP922 29/10/2026: ban 3.7.0 (30) day lai 14:35 van hien Open, may con ban 28/10 -> phai cai lai."""
    kq, st = _cai_cung_version(monkeypatch, "2026-10-28 18:38:11")
    assert ("pm", "uninstall", "pkg.a") in st["lenh"] and kq == {"da_cai": True, "go_ban_cu": True}
    assert len(st["bam"]) == 1                                           # bam Download ban moi


def test_mo_app_tester_thi_bat_man_truoc(monkeypatch):
    """02/11/2026: may tat man (Pixel 4, AIP936) -> dump "null root node", cai hong. Bat man + bo khoa truoc khi mo."""
    lenh = []

    class Client(_Client):
        async def shell(self, serial, *a, **k):
            lenh.append(a)

    class DaMo(Exception):
        pass

    async def launch(client, serial, pkg):
        lenh.append(("launch", pkg))
        raise DaMo                                          # chi kiem thu tu truoc khi mo App Tester

    async def khong(*a, **k):
        return None
    monkeypatch.setattr(ui.device_app, "launch", launch)
    monkeypatch.setattr(ui.asyncio, "sleep", khong)
    with pytest.raises(DaMo):
        asyncio.run(ui.mo_chi_tiet(Client(), "S1", "pkg.a", Path(".")))
    assert lenh == [("input", "keyevent", "KEYCODE_WAKEUP"), ("wm", "dismiss-keyguard"), ("launch", ui.s.APP_TESTER)]


def test_dump_null_root_thi_bat_man_doi_roi_chup_lai(monkeypatch):
    """02/11/2026 Pixel 4: dump "null root node" vai chuc giay du man sang -> bat man, doi, chup lai."""
    lan, lenh = [0], []

    async def dump(client, serial):
        lan[0] += 1
        if lan[0] < 3:
            raise ui.AdbError("uiautomator dump that bai: ERROR: null root node returned by UiTestAutomationBridge.")
        return "<hierarchy/>"

    class Client(_Client):
        async def shell(self, serial, *a, **k):
            lenh.append(a)

    async def khong(*a, **k):
        return None
    monkeypatch.setattr(ui.ui_dump, "dump", dump)
    monkeypatch.setattr(ui.ui_dump, "parse_dump", lambda x: ["ok"])
    monkeypatch.setattr(ui.asyncio, "sleep", khong)
    assert asyncio.run(ui._nodes(Client(), "S1")) == ["ok"] and lan[0] == 3
    assert lenh.count(("input", "keyevent", "KEYCODE_WAKEUP")) == 2


def test_may_co_san_cung_version_thi_van_go_roi_tai_lai(monkeypatch):
    """02/11/2026 AIP886 2.7.0 (20): may co san ban nay, App Tester hien Open -> bot bao "chua co". Luat: luon go
    app truoc khi vao App Tester roi tai lai (user chot 30/10, nhac lai 02/11/2026)."""
    kq, st = _cai_cung_version(monkeypatch, "2026-10-29 14:40:00", nut_dau="tai")
    assert st["lenh"][:2] == [("pm", "uninstall", "pkg.a"), ("mo_app_tester",)]      # go TRUOC khi mo
    assert kq == {"da_cai": True, "go_ban_cu": True} and len(st["bam"]) == 1


def test_khong_tim_thay_version_thi_luu_man_de_xem(monkeypatch, tmp_path):
    async def rong(*a):
        return []

    async def ban_dang_cai(*a):
        return {}

    async def luu(client, serial, out_dir, ly_do):
        return ui.LoiCai(f"{ly_do} (màn lưu)")
    for ten, f in [("mo_chi_tiet", rong), ("doc_cac_ban", rong), ("ban_dang_cai", ban_dang_cai), ("_luu_man_la", luu)]:
        monkeypatch.setattr(ui, ten, f)
    with pytest.raises(ui.LoiCai, match=r"chưa có 2.7.0 \(20\) \(màn lưu\)"):
        asyncio.run(ui.cai(_Client(), "S1", "pkg.a", "2.7.0 (20)", "release", tmp_path))


def test_danh_sach_dai_thi_cuon_ve_toi_dau_moi_thay_ban_moi_nhat(monkeypatch):
    """AIP886: release can cai o dau, doc_cac_ban da cuon xa xuong duoi; 4 lan vuot nguoc khong du."""
    dich = _ban("tai", "Nov 2, 2026 at 4:40 PM", "release moi")
    trang = [[_ban("tai", f"Jul {i}, 2026 at 9:00 AM", f"r{i}")] for i in range(1, 11)] + [[dich]]
    vi_tri = {"i": 0}                       # 0 = trang cuoi danh sach, 10 = dau danh sach
    cuon = []

    async def nodes(client, serial):
        return []

    async def cuon_(client, serial, huong, lan=1):
        cuon.append((huong, lan))
        vi_tri["i"] = min(10, vi_tri["i"] + lan) if huong == "down" else max(0, vi_tri["i"] - lan)

    async def bam(client, serial, node, nghi=0):
        pass
    monkeypatch.setattr(ui, "_nodes", nodes)
    monkeypatch.setattr(ui, "_cuon", cuon_)
    monkeypatch.setattr(ui, "_bam", bam)
    monkeypatch.setattr(ui.s, "cac_ban", lambda n: trang[vi_tri["i"]])
    assert asyncio.run(ui._toi_ban(_Client(), "S1", dich)) is dich


def test_mo_rong_release_o_day_man_thi_day_len_cho_note_hien(monkeypatch):
    """AIP886: bam mo 2.7.0 (20) o day man -> note troi xuong duoi, dump mat release; day nua trang moi thay."""
    dich = _ban("tai", "Oct 27, 2026 at 10:26 AM", "2.7.0 (20) Tutorial SDK 3.6.1")
    gap = {**dich, "mo_rong": False, "node_nut": None, "nut": ""}
    st = {"man": [gap], "day": 0}

    async def nodes(client, serial):
        return []

    async def bam(client, serial, node, nghi=0):
        st["man"] = []                      # mo rong xong: note duoi mep man

    async def nua_trang(client, serial):
        st["day"] += 1
        st["man"] = [dich]

    async def cuon_(client, serial, huong, lan=1):
        pass
    monkeypatch.setattr(ui, "_nodes", nodes)
    monkeypatch.setattr(ui, "_bam", bam)
    monkeypatch.setattr(ui, "_cuon_nua_trang", nua_trang)
    monkeypatch.setattr(ui, "_cuon", cuon_)
    monkeypatch.setattr(ui.s, "cac_ban", lambda n: st["man"])
    assert asyncio.run(ui._toi_ban(_Client(), "S1", dich)) is dich and st["day"] == 1
