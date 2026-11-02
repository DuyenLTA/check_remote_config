"""Chia luot test cho may phu: kenh / bot gia, khong cham Discord that."""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

from rcr import bot_hang_doi, bot_may_phu as mp


class _Kenh:
    def __init__(self):
        self.gui = []

    async def send(self, chu, file=None):
        self.gui.append((chu.split()[1], json.loads(file.fp.read())))


def _bot(tmp_path, **kw):
    q = bot_hang_doi.HangDoi(tmp_path / "q.json")
    return SimpleNamespace(q=q, xin_cho={}, ban={}, da_xin={}, may_san=set(), out=tmp_path, ten_may="ubuntu", **kw)


def _job(i):
    return {"msg_id": i, "package": f"p{i}", "version": "1.0 (1)", "ma": f"AIP{i}"}


def test_bot_chinh_giao_job_cho_may_phu_xin_va_khong_giao_trung(tmp_path):
    bot, k = _bot(tmp_path), _Kenh()
    bot.q.them(_job(1))
    bot.q.nho_tin({**_job(1), "tutorial": "3.6.1"})
    mp.nhan_o_may_chinh(bot, "xin", {"may": "ubuntu", "serial": "S9", "ten": "Pixel (S9)"})
    asyncio.run(mp.chia_viec(bot, k))
    loai, d = k.gui[0]
    assert loai == "giao" and d["serial"] == "S9" and d["job"]["msg_id"] == 1 and d["tin"]["tutorial"] == "3.6.1"
    assert bot.xin_cho == {} and bot.q.lay() is None             # job da giao -> may khac khong lay
    # bot chinh khoi dong lai: dang_o luu trong file -> van khong giao trung
    assert bot_hang_doi.HangDoi(tmp_path / "q.json").lay() is None


def test_xong_luu_tin_bug_va_bo_job_khoi_hang(tmp_path):
    bot = _bot(tmp_path)
    bot.q.cap_nhat(bot.q.jobs[bot.q.them(_job(1)) - 1], dang_o="ubuntu:S9")
    mp.nhan_o_may_chinh(bot, "xong", {"may": "ubuntu", "msg_id": 1, "tin": {**_job(1), "bugs": [{"case": "EV-27"}]}})
    assert bot.q.jobs == [] and bot.q.tin_cua(1)["bugs"] == [{"case": "EV-27"}]


def test_may_phu_khoi_dong_lai_hoac_tra_job_thi_job_ve_hang(tmp_path):
    bot = _bot(tmp_path)
    bot.q.cap_nhat(bot.q.jobs[bot.q.them(_job(1)) - 1], dang_o="ubuntu:S9")
    bot.q.cap_nhat(bot.q.jobs[bot.q.them(_job(2)) - 1], dang_o="ubuntu2:S1")
    bot.xin_cho = {("ubuntu", "S8"): "x", ("ubuntu2", "S1"): "y"}
    mp.nhan_o_may_chinh(bot, "khoi_dong", {"may": "ubuntu"})
    assert bot.q.lay()["msg_id"] == 1 and list(bot.xin_cho) == [("ubuntu2", "S1")]
    mp.nhan_o_may_chinh(bot, "tra", {"may": "ubuntu2", "msg_id": 2})
    assert bot.q.lay()["msg_id"] == 2


def test_may_phu_chi_nhan_job_cua_minh_may_rut_cap_thi_tra(tmp_path):
    k = _Kenh()
    bot = _bot(tmp_path)
    asyncio.run(mp.nhan_o_may_phu(bot, "giao", {"may": "khac", "serial": "S9", "job": _job(1)}, k))
    assert k.gui == [] and bot.ban == {}
    asyncio.run(mp.nhan_o_may_phu(bot, "giao", {"may": "ubuntu", "serial": "S9", "job": _job(1)}, k))
    assert k.gui == [("tra", {"may": "ubuntu", "msg_id": 1})] and bot.ban == {}   # S9 khong cam


def test_may_phu_chay_job_roi_bao_xong_kem_tin_moi(tmp_path):
    k = _Kenh()

    async def chay_tren(job, serial, ten):
        assert ten == "Pixel (S9) @ubuntu" and bot.ban == {"S9": 1}
        bot.q.nho_tin({**bot.q.tin_cua(1), "bugs": [{"case": "EV-27"}]})
        bot.ban.pop(serial)
    bot = _bot(tmp_path, _chay_tren=chay_tren)
    bot.may_san = {"S9"}

    async def chay():
        await mp.nhan_o_may_phu(bot, "giao", {"may": "ubuntu", "serial": "S9", "ten": "Pixel (S9)", "job": _job(1),
                                              "tin": _job(1), "jobs": [_job(1)]}, k)
        await asyncio.sleep(0.05)
    asyncio.run(chay())
    loai, d = k.gui[-1]
    assert loai == "xong" and d["msg_id"] == 1 and d["tin"]["bugs"] == [{"case": "EV-27"}]


def test_may_phu_xin_job_cho_may_ranh_mot_lan(tmp_path, monkeypatch):
    k = _Kenh()
    bot = _bot(tmp_path)
    nhip = []
    bot.is_closed = lambda: len(nhip) >= 2

    async def may():
        nhip.append(1)
        return [SimpleNamespace(serial="S9", model="Pixel"), SimpleNamespace(serial="S8", model="OPPO")]
    bot.ban = {"S8": 5}
    monkeypatch.setattr(mp, "NHIP", 0)
    asyncio.run(mp.vong_may_phu(bot, k, may))
    assert [x[0] for x in k.gui] == ["khoi_dong", "xin"] and k.gui[1][1]["serial"] == "S9"


def test_bot_chinh_khoi_dong_lai_thi_may_phu_xin_lai_ngay(tmp_path):
    bot = _bot(tmp_path)
    bot.da_xin = {"S9": 123.0}
    asyncio.run(mp.nhan_o_may_phu(bot, "chinh_khoi_dong", {"may": "chinh"}, _Kenh()))
    assert bot.da_xin == {}


def test_may_phu_tat_han_qua_han_thi_thu_hoi_job(tmp_path):
    bot, k = _bot(tmp_path), _Kenh()
    bot.q.them(_job(1))
    bot.q.them(_job(2))
    bot.q.jobs[1]["dang_o"] = "ubuntu:S8"                    # giao tu ban cu, chua co giao_luc
    mp.nhan_o_may_chinh(bot, "xin", {"may": "ubuntu", "serial": "S9"})
    asyncio.run(mp.chia_viec(bot, k))                         # job 1 -> ubuntu:S9
    t0 = bot.q.jobs[0]["giao_luc"]
    kenh = _KenhLichSu([])
    assert asyncio.run(mp.thu_hoi_job_treo(bot, kenh, t0 + 60)) == []          # job 2 bat dau tinh han tu day
    assert asyncio.run(mp.thu_hoi_job_treo(bot, kenh, t0 + mp.HAN_MAY_PHU)) == []
    thu = asyncio.run(mp.thu_hoi_job_treo(bot, kenh, t0 + mp.HAN_MAY_PHU + 61))
    assert [j["msg_id"] for j in thu] == [1, 2] and thu[0]["dang_o"] == "ubuntu:S9"
    q2 = bot_hang_doi.HangDoi(tmp_path / "q.json")            # luu file: khoi dong lai van chay lai
    assert q2.lay()["msg_id"] == 1 and "dang_o" not in q2.jobs[0]
    # may phu bao xong muon (job da chay lai o may khac): khong xoa job dang chay
    mp.nhan_o_may_chinh(bot, "xong", {"may": "ubuntu", "msg_id": 1, "tin": {**_job(1), "bugs": [1]}})
    assert [j["msg_id"] for j in bot.q.jobs] == [1, 2] and "bugs" not in (bot.q.tin_cua(1) or {})


class _TinDp:
    def __init__(self, loai, d):
        self.content = f"RCR {loai} ubuntu"
        self.attachments = [SimpleNamespace(read=self._doc(d))]

    @staticmethod
    def _doc(d):
        async def read():
            return json.dumps(d).encode()
        return read


class _KenhLichSu:
    def __init__(self, tin):
        self.tin = tin

    def history(self, after=None, limit=None):
        async def gen():
            for m in self.tin:
                yield m
        return gen()


def test_tin_xong_bi_lo_luc_bot_chinh_khoi_dong_thi_khong_chay_lai(tmp_path):
    bot = _bot(tmp_path)
    bot.q.cap_nhat(bot.q.jobs[bot.q.them(_job(1)) - 1], dang_o="ubuntu:S9", giao_luc=1000.0)
    kenh = _KenhLichSu([_TinDp("xin", {"may": "ubuntu", "serial": "S9"}),
                        _TinDp("xong", {"may": "ubuntu", "msg_id": 1, "tin": {**_job(1), "bugs": [1]}})])
    assert asyncio.run(mp.thu_hoi_job_treo(bot, kenh, 1000.0 + mp.HAN_MAY_PHU + 1)) == []
    assert bot.q.jobs == [] and bot.q.tin_cua(1)["bugs"] == [1]
