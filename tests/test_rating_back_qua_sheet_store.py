"""'Rate on Google Play' mo sheet trang app tren Store: BACK 1 -> trang chu Play, BACK 2 ve app = DUNG (QA 17/11/2026)."""

import asyncio

from rcr import act_rating, rating_may

P = "com.aimakeup.aifaceeditor.facemakeup.faceswap"


def test_back_hai_lan_qua_sheet_store_ve_app(monkeypatch):
    bam = []
    man = {0: (rating_may.GOOGLE_PLAY, "x.TransparentMainActivityPrivate"),
           1: (rating_may.GOOGLE_PLAY, "x.MainActivityPrivate"),
           2: (P, "com.vls.beautygenie.ui.main.MainActivity")}

    async def act(c, s):
        return man[min(len(bam), 2)]

    class C:
        async def shell(self, *a, **k):
            bam.append(a[-1])
            return "", "", 0

    t = iter(range(0, 10 ** 6, 9))      # dong ho gia: moi lan doc nhay 9s -> het cho 8s ngay
    monkeypatch.setattr(act_rating, "_act", act)
    monkeypatch.setattr(act_rating.time, "monotonic", lambda: next(t))
    monkeypatch.setattr(act_rating, "SAU_THAO_TAC", 0)
    r = asyncio.run(act_rating._back(C(), "s", P))
    assert r["so_back"] == 2 and r["trong_app"] and r["man"].endswith("MainActivity")
    assert r["qua"][0].startswith(rating_may.GOOGLE_PLAY)
