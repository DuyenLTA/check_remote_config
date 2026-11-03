"""Che do chay chuoi (`--chuoi`): case "Tiep noi" chay tiep tren app dang mo; khong PASS tron ven thi chay rieng.

Diem phai gac: ket luan FAIL / chua cham duoc KHONG BAO GIO lay tu lan chay chuoi (log dung chung mot lan mo app
de sinh ket qua gia) - luon tu lan chay rieng tu dau.
"""

from __future__ import annotations

import asyncio
import types

from rcr import case_run, chay_chuoi, log_moc, rc_patch, run_batch

CFG = {"k": "v"}


def _case(pre: str) -> dict:
    return {"runs": (CFG,), "precondition": pre, "actions": (), "expects": ()}


def test_ly_do_khong_noi():
    truoc = chay_chuoi.moc_chuoi("3.6.1#SDK361-RG01-05", [CFG], True)
    noi = _case("1. Tiếp nối SDK361-RG01-05 (cùng lượt, không clear data).")
    assert chay_chuoi.ly_do_khong_noi(truoc, noi, [CFG], ()) == ""
    assert chay_chuoi.ly_do_khong_noi(None, noi, [CFG], ())                                    # case dau
    assert chay_chuoi.ly_do_khong_noi(truoc, _case("1. Clear data."), [CFG], ())                # khong tiep noi
    assert "case vừa chạy" in chay_chuoi.ly_do_khong_noi(
        truoc, _case("1. Tiếp nối SDK361-RG01-03"), [CFG], ())                                  # noi case khac
    assert chay_chuoi.ly_do_khong_noi(truoc, noi, [{"k": "khac"}], ()) == "config khác case trước"
    assert chay_chuoi.ly_do_khong_noi(truoc, noi, [CFG], ("ép",))                               # ep ad fail
    assert chay_chuoi.ly_do_khong_noi(chay_chuoi.moc_chuoi(truoc["key"], [CFG], False), noi, [CFG], ())


def test_chi_nhan_ket_qua_chuoi_khi_pass_tron_ven():
    assert chay_chuoi.nhan_duoc({"verdict": "PASS"})
    assert not chay_chuoi.nhan_duoc({"verdict": "FAIL"})
    assert not chay_chuoi.nhan_duoc({"verdict": "PASS", "chuoi_khong_chac": "log riêng PASS · log dồn FAIL"})
    assert not chay_chuoi.nhan_duoc({"verdict": "PASS", "ad_click": 1})


def _run(monkeypatch, ket_qua, chuoi=True):
    """ket_qua: {(key, 'chuoi'|'rieng'): verdict | dict}. Tra (records, cac lan goi run_case)."""
    goi = []

    async def run_case(client, baseline, runs, pre, steps, expects, goto="", **kw):
        cach = "chuoi" if kw.get("noi_tiep") else "rieng"
        key = _key_dang_chay["k"]
        goi.append((key, cach, kw.get("giu")))
        got = ket_qua[(key, cach)]
        return (got if isinstance(got, dict) else {"verdict": got, "runs": [{"overrides": {}, "verdict": got}]}), baseline
    _key_dang_chay = {"k": ""}

    def pick(runnable, k):
        _key_dang_chay["k"] = k
        return k

    # key that dang "3.6.1#SDK361-T-a": tiep noi doi chieu theo duoi key
    goc_moc = chay_chuoi.moc_chuoi
    monkeypatch.setattr(chay_chuoi, "moc_chuoi", lambda key, runs, giu: goc_moc(f"3.6.1#SDK361-T-{key}", runs, giu))

    async def bay_gio(client, serial):
        return "1793694962.712"

    async def _noop(*a, **k):
        return None
    runnable = {"a": _case("1. Clear data."), "b": _case("1. Tiếp nối SDK361-T-a (cùng lượt)"),
                "c": _case("1. Tiếp nối SDK361-T-b (cùng lượt)")}
    args = types.SimpleNamespace(case="a,b,c", no_actions=True, no_walk=True, full_walk=False, keep=False,
                                 out_dir=".", no_dex_check=True, report="", app_label="", tab="", sdk="", chuoi=chuoi)

    class Base:
        serial, package, configs, mirrored_keys = "S", "com.ai.app", {"k": "v"}, frozenset()
    monkeypatch.setattr(run_batch, "LAN_CHAY_LAI", 1)
    monkeypatch.setattr(case_run, "run_case", run_case)
    monkeypatch.setattr(rc_patch, "restore", _noop)
    monkeypatch.setattr(log_moc, "bay_gio", bay_gio)
    monkeypatch.setattr(run_batch.tc_select, "pick", pick)
    rows = [{"key": k, "tab": "TC SDK 3.6.1", "label": f"case {k}"} for k in "abc"]
    recs = asyncio.run(run_batch.run_cases(None, Base(), args, runnable, rows, {"sdk": "3.6.1"}))
    return recs, goi


def test_case_tiep_noi_pass_thi_nhan_ket_qua_chuoi_khong_chay_lai(monkeypatch):
    recs, goi = _run(monkeypatch, {("a", "rieng"): "PASS", ("b", "chuoi"): "PASS", ("c", "chuoi"): "PASS"})
    assert [(k, c) for k, c, _ in goi] == [("a", "rieng"), ("b", "chuoi"), ("c", "chuoi")]
    assert all(g for _, _, g in goi)                                   # giu config cho case sau noi tiep
    assert [r["verdict"] for r in recs] == ["PASS"] * 3
    assert [r["noi_chuoi"] for r in recs] == [False, True, True]


def test_chuoi_khong_pass_thi_chay_rieng_va_lay_ket_qua_chay_rieng(monkeypatch):
    """FAIL tren chuoi (vd log don thay 305 tu case truoc) khong duoc len report - chay rieng tu dau."""
    recs, goi = _run(monkeypatch, {
        ("a", "rieng"): "PASS",
        ("b", "chuoi"): {"verdict": "PASS", "chuoi_khong_chac": "log riêng: PASS · log dồn cả chuỗi: FAIL",
                         "runs": [{"overrides": {}, "verdict": "PASS"}]},
        ("b", "rieng"): "PASS",
        ("c", "chuoi"): "FAIL", ("c", "rieng"): "FAIL",
    })
    assert [(k, c) for k, c, _ in goi] == [("a", "rieng"), ("b", "chuoi"), ("b", "rieng"),
                                           ("c", "chuoi"), ("c", "rieng")]
    assert [r["verdict"] for r in recs] == ["PASS", "PASS", "FAIL"]
    assert [r["noi_chuoi"] for r in recs] == [False, False, False]


def test_khong_bat_chuoi_thi_moi_case_chay_rieng_va_tra_config(monkeypatch):
    recs, goi = _run(monkeypatch, {("a", "rieng"): "PASS", ("b", "rieng"): "PASS", ("c", "rieng"): "PASS"},
                     chuoi=False)
    assert goi == [("a", "rieng", False), ("b", "rieng", False), ("c", "rieng", False)]
    assert [r["noi_chuoi"] for r in recs] == [False] * 3


def _noi_tiep(monkeypatch, rieng: str, don: str) -> tuple[dict, list]:
    """Chay apply_case che do noi tiep, _cham_log gia: ket qua theo moc log dang doc."""
    doc = []

    async def cham(client, baseline, out, overrides, expects, precondition, steps, result_ok, log_fn=None):
        moc = log_moc.TU.get()
        doc.append(moc)
        return {**out, "verdict": rieng if moc else don}

    class Ok:
        ok, summary, mismatches = True, {"ok": True}, []

    async def verify(client, baseline, overrides):
        return Ok()

    class Base:
        serial, package, configs, firebase = "S", "com.ai.app", {}, {"project": "p"}
    monkeypatch.setattr(case_run, "_cham_log", cham)
    monkeypatch.setattr(case_run.rc_verify, "verify", verify)
    out = asyncio.run(case_run.apply_case(None, Base(), {"k": "v"}, False, ".", (), ("Native 301 hiển thị",), "",
                                          noi_tiep="1793694962.712", giu=True))
    return out, doc


def test_noi_tiep_cham_hai_lan_log_rieng_va_log_don(monkeypatch):
    out, doc = _noi_tiep(monkeypatch, "PASS", "PASS")
    assert doc == [None, "1793694962.712"]          # log don ca chuoi (khong moc) roi log rieng case (tu moc)
    assert out["verdict"] == "PASS" and not out.get("chuoi_khong_chac")
    assert out["giu_config"] and not out["restored"] and out["noi_tiep"]


def test_noi_tiep_log_don_khong_pass_thi_khong_chac(monkeypatch):
    """Vd 'khong load 305': log rieng case khong thay nhung 305 da load tu case truoc trong chuoi."""
    out, _ = _noi_tiep(monkeypatch, "PASS", "FAIL")
    assert out["chuoi_khong_chac"] == "log riêng case: PASS · log dồn cả chuỗi: FAIL"
    assert not chay_chuoi.nhan_duoc(out)


def _kq(verdict, don, dong):
    return {"verdict": verdict, "chuoi_don": don, "chuoi_khong_chac": "x",
            "runs": [{"verdict": verdict, "assert": {"lines": dong}}]}


def test_nhan_ket_qua_chuoi_khi_dong_con_mo_deu_suy_tu_cau_chu():
    """RG01-06 03/11: chay rieng them 63s ra dung NOT_VERIFIABLE do -> khong chay rieng nua."""
    tinh = [{"verdict": "PASS"}, {"verdict": "NOT_VERIFIABLE", "tinh": True}]
    assert chay_chuoi.nhan_duoc(_kq("NOT_VERIFIABLE", "NOT_VERIFIABLE", tinh))
    # log don ra khac log rieng -> co dong phu thuoc log -> chay rieng
    assert not chay_chuoi.nhan_duoc(_kq("NOT_VERIFIABLE", "FAIL", tinh))
    # dong con mo do log (khong phai cau chu) -> chay rieng
    assert not chay_chuoi.nhan_duoc(_kq("NOT_VERIFIABLE", "NOT_VERIFIABLE",
                                        [{"verdict": "NOT_VERIFIABLE", "tinh": False}]))
    # co dong FAIL -> luon chay rieng
    assert not chay_chuoi.nhan_duoc(_kq("FAIL", "FAIL", [{"verdict": "FAIL"}]))


def test_nhan_ket_qua_chuoi_khi_tool_dung_o_buoc_khong_lam_duoc():
    """RG01-02/03 03/11: buoc 'Chon ngon ngu.' tool chua lam duoc -> chay rieng ~65s ra y het NEEDS_HUMAN."""
    kq = _kq("NEEDS_HUMAN", "NEEDS_HUMAN", [{"verdict": "NEEDS_HUMAN", "tinh": False}])
    kq["runs"][0]["drive"] = {"status": "NEEDS_HUMAN"}
    assert chay_chuoi.nhan_duoc(kq)
    kq["runs"][0]["assert"]["lines"].append({"verdict": "FAIL"})   # co dong FAIL thi van chay rieng
    assert not chay_chuoi.nhan_duoc(kq)
