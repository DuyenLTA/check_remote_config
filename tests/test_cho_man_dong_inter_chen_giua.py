"""Buoc `cho_man` gap inter chen giua (bam template -> inter style -> man dich) thi dong ad roi doi tiep - 18/11/2026."""

import asyncio

from rcr import rating_cong_thuc as rc

P = "photomaker.image.editor.ai"


def test_cho_man_gap_ad_thi_dong_roi_toi_man_dich(monkeypatch):
    man = iter([f"{P}/com.google.android.libraries.ads.mobile.sdk.common.AdActivity",
                f"{P}/.ui.feature.select_photo.SelectPhotoActivity"])
    dong = []

    async def act(c, s):
        return P, next(man)

    async def dong_ad(c, s, cho=0):
        dong.append(cho)
        return "đóng ad"

    async def ngu(*a):
        return None
    monkeypatch.setattr(rc.device_app, "focus", act)
    monkeypatch.setattr(rc.fo_flow, "dong_ad_dang_che", dong_ad)
    monkeypatch.setattr(rc.asyncio, "sleep", ngu)
    log = []
    ok = asyncio.run(rc._mot_buoc(None, "s", P, {"cho_man": "SelectPhoto", "toi_da": 60}, log))
    assert ok is True and dong == [45] and log == ["đóng ad", "tới SelectPhotoActivity"]
