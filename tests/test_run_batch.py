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
    case="a,b,c", no_actions=True, no_walk=True, keep=False, out_dir=".",
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


def run(monkeypatch, outcomes):
    """outcomes: {key: Exception | verdict}"""
    async def run_case(client, baseline, runs, pre, steps, expects, goto="", **kw):
        key = run.order.pop(0)
        got = outcomes[key]
        if isinstance(got, Exception):
            raise got
        return {"verdict": got, "runs": [{"overrides": {}, "verdict": got}]}, baseline

    run.order = ["a", "b", "c"]
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
