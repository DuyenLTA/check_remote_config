"""fa_log.bat tat tag log rac de ROM bop log (vivo ratelimit) khong lam mat log quang cao cua app."""

import asyncio

from rcr import fa_log


class _Client:
    def __init__(self):
        self.lenh = []

    async def shell(self, serial, *args, **kw):
        self.lenh.append(args)
        return "", "", 0


def test_bat_tat_tag_rac_nhung_giu_tag_tool_doc():
    c = _Client()
    asyncio.run(fa_log.bat(c, "3454184009000HI"))
    tat = {a[1] for a in c.lenh if a[0] == "setprop" and a[2] == "S"}
    assert "log.tag.chromium" in tat and "log.tag.okhttp.Http2" in tat
    for giu in ("FA", fa_log.TAG, "AdEventLogger", "BannerAdHelper", "System.err", "libc", "FirebaseRemoteConfig"):
        assert f"log.tag.{giu}" not in tat
