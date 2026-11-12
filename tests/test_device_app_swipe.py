"""Vuot ngang tranh popup "AdMob native ad validator" giua man (vivo V2143, 12/11/2026)."""
from __future__ import annotations

import asyncio

from rcr import device_app


class _Client:
    def __init__(self):
        self.cmds = []

    async def shell(self, serial, *args):
        self.cmds.append(args)
        return "", "", 0


def test_vuot_ngang_o_tren_vung_popup_validator(monkeypatch):
    monkeypatch.setattr(device_app, "guard", lambda serial: None)
    c = _Client()
    asyncio.run(device_app.swipe(c, "S", "left", (1080, 2408)))
    _, _, x1, y1, x2, y2, _ = c.cmds[0]
    # Popup che y 1115-1432 tren man 2408: diem vuot phai nam tren vung do, va vuot tu phai sang trai.
    assert int(y1) == int(y2) < 1115 and int(x1) > int(x2)
