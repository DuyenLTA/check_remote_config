"""Luot bot LOI / HET_GIO khong co KET_QUA -> bug lay tu file luot (AIP918 2.5.0 12/11/2026 mat menu bug)."""

import json
import os
import time

from rcr import bot_bug_tu_file_luot as b

PKG = "com.nxl.aienglishtutor"


def _luot(out, ten, records, report="", mtime=None):
    f = out / ten
    f.write_text(json.dumps({"package": PKG, "report": report, "records": records}), encoding="utf-8")
    if mtime:
        os.utime(f, (mtime, mtime))
    return f


def _rec(key, verdict, lines):
    return {"key": key, "label": f"#{key} nhãn", "verdict": verdict, "precondition": "Clear data.",
            "steps": [{"s": "lái luồng", "k": "chup_man"}, {"s": "Bấm Next", "k": "tap"}],
            "lines": [{"e": e, "v": v, "r": r} for e, v, r in lines]}


def test_loi_khong_bug_lay_case_FAIL_moi_nhat(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    bat_dau = time.time() - 100
    _luot(out, f"run-{PKG}-S-1.luot.json", [_rec("3.6.1#RG01-03", "FAIL", [("Load 202 high1", "FAIL", "không request")]),
                                            _rec("3.6.1#RG01-04", "FAIL", [("x", "FAIL", "y")])])
    rp = out / "r.html"
    rp.write_text("<html></html>", encoding="utf-8")
    # lan chay lai sau: RG01-04 da PASS -> khong con la bug
    _luot(out, f"luot-{PKG}-2.luot.json", [_rec("3.6.1#RG01-04", "PASS", [("x", "PASS", "ok")])], report=str(rp),
          mtime=time.time() + 5)
    _luot(out, f"run-{PKG}-cu.luot.json", [_rec("3.6.1#CU", "FAIL", [("a", "FAIL", "b")])], mtime=bat_dau - 3600)
    kq = b.cuu_ket_qua({"trang_thai": "LOI", "link": "", "tom_tat": "", "bugs": []}, out, PKG, bat_dau)
    assert [x["case"] for x in kq["bugs"]] == ["3.6.1#RG01-03"]
    bug = kq["bugs"][0]
    assert "Load 202 high1" in bug["tieu_de"] and bug["buoc"] == "1. Bấm Next"
    assert "chưa ai xem lại" in bug["thuc_te"] and kq["link"] == str(rp.resolve())


def test_xong_hoac_da_co_bug_thi_giu_nguyen(tmp_path):
    for kq in ({"trang_thai": "XONG", "bugs": []}, {"trang_thai": "LOI", "bugs": [{"case": "a"}]}):
        assert b.cuu_ket_qua(kq, tmp_path, PKG, time.time() - 10) is kq


def test_cli_tha_vao_hop_thu(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    _luot(out, f"run-{PKG}-S-1.luot.json", [_rec("3.6.1#RG01-03", "FAIL", [("Load 202", "FAIL", "không")])])
    from datetime import datetime
    tu = datetime.fromtimestamp(time.time() - 60).strftime("%Y-%m-%d %H:%M")
    assert b.main(["--package", PKG, "--tu", tu, "--version", "2.5.0 (23)", "--tha", "--out", str(out)]) == 0
    f = next((out / "bot-hop-thu-bug").glob("bug-*.json"))
    d = json.loads(f.read_text(encoding="utf-8"))
    assert d["package"] == PKG and d["version"] == "2.5.0 (23)" and d["bugs"][0]["case"] == "3.6.1#RG01-03"
