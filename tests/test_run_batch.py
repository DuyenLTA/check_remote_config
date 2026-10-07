"""Test chay nhieu case lien tiep. Khong can may that.

Diem phai gac:
  - MOT case hong khong duoc giet ca luot (53 case chay 50 phut)
  - case hong van len report, khong bi bo qua im lang
  - mat ket noi may thi DUNG han: chay tiep la vo nghia
"""

from __future__ import annotations

import asyncio
import types

import pytest

from rcr import case_run, rc_patch, report_data, run_batch
from rcr.adb_parsers import AdbTransportError
from rcr.models import RcError

ARGS = types.SimpleNamespace(
    case="a,b,c", no_actions=True, no_walk=True, full_walk=False, keep=False, out_dir=".",
    no_dex_check=True, report="", app_label="", tab="", sdk="",
)
RUNNABLE = {k: {"runs": ({"k": "v"},), "precondition": "", "actions": (), "expects": ()}
            for k in ("a", "b", "c")}
ROWS = [{"key": k, "tab": "TC SDK 3.5.0", "label": f"case {k}"} for k in ("a", "b", "c")]


class FakeBaseline:
    serial = "S"
    package = "com.ai.app"
    configs = {"k": "v"}
    mirrored_keys = frozenset()


def run(monkeypatch, outcomes, lan=1):
    """outcomes: {key: Exception | verdict}"""
    async def run_case(client, baseline, runs, pre, steps, expects, goto="", **kw):
        key = run.order.pop(0)
        got = outcomes[key]
        if isinstance(got, list):          # ket qua tung lan chay lai
            got = got.pop(0)
            if outcomes[key]:
                run.order.insert(0, key)
        if isinstance(got, Exception):
            raise got
        return {"verdict": got, "runs": [{"overrides": {}, "verdict": got}]}, baseline

    run.order = ["a", "b", "c"]
    monkeypatch.setattr(run_batch, "LAN_CHAY_LAI", lan)
    monkeypatch.setattr(case_run, "run_case", run_case)
    monkeypatch.setattr(rc_patch, "restore", _noop_restore)
    monkeypatch.setattr(run_batch.tc_select, "pick", lambda runnable, k: k)
    return asyncio.run(
        run_batch.run_cases(None, FakeBaseline(), ARGS, RUNNABLE, ROWS, {"sdk": "3.5.0"})
    )


async def _noop_restore(client, baseline):
    return None


def test_mot_case_hong_khong_giet_ca_luot(monkeypatch):
    recs = run(monkeypatch, {"a": "PASS", "b": RcError("khong dat duoc swipe_onb2='null'"), "c": "PASS"})
    assert [r["key"] for r in recs] == ["a", "b", "c"]
    assert [r["verdict"] for r in recs] == ["PASS", "BLOCKED", "PASS"]
    # case hong van len report kem ly do that
    assert "swipe_onb2" in recs[1]["actual"]


def test_mat_ket_noi_may_thi_dung_han(monkeypatch):
    with pytest.raises(AdbTransportError):
        run(monkeypatch, {"a": "PASS", "b": AdbTransportError("device offline"), "c": "PASS"})


def test_case_hong_van_giu_ten_va_nhom_de_tim(monkeypatch):
    recs = run(monkeypatch, {"a": RcError("x"), "b": "PASS", "c": "PASS"})
    rec = report_data.error_record("a", ROWS[0], "x")
    assert rec["label"] == "case a" and rec["tab"] == "3.5.0"
    assert recs[0]["group"] == "Không chạy được"


def test_go_nham_ten_case_khong_lam_mat_ket_qua_da_chay(monkeypatch):
    """Ten case sai la loi cua nguoi go - khong duoc xoa cong cua 2 case truoc."""
    def pick(runnable, wanted):
        if wanted == "b":
            raise RcError(f"Case {wanted} khong ton tai")
        return wanted

    monkeypatch.setattr(run_batch.tc_select, "pick", pick)

    async def run_case(client, baseline, runs, pre, steps, expects, goto="", **kw):
        return {"verdict": "PASS", "runs": [{"overrides": {}, "verdict": "PASS"}]}, baseline

    monkeypatch.setattr(case_run, "run_case", run_case)
    monkeypatch.setattr(rc_patch, "restore", _noop_restore)
    recs = asyncio.run(
        run_batch.run_cases(None, FakeBaseline(), ARGS, RUNNABLE, ROWS, {"sdk": "3.5.0"})
    )
    assert [r["verdict"] for r in recs] == ["PASS", "BLOCKED", "PASS"]


def test_cong_tac_tong_ads_luon_bat_lam_nen_tru_khi_case_tu_dat(monkeypatch):
    """Sau `pm clear` config moi co enable_all_ads=false -> khong ads nao chay."""
    nhan: list[dict] = []

    async def run_case(client, baseline, runs, *a, **kw):
        nhan.extend(runs)
        return {"verdict": "PASS", "runs": [{"overrides": {}, "verdict": "PASS"}]}, baseline

    class Bl(FakeBaseline):
        configs = {"k": "v", "enable_all_ads": "false", "enable_all_ads_tutorial": "false"}

    runnable = {"a": {"runs": ({"k": "v"},), "precondition": "", "actions": (), "expects": ()},
                "b": {"runs": ({"enable_all_ads": "false"},), "precondition": "",
                      "actions": (), "expects": ()}}
    monkeypatch.setattr(case_run, "run_case", run_case)
    monkeypatch.setattr(run_batch.tc_select, "pick", lambda r, k: k)
    args = types.SimpleNamespace(**{**vars(ARGS), "case": "a,b"})
    asyncio.run(run_batch.run_cases(None, Bl(), args, runnable, ROWS, {"sdk": "3.5.0"}))
    assert nhan[0] == {"enable_all_ads": "true", "enable_all_ads_tutorial": "true", "k": "v"}
    assert nhan[1]["enable_all_ads"] == "false"          # case tu dat thi case thang
    assert "enable_all_ads_in_app" not in nhan[0]        # app khong co key thi khong them


def test_ket_qua_lo_lung_thi_tu_chay_lai_toi_khi_ra_PASS_FAIL(monkeypatch):
    """Report chi PASS/FAIL: doc file trung luc SDK ghi -> chay lai, khong BLOCKED."""
    recs = run(monkeypatch, {"a": [RcError("activate.json khong phai JSON"), "PASS"],
                             "b": ["NEEDS_HUMAN", "FAIL", "FAIL"], "c": "PASS"}, lan=3)
    assert [r["verdict"] for r in recs] == ["PASS", "FAIL", "PASS"]


def test_fail_chi_len_report_khi_lap_lai(monkeypatch):
    """Mot lan FAIL co the do config bi fetch de / tool nhin tre: phai chay lai xac nhan."""
    recs = run(monkeypatch, {"a": ["FAIL", "FAIL"], "b": "PASS", "c": "PASS"}, lan=3)
    assert recs[0]["verdict"] == "FAIL"
    assert recs[0]["lich_su_verdict"] == ["FAIL", "FAIL"]
    assert not recs[0]["khong_on_dinh"]


def test_fail_roi_pass_thi_phan_xu_va_danh_dau_khong_on_dinh(monkeypatch):
    recs = run(monkeypatch, {"a": ["FAIL", "PASS", "PASS"], "b": "PASS", "c": "PASS"}, lan=3)
    assert recs[0]["verdict"] == "PASS"
    assert recs[0]["lich_su_verdict"] == ["FAIL", "PASS", "PASS"]
    assert recs[0]["khong_on_dinh"] and "KHÔNG ỔN ĐỊNH" in recs[0]["actual"]


def test_pass_ngay_lan_dau_khong_chay_lai(monkeypatch):
    recs = run(monkeypatch, {"a": "PASS", "b": "PASS", "c": "PASS"}, lan=3)
    assert [r["lich_su_verdict"] for r in recs] == [["PASS"]] * 3
