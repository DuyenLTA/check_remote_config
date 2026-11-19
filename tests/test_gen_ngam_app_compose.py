"""rcr-gen-ngam voi app Compose (moi man chung mot activity, AIP893 18/11/2026): ten man ao theo chu, moc vao man
cho / popup / ve Home tu log WindowManager, o History kieu nhan Image/Video."""

from __future__ import annotations

import pytest

from rcr import gen_ngam_may as may
from rcr.ui_dump import Bounds, DeviceNode

P = "com.aiphotogenerator.aivideomaker.photoslideshow"
CT = may.cong_thuc(P)
MAIN = "AIP893AIPhotoVideoMakerMainActivity"


def _n(text="", desc="", b=(0, 0, 10, 10), i=0):
    return DeviceNode(str(i), "", "android.view.View", text, desc, Bounds(*b), False, True, True, P, None, 0)


@pytest.fixture(autouse=True)
def _theo_chu():
    may.MAN_THEO_CHU.clear()
    may.MAN_THEO_CHU.update(CT["man_theo_chu"])
    may.THANH_TAB[:] = ["|".join(CT[k] for k in ("tab_home", "tab_anh", "tab_video"))]
    yield
    may.MAN_THEO_CHU.clear()
    may.THANH_TAB.clear()


def test_ten_man_ao_theo_chu_khong_theo_desc():
    home = may.Man(0, P, MAIN, [_n(desc="History", b=(934, 115, 1035, 216)), _n("AI Studio", b=(158, 135, 889, 196)),
                                _n("AI Photos", b=(471, 2328, 607, 2368))])
    assert may.ten_man_ao(home, P) == MAIN                       # nut History o Home chi co desc -> van la Home
    ls = may.Man(0, P, MAIN, [_n("History", b=(158, 124, 1001, 185))])
    assert may.ten_man_ao(ls, P) == "HistoryScreen"
    cho = may.Man(0, P, MAIN, [_n("27%", b=(400, 900, 600, 960))])
    assert may.ten_man_ao(cho, P) == "ProcessingScreen"
    popup = may.Man(0, P, MAIN, [_n("Taking you to Home in 3s", b=(132, 1140, 948, 1284)), _n("OK", b=(500, 1380, 580, 1450))])
    assert may.ten_man_ao(popup, P) == "ProcessingScreen"
    kq = may.Man(0, P, MAIN, [_n("Result", b=(158, 128, 933, 182)), _n("Download", b=(739, 1217, 886, 1257))])
    assert may.ten_man_ao(kq, P) == "ResultScreen"
    t2i = may.Man(0, P, MAIN, [_n("Text to Image", b=(158, 124, 1001, 185)), _n("Generate", b=(445, 2246, 636, 2300))])
    assert may.ten_man_ao(t2i, P) == "ManKhac"               # khong co thanh tab duoi -> khong phai Home
    picker = may.Man(0, "com.google.android.photopicker", "MainActivity", [])
    assert may.ten_man_ao(picker, P) == "PhotoPicker"


def test_app_nhieu_activity_giu_ten_that():
    may.MAN_THEO_CHU.clear()
    m = may.Man(0, P, "ProcessingActivity", [_n("Result", b=(1, 1, 50, 50))])
    assert may.ten_man_ao(m, P) == "ProcessingActivity"


def test_moc_cua_so_vao_popup_ve_home():
    a = f"{P}/{P}.presentation.activity.main.{MAIN}"
    dong = [
        "1794975099.469  1047  1712 V WindowManager: Changing focus from Window{c2fc6fe u0 com.google.android."
        f"photopicker/com.android.photopicker.MainActivity}} to Window{{43eebab u0 {a}}} mFocusedApp=x",
        f"1794975117.035  1047  1554 V WindowManager: Changing focus from Window{{43eebab u0 {a}}} to "
        f"Window{{38933a0 u0 {a}}} mFocusedApp=x",
        f"1794975120.050  1047  1364 V WindowManager: Remove Window{{38933a0 u0 {a}}}: mSurfaceController=x",
        f"1794975120.056  1047  1364 V WindowManager: Changing focus from Window{{38933a0 u0 {a} EXITING}} to "
        f"Window{{43eebab u0 {a}}} mFocusedApp=x",
    ]
    w = may.moc_cua_so(dong, P, 1794975098.0)
    assert w == {"vao": 1794975099.469, "popup": 1794975117.035, "ra": 1794975120.05}
    # Anh xong truoc moc popup -> app tu sang Ket qua (Compose, khong doi cua so): khong co popup / ra
    assert may.moc_cua_so(dong[:1], P, 1794975098.0) == {"vao": 1794975099.469, "popup": 0.0, "ra": 0.0}


def test_o_lich_su_theo_nhan_image_video():
    m = may.Man(0, P, "HistoryScreen", [
        _n("History", b=(158, 124, 1001, 185), i=1),
        _n("Generating…", b=(150, 500, 400, 540), i=2),
        _n("Image", b=(85, 852, 180, 892), i=3),
        _n("Untitled creation", b=(45, 944, 335, 991), i=4),
        _n("0 minutes ago", b=(45, 991, 225, 1031), i=5),
        _n("Video", b=(633, 852, 720, 892), i=6),
        _n("Untitled creation", b=(560, 944, 850, 991), i=7),
        _n("3 minutes ago", b=(560, 991, 740, 1031), i=8),
    ])
    o = may.o_lich_su(m, CT)
    assert [(x["ten"], x["dang_tao"], x["video"]) for x in o] == [
        ("Untitled creation", True, False), ("Untitled creation", False, True)]
    assert o[0]["xy"] == (235, 602) and o[1]["ten"] == "Untitled creation"


def test_moc_cua_so_t2i_khong_qua_trinh_chon_anh():
    """T2I: vao man cho = luc bam Generate; dialog popup = focus tu cua so app sang cua so app khac."""
    a = f"{P}/{P}.presentation.activity.main.{MAIN}"
    dong = [
        f"1794979666.954  1047  1712 V WindowManager: Changing focus from Window{{da00737 u0 {a}}} to "
        f"Window{{7102017 u0 {a}}} mFocusedApp=x",
        f"1794979669.112  1047  2225 V WindowManager: Remove Window{{7102017 u0 {a}}}: mSurfaceController=x",
        f"1794979669.116  1047  2225 V WindowManager: Changing focus from Window{{7102017 u0 {a} EXITING}} to "
        f"Window{{da00737 u0 {a}}} mFocusedApp=x",
    ]
    w = may.moc_cua_so(dong, P, 1794979661.3, vao_san=1794979661.8)
    assert w == {"vao": 1794979661.8, "popup": 1794979666.954, "ra": 1794979669.112}


def test_t2i_chi_khi_app_khai_va_khong_ep_style():
    from rcr import gen_ngam_t2i as t2i
    assert t2i.dung_t2i(CT, "anh", "t2i") and not t2i.dung_t2i(CT, "anh", None)
    assert not t2i.dung_t2i(CT, "video", "t2i") and not t2i.dung_t2i({"t2i": {}}, "anh", "t2i")


def test_vao_man_cho_chi_tinh_khi_thay_man_cho(monkeypatch):
    """Trinh chon anh dong nhung app chan (het luot) -> khong tinh la vao man cho (dem luot khong cong sai)."""
    import asyncio
    from rcr import gen_ngam_tao as tao

    async def cua_so(*a):
        return "43eebab", P

    async def gio(*a):
        return 100.0

    def cho_man(ten):
        async def cho(client, serial, package, dk, giay):
            m = may.Man(101.0, P, ten, [_n("Daily Limit Reached", b=(0, 0, 500, 60))] if ten == MAIN else [])
            return m if dk(m) else None
        return cho

    monkeypatch.setattr(may, "cua_so", cua_so)
    monkeypatch.setattr(may, "gio", gio)
    monkeypatch.setattr(may, "cho", cho_man(MAIN))
    assert asyncio.run(tao._vao_man_cho_nhanh(None, "S", P, CT)) == (0.0, "")
    monkeypatch.setattr(may, "cho", cho_man("ProcessingScreen"))
    assert asyncio.run(tao._vao_man_cho_nhanh(None, "S", P, CT)) == (100.0, "43eebab")
