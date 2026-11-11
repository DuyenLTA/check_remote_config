"""Dev bao lai CUNG ma + version (build lai, khong tang so) o kenh project: bot phai hoi Check lai + xep verify.

11/11/2026: AIP922 3.9.0 (32) day lai them TikTok config + ads-core 2.0.1, bot im vi coi la build da hoi roi.
"""
from __future__ import annotations

import asyncio
from types import SimpleNamespace

from rcr import bot_nhan_build as nb

TIN_DEV = ("Bản build **AIP922** v3.9.0 (32) đã được hoàn thiện. Please check\n"
           "- apply Tutorial SDK 3.7.1, fix ANR cold-start, add TikTok ad config")
PHUT = 60 * 1000


def sf(phut: int) -> int:
    """Snowflake Discord cua mot tin gui luc `phut` (tinh tu moc bat ky)."""
    return (phut * PHUT) << 22


class _Kenh:
    def __init__(self):
        self.sent = []

    async def send(self, chu, **k):
        self.sent.append(chu)


def _bot(tin_luu: dict, dang_chay: bool = False):
    goi = {"verify": []}
    da_bao = set()

    def bao_lan_dau(khoa):
        moi = khoa not in da_bao
        da_bao.add(khoa)
        return moi
    bot = SimpleNamespace(kenh_qa=1, kenh_build={1}, duyet=set(), role=0)
    bot.q = SimpleNamespace(tin=tin_luu, vi_tri=lambda mid: 1 if dang_chay else None, bao_lan_dau=bao_lan_dau,
                            nho_tin=lambda c: tin_luu.update({str(c["msg_id"]): c}))
    bot._duoc_duyet = lambda user: False

    async def xep_verify(c, kenh):
        goi["verify"].append(c)

    async def hoi_lai(m, tin):
        goi.setdefault("hoi_qa", []).append(tin)
    bot._xep_verify, bot._hoi_lai = xep_verify, hoi_lai
    kenh = _Kenh()
    bot.get_channel = lambda cid: kenh
    return bot, goi, kenh


def _tin(link, phut=24 * 60, webhook=None, tac_gia=6, chu=TIN_DEV):
    return SimpleNamespace(id=sf(phut), author=SimpleNamespace(bot=True, id=tac_gia), webhook_id=webhook,
                           guild=SimpleNamespace(id=9), message_snapshots=[], content=chu, jump_url=link,
                           channel=SimpleNamespace(id=8, name="aip922-nexsus-ai-video-official-group"))


def _cu(link="https://discord.com/x/cu", loai_job=None):
    c = {"msg_id": sf(0), "ma": "AIP922", "version": "3.9.0 (32)", "package": "p.aip922", "loai_ban": "release",
         "sdk": True, "tutorial": "3.7.1", "link_tin": link}
    if loai_job:
        c["loai_job"] = loai_job
    return {str(c["msg_id"]): c}


def _gia_lap(monkeypatch, bot_dev=6):
    monkeypatch.setattr(nb.bot_kenh_project, "la_bot_dev", lambda i: i == bot_dev)
    hoi = []

    async def hoi_lai_build(bot, tin, link_tin, gui, doi=None):
        if any(bot.q.vi_tri(t["msg_id"]) is not None for t in nb.tin_da_hoi(bot, tin)):
            return f"Build **{tin['ma']}** đang chờ / đang chạy"
        bot.q.nho_tin({**next(iter(_cu().values())), "msg_id": sf(24 * 60 + 1), "link_tin": link_tin, **(doi or {})})
        hoi.append((link_tin, doi))
        return "Đã gửi tin hỏi Check mới: u"
    monkeypatch.setattr(nb, "hoi_lai_build", hoi_lai_build)
    moi = []

    async def hoi_build_moi(bot, tin, link_tin, kenh, out):
        moi.append(link_tin)
    monkeypatch.setattr(nb, "hoi_build_moi", hoi_build_moi)
    return hoi, moi


def test_dev_day_lai_cung_version_thi_hoi_check_lai_theo_sdk_moi_va_xep_verify(monkeypatch):
    hoi, _ = _gia_lap(monkeypatch)
    bot, goi, _ = _bot(_cu())
    asyncio.run(nb.nhan_tin_build(bot, _tin("https://discord.com/x/moi"), None))
    assert [h[0] for h in hoi] == ["https://discord.com/x/moi"] and hoi[0][1]["tutorial"] == "3.7.1"
    assert len(goi["verify"]) == 1 and goi["verify"][0]["msg_id"] == sf(24 * 60 + 1)
    assert goi["verify"][0]["link_tin"] == "https://discord.com/x/moi"


def test_cung_tin_dev_den_hai_lan_chi_xu_ly_mot_lan(monkeypatch):
    """Reconnect phat lai dung tin vua xu ly (link chua kip luu o nhanh ban): khong hoi / canh bao lap."""
    hoi, _ = _gia_lap(monkeypatch)
    bot, goi, _ = _bot(_cu())
    canh_bao = []

    async def ghi(bot_, c, kenh_, dong):
        canh_bao.append(dong)
    monkeypatch.setattr(nb, "_canh_bao", ghi)
    bot.q.vi_tri = lambda mid: 1
    for _ in range(2):
        asyncio.run(nb.nhan_tin_build(bot, _tin("https://discord.com/x/moi", webhook=4), None))
    assert hoi == [] and len(canh_bao) == 1 and len(goi["verify"]) == 1   # nhanh ban van xep verify, chi mot lan


def test_tin_cu_hon_lan_hoi_gan_nhat_khong_tinh_la_day_lai(monkeypatch):
    """Build hoi qua /check (link rong): quet lai tin lo khi reconnect phat lai tin dev CU -> im."""
    hoi, moi = _gia_lap(monkeypatch)
    luu = _cu(link="")
    c = next(iter(luu.values()))
    c["msg_id"] = sf(10)
    bot, goi, _ = _bot({str(c["msg_id"]): c})
    asyncio.run(nb.nhan_tin_build(bot, _tin("https://discord.com/x/dev-0", phut=0), None))
    assert hoi == [] and moi == [] and goi["verify"] == []


def test_dev_dang_cheo_kenh_gan_nhu_cung_luc_khong_hoi_trung(monkeypatch):
    hoi, _ = _gia_lap(monkeypatch)
    bot, goi, _ = _bot(_cu())
    asyncio.run(nb.nhan_tin_build(bot, _tin("https://discord.com/x/kenh-khac", phut=5), None))
    assert hoi == [] and goi["verify"] == []


def test_dev_tra_loi_nhac_version_khong_phai_tin_build(monkeypatch):
    hoi, _ = _gia_lap(monkeypatch)
    bot, goi, _ = _bot(_cu())
    asyncio.run(nb.nhan_tin_build(bot, _tin("https://discord.com/x/rep", chu="AIP922 đã fix trên v3.9.0 (32) nhé"), None))
    assert hoi == [] and goi["verify"] == []


def test_nguoi_thuong_o_kenh_project_nhac_lai_version_khong_hoi(monkeypatch):
    hoi, _ = _gia_lap(monkeypatch, bot_dev=6)
    bot, goi, _ = _bot(_cu())
    m = _tin("https://discord.com/x/chat", tac_gia=77)
    m.author.bot = False
    asyncio.run(nb.nhan_tin_build(bot, m, None))
    assert hoi == [] and goi["verify"] == []


def test_luot_cu_dang_chay_thi_ghi_vao_tin_goc_cua_luot_do(monkeypatch):
    hoi, _ = _gia_lap(monkeypatch)
    luu = _cu()
    cu_a = next(iter(luu.values()))
    cu_b = {**cu_a, "msg_id": sf(30)}                      # tin hoi lai B (chua bam), luot dang chay o A
    luu[str(cu_b["msg_id"])] = cu_b
    bot, goi, _ = _bot(luu)
    bot.q.vi_tri = lambda mid: 1 if mid == cu_a["msg_id"] else None
    canh_bao = []

    async def ghi(bot_, c, kenh_, dong):
        canh_bao.append((c["msg_id"], dong))
    monkeypatch.setattr(nb, "_canh_bao", ghi)
    asyncio.run(nb.nhan_tin_build(bot, _tin("https://discord.com/x/moi", webhook=4), None))
    assert hoi == [] and canh_bao[0][0] == cu_a["msg_id"] and "Dev đẩy lại" in canh_bao[0][1]
    assert len(goi["verify"]) == 1


def test_lan_dau_khong_ghi_sdk_lan_nay_co_thi_hoi_check_nhu_build_moi(monkeypatch):
    hoi, moi = _gia_lap(monkeypatch)
    bot, goi, _ = _bot(_cu(loai_job="verify"))
    asyncio.run(nb.nhan_tin_build(bot, _tin("https://discord.com/x/moi"), None))
    assert moi == ["https://discord.com/x/moi"] and hoi == []


def test_build_chi_co_verify_khong_ghi_sdk_thi_xep_verify_lai(monkeypatch):
    hoi, moi = _gia_lap(monkeypatch)
    bot, goi, _ = _bot(_cu(loai_job="verify"))
    chu = "Bản build **AIP922** v3.9.0 (32) đã được hoàn thiện. Please check\n- fix crash màn Home"
    asyncio.run(nb.nhan_tin_build(bot, _tin("https://discord.com/x/moi", chu=chu), None))
    assert hoi == [] and moi == [] and len(goi["verify"]) == 1
    assert goi["verify"][0]["link_tin"] == "https://discord.com/x/moi"
