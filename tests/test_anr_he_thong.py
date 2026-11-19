"""Hop thoai ANR cua launcher che man app: tool bam Wait; ANR cua chinh app thi giu nguyen."""

from __future__ import annotations

import asyncio

from rcr import anr_he_thong as a
from rcr import ui_dump

# Dang hop thoai tren anh OPPO f3466cdb 18/11/2026 (lượt AIP936): "System Launcher isn't responding", Close app / Wait.
XML_ANR = (
    '<?xml version="1.0"?><hierarchy rotation="0">'
    '<node index="0" text="" resource-id="" package="android" bounds="[60,880][1020,1480]">'
    '<node index="0" text="System Launcher isn\'t responding" resource-id="android:id/alertTitle" package="android" '
    'bounds="[100,920][980,1060]" />'
    '<node index="1" text="Close app" resource-id="android:id/aerr_close" package="android" clickable="true" '
    'bounds="[60,1180][1020,1300]" />'
    '<node index="2" text="Wait" resource-id="android:id/aerr_wait" package="android" clickable="true" '
    'bounds="[60,1320][1020,1440]" />'
    '</node></hierarchy>'
)
XML_APP = ('<?xml version="1.0"?><hierarchy rotation="0"><node index="0" text="Select Language" resource-id="" '
           'package="com.aihomedesign.app" bounds="[0,0][1080,2400]" /></hierarchy>')
WIN_LAUNCHER = "  Window #9 Window{8149b86 u0 Application Not Responding: com.oppo.launcher}:\n    mOwnerUid=1000"
WIN_APP = "  Window #9 Window{8149b86 u0 Application Not Responding: com.aihomedesign.app}:\n    mOwnerUid=1000"


class _May:
    """Client gia: dump tra lan luot cac XML trong `dumps`, ghi lai lenh tap."""

    def __init__(self, dumps, windows):
        self.dumps, self.windows, self.taps = list(dumps), windows, []
        self.cur = ""

    async def shell(self, serial, *args, timeout=None):
        if args[:2] == ("uiautomator", "dump"):
            self.cur = self.dumps.pop(0) if len(self.dumps) > 1 else self.dumps[0]
            return "UI hierchary dumped to: x", "", 0
        if args[0] == "cat":
            return self.cur, "", 0
        if args[:2] == ("dumpsys", "window"):
            return self.windows, "", 0
        if args[:2] == ("input", "tap"):
            self.taps.append((int(args[2]), int(args[3])))
        return "", "", 0


def test_nhan_hop_thoai_va_nut_wait():
    assert a.co_hop_thoai_anr(XML_ANR) and not a.co_hop_thoai_anr(XML_APP)
    assert a.diem_nut_doi(XML_ANR) == (540, 1380)
    assert a.tien_trinh_anr(WIN_LAUNCHER) == "com.oppo.launcher"


def test_chi_tien_trinh_he_thong_moi_dong():
    for tt in ("com.oppo.launcher", "com.android.systemui", "com.sec.android.app.launcher", "system"):
        assert a.la_he_thong(tt), tt
    for tt in ("com.aihomedesign.app", "aitutor.grammar.languagetutor", ""):
        assert not a.la_he_thong(tt), tt


def test_dump_bam_wait_khi_launcher_anr_roi_tra_man_app(monkeypatch):
    monkeypatch.setattr(ui_dump, "guard", lambda s: None)
    may = _May([XML_ANR, XML_APP], WIN_LAUNCHER)
    xml = asyncio.run(ui_dump.dump(may, "S1"))
    assert may.taps == [(540, 1380)] and "Select Language" in xml


def test_dump_giu_nguyen_khi_chinh_app_anr(monkeypatch):
    # ANR cua app dang test la ket qua: khong bam gi, anh / dump giu hop thoai
    monkeypatch.setattr(ui_dump, "guard", lambda s: None)
    may = _May([XML_ANR], WIN_APP)
    xml = asyncio.run(ui_dump.dump(may, "S1"))
    assert may.taps == [] and "isn't responding" in xml

