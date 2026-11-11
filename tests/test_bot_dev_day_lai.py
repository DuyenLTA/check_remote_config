"""Dev bao lai CUNG ma + version (build lai, khong tang so) o kenh project: bot phai hoi Check lai + xep verify.

11/11/2026: AIP922 3.9.0 (32) day lai them TikTok config + ads-core 2.0.1, bot im vi coi la build da hoi roi.
"""
from __future__ import annotations

import asyncio
from types import SimpleNamespace

from rcr import bot_nhan_build as nb

TIN_DEV = ("Bản build **AIP922** v3.9.0 (32) đã được hoàn thiện. Please check\n"
           "- apply Tutorial SDK 3.7.1, fix ANR cold-start, add TikTok ad config")


class _Kenh:
    def __init__(self):
        self.sent = []

    async def send(self, chu, **k):
        self.sent.append(chu)


def _bot(tin_luu: dict, dang_chay: bool = False):
    goi = {"verify": [], "hoi": []}
    bot = SimpleNamespace(kenh_qa=1, kenh_build={1}, duyet=set(), role=0)
    bot.q = SimpleNamespace(tin=tin_luu, vi_tri=lambda mid: 1 if dang_chay else None,
                            nho_tin=lambda c: tin_luu.update({str(c["msg_id"]): c}))
    bot._duoc_duyet = lambda user: False

    async def xep_verify(c, kenh):
        goi["verify"].append(c)

    async def hoi_lai(m, tin):
        goi["hoi"].append("qa")
    bot._xep_verify, bot._hoi_lai = xep_verify, hoi_lai
    kenh = _Kenh()
    bot.get_channel = lambda cid: kenh
    return bot, goi, kenh


def _tin(link, webhook=None, tac_gia=6):
    return SimpleNamespace(author=SimpleNamespace(bot=True, id=tac_gia), webhook_id=webhook, guild=SimpleNamespace(id=9),
                           channel=SimpleNamespace(id=8, name="aip922-nexsus-ai-video-official-group"),
                           content=TIN_DEV, message_snapshots=[], jump_url=link)


def _cu(link="https://discord.com/x/cu"):
    return {"10": {"msg_id": 10, "ma": "AIP922", "version": "3.9.0 (32)", "package": "p.aip922",
                   "loai_ban": "release", "sdk": "3.7.1", "link_tin": link}}


def _gia_lap(monkeypatch, bot_dev=6):
    monkeypatch.setattr(nb.bot_kenh_project, "la_bot_dev", lambda i: i == bot_dev)
    hoi = []

    async def hoi_lai_build(bot, tin, link_tin, gui, doi=None):
        if any(bot.q.vi_tri(t["msg_id"]) is not None for t in nb.tin_da_hoi(bot, tin)):
            return f"Build **{tin['ma']}** đang chờ / đang chạy"
        bot.q.nho_tin({**_cu()["10"], "msg_id": 20, "link_tin": link_tin})
        hoi.append(link_tin)
        return "Đã gửi tin hỏi Check mới: u"
    monkeypatch.setattr(nb, "hoi_lai_build", hoi_lai_build)
    return hoi


def test_dev_day_lai_cung_version_thi_hoi_check_lai_va_xep_verify(monkeypatch):
    hoi = _gia_lap(monkeypatch)
    bot, goi, _ = _bot(_cu())
    asyncio.run(nb.nhan_tin_build(bot, _tin("https://discord.com/x/moi"), None))
    assert hoi == ["https://discord.com/x/moi"]
    assert len(goi["verify"]) == 1 and goi["verify"][0]["msg_id"] == 20
    assert goi["verify"][0]["link_tin"] == "https://discord.com/x/moi"


def test_tin_da_xu_ly_roi_khong_hoi_lai(monkeypatch):
    """Quet lai tin lo sau restart: dung tin da luu (cung link) thi im."""
    hoi = _gia_lap(monkeypatch)
    bot, goi, _ = _bot(_cu("https://discord.com/x/cu"))
    asyncio.run(nb.nhan_tin_build(bot, _tin("https://discord.com/x/cu"), None))
    assert hoi == [] and goi["verify"] == []


def test_nguoi_thuong_o_kenh_project_nhac_lai_version_khong_hoi(monkeypatch):
    """Chi tin cua dev (webhook / bot Assistant) moi tinh la day lai; nguoi chat nhac version thi im."""
    hoi = _gia_lap(monkeypatch, bot_dev=6)
    bot, goi, _ = _bot(_cu())
    m = _tin("https://discord.com/x/chat", tac_gia=77)
    m.author.bot = False
    asyncio.run(nb.nhan_tin_build(bot, m, None))
    assert hoi == [] and goi["verify"] == []


def test_luot_cu_dang_chay_thi_ghi_vao_tin_goc_khong_tao_luot_trung(monkeypatch):
    hoi = _gia_lap(monkeypatch)
    bot, goi, kenh = _bot(_cu(), dang_chay=True)
    canh_bao = []

    async def ghi(bot_, c, kenh_, dong):
        canh_bao.append((c["msg_id"], dong))
    monkeypatch.setattr(nb, "_canh_bao", ghi)
    asyncio.run(nb.nhan_tin_build(bot, _tin("https://discord.com/x/moi", webhook=4), None))
    assert hoi == [] and goi["verify"] == []
    assert len(canh_bao) == 1 and canh_bao[0][0] == 10 and "Dev đẩy lại" in canh_bao[0][1]


def test_build_chi_co_verify_thi_xep_verify_lai(monkeypatch):
    """Build fix bug khong ghi SDK (bot chi luu tin verify): day lai cung version -> verify lai tren ban moi."""
    hoi = _gia_lap(monkeypatch)
    luu = {"30": {"msg_id": 30, "ma": "AIP922", "version": "3.9.0 (32)", "package": "p", "loai_job": "verify",
                  "link_tin": "https://discord.com/x/cu"}}
    bot, goi, _ = _bot(luu)
    asyncio.run(nb.nhan_tin_build(bot, _tin("https://discord.com/x/moi"), None))
    assert hoi == [] and len(goi["verify"]) == 1 and goi["verify"][0]["link_tin"] == "https://discord.com/x/moi"
