"""File luot ghi sau moi case, chay tiep (--tiep), gop luot (--gop). Khong can may that.

Diem phai gac:
  - luot chet giua chung (mat may, Claude Code tat lenh nen) van con ket qua case da xong
  - --tiep khong chay lai case da co ket qua
  - gop: luot sau de luot truoc theo key, khong gop nham luot cua app khac
"""

from __future__ import annotations

import asyncio
import json
import types

import pytest

from rcr import case_run, cli_check, luot_file, rc_patch, report_data, run_batch
from rcr.adb_parsers import AdbTransportError
from rcr.models import RcError
from test_run_batch import ARGS, ROWS, RUNNABLE, FakeBaseline, _noop_restore

PKG = "com.ai.app"


def _chay(monkeypatch, tmp_path, outcomes, **kw):
    da_chay: list[str] = []

    async def run_case(client, baseline, runs, pre, steps, expects, goto="", **_kw):
        key = da_chay[-1]
        got = outcomes[key]
        if isinstance(got, Exception):
            raise got
        return {"verdict": got, "runs": [{"overrides": {}, "verdict": got}]}, baseline

    def pick(runnable, k):
        da_chay.append(k)
        return k

    monkeypatch.setattr(case_run, "run_case", run_case)
    monkeypatch.setattr(rc_patch, "restore", _noop_restore)
    monkeypatch.setattr(run_batch.tc_select, "pick", pick)
    monkeypatch.setattr(run_batch, "LAN_CHAY_LAI", 1)
    path = tmp_path / "run.json"
    meta = {"package": PKG, "case_list": ARGS.case,
            "baseline_tom": luot_file.tom_baseline(FakeBaseline())}
    recs = asyncio.run(run_batch.run_cases(
        None, FakeBaseline(), ARGS, RUNNABLE, ROWS, {"sdk": "3.5.0"},
        luot={"path": path, "meta": meta}, **kw))
    return recs, path, da_chay


def test_luot_chet_giua_chung_van_con_case_da_xong(monkeypatch, tmp_path):
    with pytest.raises(AdbTransportError):
        _chay(monkeypatch, tmp_path, {"a": "PASS", "b": AdbTransportError("device offline")})
    data = json.loads((tmp_path / "run.json").read_text(encoding="utf-8"))
    assert [r["key"] for r in data["records"]] == ["a"]
    assert data["xong"] is False


def test_chay_xong_thi_file_ghi_du_va_danh_dau_xong(monkeypatch, tmp_path):
    recs, path, _ = _chay(monkeypatch, tmp_path, {"a": "PASS", "b": "FAIL", "c": "PASS"})
    data = luot_file.doc(str(path), PKG)
    assert data["xong"] is True
    assert [r["key"] for r in data["records"]] == [r["key"] for r in recs] == ["a", "b", "c"]


def test_tiep_khong_chay_lai_case_da_co_ket_qua(monkeypatch, tmp_path):
    cu = report_data.error_record("a", ROWS[0], "giu nguyen")
    recs, _, da_chay = _chay(monkeypatch, tmp_path, {"b": "PASS", "c": "PASS"},
                             goc=[cu], bo_qua=frozenset({"a"}))
    assert [r["key"] for r in recs] == ["a", "b", "c"]
    assert recs[0] is cu                         # ket qua cu giu nguyen, khong chay lai
    assert da_chay == ["b", "c"]                 # a bo qua truoc ca buoc chon case


def test_gop_luot_sau_de_luot_truoc_giu_thu_tu():
    cu = [{"key": "a", "verdict": "FAIL"}, {"key": "b", "verdict": "BLOCKED"}]
    moi = [{"key": "b", "verdict": "PASS"}, {"key": "c", "verdict": "PASS"}]
    assert luot_file.gop(cu, moi) == [{"key": "a", "verdict": "FAIL"},
                                      {"key": "b", "verdict": "PASS"},
                                      {"key": "c", "verdict": "PASS"}]


def test_khong_gop_nham_luot_cua_app_khac(tmp_path):
    p = tmp_path / "x.json"
    luot_file.ghi(p, {"package": "com.khac.app"}, [], True)
    with pytest.raises(RcError, match="com.khac.app"):
        luot_file.doc(str(p), PKG)


def test_gop_khong_kem_case_dung_lai_report_khong_can_may(monkeypatch, tmp_path):
    meta = {"package": PKG, "tc": {"sdk": "3.5.0", "total": 3, "runnable": 3},
            "baseline_tom": luot_file.tom_baseline(FakeBaseline())}
    a, b = tmp_path / "a.json", tmp_path / "b.json"
    luot_file.ghi(a, meta, [report_data.error_record("a", ROWS[0], "cu"),
                            report_data.error_record("b", ROWS[1], "cu")], True)
    luot_file.ghi(b, meta, [report_data.error_record("b", ROWS[1], "moi")], True)

    def khong_may(*_a, **_k):
        raise AssertionError("dung lai report khong duoc dung toi may")

    monkeypatch.setattr(cli_check, "AdbClient", khong_may)
    report = tmp_path / "gop.html"
    args = cli_check.build_parser().parse_args(
        ["--package", PKG, "--gop", str(a), "--gop", str(b), "--report", str(report)])
    out = asyncio.run(cli_check.run(args))
    assert [(r["key"], r["actual"]) for r in out["cases"]] == [("a", "cu"), ("b", "moi")]
    assert report.exists() and "moi" in report.read_text(encoding="utf-8")


def test_tiep_lay_lai_tham_so_cua_luot_bi_tat(tmp_path):
    p = tmp_path / "run.json"
    luot_file.ghi(p, {"package": PKG, "case_list": "a,b,c", "tc_nguon": "tc.xlsx",
                      "tab": "3.5.0", "report": "out/run.html"},
                  [report_data.error_record("a", ROWS[0], "x")], False)
    args = cli_check.build_parser().parse_args(["--package", PKG, "--tiep", str(p)])
    goc = cli_check.nap_tiep(args)
    assert (args.case, args.tc, args.tab, args.report) == ("a,b,c", "tc.xlsx", "3.5.0", "out/run.html")
    assert [r["key"] for r in goc] == ["a"]


def test_file_luot_canh_report():
    assert luot_file.duong_dan("out/run-x.html", "out", PKG).name == "run-x.luot.json"
    # --report ten .json: file luot khong duoc trung report (report ghi de sau moi case)
    assert luot_file.duong_dan("out/x.json", "out", PKG).name == "x.luot.json"
    assert luot_file.duong_dan("", "out", PKG).name.startswith(f"luot-{PKG}-")


def test_tiep_ma_bo_TC_doi_khong_de_mat_ket_qua_da_xong(monkeypatch, tmp_path):
    """Chay tiep: case da xong khong con trong runnable -> pick hong. Khong duoc de record loi."""
    cu = {**report_data.error_record("a", ROWS[0], "ket qua that"), "verdict": "PASS"}

    def pick(runnable, k):
        if k == "a":
            raise RcError("Case a khong chay tu dong duoc")
        return k

    async def run_case(client, baseline, runs, *a, **kw):
        return {"verdict": "PASS", "runs": [{"overrides": {}, "verdict": "PASS"}]}, baseline

    monkeypatch.setattr(case_run, "run_case", run_case)
    monkeypatch.setattr(rc_patch, "restore", _noop_restore)
    monkeypatch.setattr(run_batch.tc_select, "pick", pick)
    recs = asyncio.run(run_batch.run_cases(None, FakeBaseline(), ARGS, RUNNABLE, ROWS, {"sdk": "3.5.0"},
                                           goc=[cu], bo_qua=frozenset({"a"})))
    assert recs[0] is cu


def test_case_hong_vi_loi_chay_khong_de_ket_qua_cu(monkeypatch, tmp_path):
    cu = {**report_data.error_record("a", ROWS[0], "ket qua that"), "verdict": "FAIL"}
    recs, _, _ = _chay(monkeypatch, tmp_path, {"a": RcError("adb treo"), "b": "PASS", "c": "PASS"},
                       goc=[cu])
    assert recs[0]["verdict"] == "FAIL" and recs[0]["actual"] == "ket qua that"


def test_tiep_chay_lai_case_hong_vi_loi_chay():
    hong = {"key": "a", "verdict": "BLOCKED", "loi_chay": True}
    xong = {"key": "b", "verdict": "PASS"}
    assert luot_file.da_xong([hong, xong]) == frozenset({"b"})


def test_doc_duoc_json_kieu_cu(tmp_path):
    """rc-all.json 10/10 la list record; stdout cu co `cases`."""
    a, b = tmp_path / "a.json", tmp_path / "b.json"
    a.write_text(json.dumps([{"key": "x"}]), encoding="utf-8")
    b.write_text(json.dumps({"package": PKG, "cases": [{"key": "y"}]}), encoding="utf-8")
    assert luot_file.doc_nhieu([str(a), str(b)], PKG)[1] == [{"key": "x"}, {"key": "y"}]


def test_ghi_bi_khoa_file_thi_thu_lai(monkeypatch, tmp_path):
    goc = luot_file.os.replace
    lan = []

    def replace(a, b):
        lan.append(1)
        if len(lan) < 3:
            raise PermissionError("file dang bi mo")
        goc(a, b)

    monkeypatch.setattr(luot_file.os, "replace", replace)
    monkeypatch.setattr(luot_file.time, "sleep", lambda s: None)
    luot_file.ghi(tmp_path / "x.luot.json", {"package": PKG}, [], True)
    assert len(lan) == 3 and (tmp_path / "x.luot.json").exists()


def test_ghi_hong_giua_luot_khong_giet_luot(monkeypatch, tmp_path):
    def hong(*a, **k):
        raise PermissionError("bi khoa")

    monkeypatch.setattr(luot_file, "ghi", hong)
    with pytest.raises(PermissionError):           # chi lan ghi cuoi moi bao loi
        _chay(monkeypatch, tmp_path, {"a": "PASS", "b": "PASS", "c": "PASS"})
