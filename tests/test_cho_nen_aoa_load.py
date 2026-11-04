"""Cho o nen truoc khi mo lai: dung som khi AOA load xong, cho them khi AOA da request ma chua co ket qua (may cham)."""

import asyncio

from rcr import act_exec

REQ = "AdEventLogger: trackAdRequest adPlatform:Admob  - adUnitId: *****440  -  adType: APP_OPEN"
OK = "AdEventLogger: trackAdLoadSuccess - adUnitId: *****440 - adType: app_open"


class _Client:
    def __init__(self, logs):
        self.logs, self.n = logs, 0

    async def shell(self, *_a):
        out = self.logs[min(self.n, len(self.logs) - 1)]
        self.n += 1
        return out, "", 0


def _chay(monkeypatch, logs, toi_da=0.3):
    monkeypatch.setattr(act_exec, "CHO_NEN_TOI_THIEU", 0.0)
    monkeypatch.setattr(act_exec, "CHO_NEN_KEO_DAI", 0.6)
    real_sleep = asyncio.sleep
    monkeypatch.setattr(act_exec.asyncio, "sleep", lambda s: real_sleep(min(s, 0.05)))
    c = _Client(logs)
    giay = asyncio.run(act_exec._cho_ad_resume_load(c, "S", "moc", toi_da))
    return giay, c.n


def test_dung_som_khi_aoa_load_xong(monkeypatch):
    giay, n = _chay(monkeypatch, [REQ, REQ + "\n" + OK])
    assert n == 2 and giay < 0.3


def test_khong_co_request_aoa_thi_cho_dung_toi_da(monkeypatch):
    giay, _ = _chay(monkeypatch, [""])
    assert 0.3 <= giay < 0.6


def test_aoa_dang_load_thi_cho_them_toi_moc_keo_dai(monkeypatch):
    giay, _ = _chay(monkeypatch, [REQ])
    assert giay >= 0.6
