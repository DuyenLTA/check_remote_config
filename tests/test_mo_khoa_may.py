"""mo_khoa_may: bat man + mo khoa bang PIN 0000 hoac pattern chu L, khong dung cho nguoi."""

from __future__ import annotations

import asyncio

import pytest

from conftest import SERIAL, FakeAdb
from rcr import mo_khoa_may

MO = "  mWakefulness=Awake\n    isKeyguardShowing=false\n"
KHOA = "  mWakefulness=Asleep\n    isKeyguardShowing=true\n"
KHOA_VIVO = "  mWakefulness=Awake\n    mShowingLockscreen=true mShowingDream=false mDreamingLockscreen=false\n"

XML_PIN = """<?xml version='1.0' ?><hierarchy rotation="0">
<node index="0" text="" resource-id="com.android.systemui:id/pinEntry" class="android.widget.EditText"
 package="com.android.systemui" bounds="[100,900][980,1000]" /></hierarchy>"""
XML_PATTERN = """<?xml version='1.0' ?><hierarchy rotation="0">
<node index="0" text="" resource-id="com.android.systemui:id/lockPatternView"
 class="com.android.internal.widget.LockPatternView" package="com.android.systemui"
 bounds="[90,1200][990,2100]" /></hierarchy>"""


class LockAdb(FakeAdb):
    """May co man khoa: `mo_bang` = lenh input lam may mo khoa ("text 0000" / "motionevent UP" / None)."""

    def __init__(self, trang_thai, xml="", mo_bang=None):
        super().__init__()
        self.trang_thai, self.xml, self.mo_bang = trang_thai, xml, mo_bang

    def _dispatch(self, cmd):
        self.calls.append(cmd)
        if "dumpsys" in cmd:
            return self.trang_thai, "", 0
        if "wm size" in cmd:
            return "Physical size: 1080x2400\n", "", 0
        if " cat " in cmd:
            return self.xml, "", 0
        if self.mo_bang and self.mo_bang in cmd:
            self.trang_thai = MO
        return "", "", 0

    def inputs(self):
        return [c.split(" shell ", 1)[1] for c in self.calls if " shell input " in c]


@pytest.fixture(autouse=True)
def nhanh(monkeypatch):
    monkeypatch.setattr(mo_khoa_may, "NGHI", 0)
    monkeypatch.setattr(mo_khoa_may, "NGHI_SAU_NHAP", 0)


def test_may_da_mo_thi_khong_gui_phim_nao():
    adb = LockAdb(MO)
    assert asyncio.run(mo_khoa_may.mo_khoa(adb, SERIAL)) is True
    assert adb.inputs() == []
    assert len(adb.calls) == 1  # dung mot lenh dumpsys


def test_man_pin_thi_nhap_0000_roi_enter():
    adb = LockAdb(KHOA, XML_PIN, mo_bang="KEYCODE_ENTER")
    assert asyncio.run(mo_khoa_may.mo_khoa(adb, SERIAL)) is True
    ins = adb.inputs()
    assert ins[0] == "input keyevent KEYCODE_WAKEUP"
    assert ins[-2:] == ["input text 0000", "input keyevent KEYCODE_ENTER"]
    assert not any("motionevent" in c for c in ins)


def test_co_khoa_kieu_vivo_mShowingLockscreen_cung_nhan_ra():
    adb = LockAdb(KHOA_VIVO, XML_PIN, mo_bang="KEYCODE_ENTER")
    assert asyncio.run(mo_khoa_may.mo_khoa(adb, SERIAL)) is True
    assert "input text 0000" in adb.inputs()


def test_man_pattern_thi_ve_chu_L_qua_5_diem_theo_thu_tu():
    adb = LockAdb(KHOA, XML_PATTERN, mo_bang="motionevent UP")
    assert asyncio.run(mo_khoa_may.mo_khoa(adb, SERIAL)) is True
    motion = [c.split()[2:] for c in adb.inputs() if "motionevent" in c]
    assert motion[0][0] == "DOWN" and motion[-1][0] == "UP"
    diem = [(int(x), int(y)) for _, x, y in motion]
    # Bounds [90,1200][990,2100]: o rong 300 -> tam cot 240/540/840, tam hang 1350/1650/1950.
    l = [(240, 1350), (240, 1650), (240, 1950), (540, 1950), (840, 1950)]
    vi_tri = [diem.index(p) for p in l]
    assert vi_tri == sorted(vi_tri) and vi_tri[0] == 0 and diem[-1] == l[-1]
    assert "input text 0000" not in adb.inputs()


def test_khong_co_motionevent_thi_ve_bang_swipe_tung_doan():
    adb = LockAdb(KHOA, XML_PATTERN, mo_bang="1950 840 1950 150")
    adb.fails = {}
    goc = adb._dispatch

    def dispatch(cmd):
        if "motionevent" in cmd:
            adb.calls.append(cmd)
            return "", "Error: Unknown command: motionevent", 1
        return goc(cmd)

    adb._dispatch = dispatch
    assert asyncio.run(mo_khoa_may.mo_khoa(adb, SERIAL)) is True
    doan = [c.split()[2:6] for c in adb.inputs() if "swipe" in c and c.endswith(" 150")]
    assert doan == [["240", "1350", "240", "1650"], ["240", "1650", "240", "1950"],
                    ["240", "1950", "540", "1950"], ["540", "1950", "840", "1950"]]


def test_thu_het_lan_van_khoa_thi_tra_false():
    adb = LockAdb(KHOA, XML_PIN, mo_bang=None)
    assert asyncio.run(mo_khoa_may.mo_khoa(adb, SERIAL)) is False
    assert adb.inputs().count("input text 0000") == mo_khoa_may.LAN_THU


def test_anh_den_vi_may_khoa_thi_mo_khoa_roi_chup_lai():
    from rcr import screencap

    adb = LockAdb(KHOA, XML_PIN, mo_bang="KEYCODE_ENTER")
    anh = [b"\x89PNG" + b"0" * 100, b"\x89PNG" + b"1" * 60_000]

    async def run_binary(*a, timeout=None):
        return anh.pop(0), b"", 0

    adb.run_binary = run_binary
    ra = asyncio.run(screencap.capture(adb, SERIAL, giu_png=True))
    assert ra["warning"] == "" and len(ra["png"]) > 60_000
    assert "input text 0000" in adb.inputs()
