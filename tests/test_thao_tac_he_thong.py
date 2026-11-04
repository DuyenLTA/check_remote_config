"""Thao tac he thong: keo thanh thong bao, kill app. AIP936 RG08-03/05 03/11/2026: hai cau nay bi dich thanh vuot
man hinh app - thao tac sai ma van ra ket qua."""

from __future__ import annotations

import asyncio

import pytest

from rcr import act_exec, act_resolver


@pytest.mark.parametrize("cau, kind, mo_lai", [
    ("Kéo thanh notification xuống rồi vuốt lên đóng (không tap notification).", "thong_bao", None),
    ("Vuốt app khỏi Recent (kill), mở lại từ launcher.", "kill", True),
    ("Ở OB1 kill app, mở lại từ launcher.", "kill", True),
    ("Không bấm tick, kill app (vuốt khỏi Recent).", "kill", False),
    ("Vuốt sang trái.", "swipe", None),
])
def test_dich_thao_tac_he_thong(cau, kind, mo_lai):
    a = act_resolver.resolve(cau, []).summary
    assert a["kind"] == kind
    if mo_lai is not None:
        assert a["mo_lai"] is mo_lai


def _chay(monkeypatch, action):
    lenh = []

    class C:
        async def shell(self, serial, *args):
            lenh.append(args)
            return "", "", 0

    async def ngu(_s):
        return None
    monkeypatch.setattr(act_exec.asyncio, "sleep", ngu)
    monkeypatch.setattr(act_exec.device_app, "launch", lambda c, s, p: _ghi(lenh, "launch"))
    monkeypatch.setattr(act_exec.device_app, "wait_foreground", lambda c, s, p: _ghi(lenh, "foreground"))

    async def focus(client, serial):
        return "com.ai.app", "x.VslTemplate4Language14Activity"
    monkeypatch.setattr(act_exec.device_app, "focus", focus)
    ctx = act_exec.ctx_moi("com.ai.app")
    asyncio.run(act_exec.lam(C(), "S", action, {}, ctx))
    return lenh


async def _ghi(lenh, ten):
    lenh.append((ten,))


def test_keo_thong_bao_roi_dong_khong_tap(monkeypatch):
    lenh = _chay(monkeypatch, act_resolver.ThongBao(3.0, "x"))
    assert ("cmd", "statusbar", "expand-notifications") in lenh and ("cmd", "statusbar", "collapse") in lenh
    assert not any(l and l[0] == "input" for l in lenh)


def test_kill_roi_mo_lai_tu_launcher(monkeypatch):
    lenh = _chay(monkeypatch, act_resolver.KillMoLai(True, "x"))
    assert lenh[0] == ("am", "force-stop", "com.ai.app") and ("launch",) in lenh
    assert ("launch",) not in _chay(monkeypatch, act_resolver.KillMoLai(False, "x"))


@pytest.mark.parametrize("cau, thu_tu", [("Chọn ngôn ngữ.", 0), ("Click 1 ngôn ngữ khác.", 1)])
def test_chon_mot_ngon_ngu_khong_ten(cau, thu_tu):
    a = act_resolver.resolve(cau, []).summary
    assert a["kind"] == "chon_mot_ngon_ngu" and a["thu_tu"] == thu_tu


def test_chon_ngon_ngu_bam_dong_chon_duoc_ngay(monkeypatch):
    """Dump that LFO1 AIP936: Francais / English co mui ten mo rong, dong chon duoc ngay dau tien la tieng Hindi."""
    from pathlib import Path
    xml = (Path(__file__).parent / "fixtures" / "uidump_lfo1_next_tat_ban_tay.xml").read_text(encoding="utf-8")
    bam = []

    async def dump(client, serial):
        return xml

    async def tap(client, serial, x, y):
        bam.append((x, y))

    async def ngu(_s):
        return None
    from rcr import ui_dump
    monkeypatch.setattr(ui_dump, "dump", dump)
    monkeypatch.setattr(act_exec.device_app, "tap", tap)
    monkeypatch.setattr(act_exec.asyncio, "sleep", ngu)
    ten = asyncio.run(act_exec._chon_mot_ngon_ngu(None, "S", 0, {}))
    assert ten not in ("Français", "English") and bam


def test_o_nen_cho_toi_khi_ad_resume_load_xong(monkeypatch):
    """Khong cho cung 10s: log co trackAdLoadSuccess thi mo lai."""
    goi = []

    class C:
        async def shell(self, serial, *args):
            goi.append(args)
            if args[:1] == ("echo",):
                return "1793694962.712", "", 0
            n = len([g for g in goi if g[:1] == ("logcat",)])
            if n == 1:      # native man Question load xong truoc -> KHONG duoc mo lai
                return "I AdEventLogger: trackAdLoadFailed - adUnitId: *****669 - adType: native", "", 0
            return "I AdEventLogger: trackAdLoadSuccess - adUnitId: *****440 - adType: app_open", "", 0

    dong_ho = iter(range(0, 100))
    monkeypatch.setattr(act_exec.time, "monotonic", lambda: float(next(dong_ho)))

    async def ngu(_s):
        return None

    async def home(client, serial):
        goi.append(("home",))
    monkeypatch.setattr(act_exec.asyncio, "sleep", ngu)
    monkeypatch.setattr(act_exec.device_motion, "home", home)
    record = {}
    asyncio.run(act_exec.lam(C(), "S", act_resolver.Background(10.0, "x"), record, act_exec.ctx_moi("p")))
    assert record["cho_nen_giay"] < 10 and len([g for g in goi if g[:1] == ("logcat",)]) == 2
