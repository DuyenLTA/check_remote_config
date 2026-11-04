"""Cho o nen truoc khi mo lai: dung som khi AOA san sang, cho toi moc keo dai khi chua; ghi `aoa_san_sang`."""

import asyncio

from rcr import act_exec

LOAD = "AdEventLogger: trackAdLoadSuccess - adUnitId: *****440  -  adType: app_open  -  wonAdSource: AdMob"
SHOW = "AdEventLogger: trackAdShowSuccess - adUnitId: *****440  -  adType: app_open  -  showStatus: success"


class _Client:
    def __init__(self, logs):
        self.logs, self.n, self.args = logs, 0, []

    async def shell(self, *a):
        self.args.append(a)
        out = self.logs[min(self.n, len(self.logs) - 1)]
        self.n += 1
        return out, "", 0


def _chay(monkeypatch, logs, pid="123"):
    monkeypatch.setattr(act_exec, "CHO_NEN_TOI_THIEU", 0.0)
    monkeypatch.setattr(act_exec, "CHO_NEN_KEO_DAI", 0.4)
    real_sleep = asyncio.sleep
    monkeypatch.setattr(act_exec.asyncio, "sleep", lambda s: real_sleep(min(s, 0.05)))
    c, rec = _Client(logs), {}
    giay = asyncio.run(act_exec._cho_ad_resume_load(c, "S", "moc", 0.1, pid, rec))
    return giay, rec, c


def test_aoa_san_sang_khi_su_kien_cuoi_la_load():
    assert act_exec.aoa_san_sang(LOAD)
    assert not act_exec.aoa_san_sang(LOAD + "\n" + SHOW)          # da show -> ad cu dung mat, chua co ad moi
    assert act_exec.aoa_san_sang(LOAD + "\n" + SHOW + "\n" + LOAD)
    assert not act_exec.aoa_san_sang("")


def test_dung_som_khi_aoa_load_xong(monkeypatch):
    giay, rec, c = _chay(monkeypatch, [SHOW, SHOW + "\n" + LOAD])
    assert rec["aoa_san_sang"] is True and c.n == 2 and giay < 0.4
    assert "--pid" in c.args[0]                                    # doc log dung tien trinh app


def test_aoa_chua_san_sang_thi_cho_toi_moc_keo_dai_va_ghi_lai(monkeypatch):
    giay, rec, _ = _chay(monkeypatch, [SHOW])
    assert rec["aoa_san_sang"] is False and giay >= 0.4
