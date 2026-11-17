"""Phien claude -p het han muc 5 tieng: doc dung gio reset, job giu trong hang toi gio do roi chay tiep."""

from __future__ import annotations

import json
import os
import time
from datetime import datetime

from rcr import bot_chay_claude, bot_het_han_muc as hm
from rcr import bot_hang_doi as h

KQ_HET = {"is_error": True, "api_error": "usage_limit_reached", "api_error_status": 429,
          "result": "You've hit your 5-hour limit · resets 5:50pm (Asia/Bangkok)", "total_cost_usd": 15.4}


def _ts(gio, phut=0, ngay=17):
    return datetime(2026, 11, ngay, gio, phut).timestamp()


def test_doc_ket_qua_het_han_muc_khong_phai_loi():
    ra = bot_chay_claude.doc_ket_qua(json.dumps(KQ_HET))
    assert ra["trang_thai"] == hm.HET_HAN_MUC
    assert ra["cho_den"] > time.time() - 86400


def test_doc_ket_qua_loi_khac_van_la_loi():
    ra = bot_chay_claude.doc_ket_qua(json.dumps({"is_error": True, "result": "API Error: 500"}))
    assert ra["trang_thai"] == "LOI" and "cho_den" not in ra


def test_gio_reset_chieu_cung_ngay_va_qua_dem():
    assert hm.gio_reset("resets 5:50pm (Asia/Bangkok)", _ts(15, 56)) == _ts(17, 50) + hm.DU_SAU_RESET
    assert hm.gio_reset("resets 12:50pm", _ts(12, 49)) == _ts(12, 50) + hm.DU_SAU_RESET
    assert hm.gio_reset("resets 1am", _ts(23, 0)) == _ts(1, 0, 18) + hm.DU_SAU_RESET
    assert hm.gio_reset("resets Nov 18, 9am", _ts(10, 0)) == _ts(9, 0, 18) + hm.DU_SAU_RESET


def test_gio_reset_khong_doc_duoc_thi_cho_mac_dinh():
    assert hm.gio_reset("limit reached", _ts(10)) == _ts(10) + hm.CHO_MAC_DINH


def test_hang_doi_giu_job_toi_gio_reset(tmp_path):
    q = h.HangDoi(tmp_path / "q.json")
    q.them({"msg_id": 1, "package": "pkg.a", "version": "1.0 (1)", "loai_ban": "release"})
    j = q.lay()
    q.cap_nhat(j, kq={"trang_thai": hm.HET_HAN_MUC}, bat_dau=100.0)
    q.cho_lai(j, time.time() + 3600)
    q.xong(j)                                     # finally cua _chay_tren: khong duoc bo job dang cho
    assert len(q.jobs) == 1 and "kq" not in j and j["chay_tiep_tu"] == 100.0
    assert q.lay() is None and not q.co_cho()
    j["cho_den"] = time.time() - 1                # toi gio reset
    assert q.co_cho() and q.lay()["msg_id"] == 1
    q.cho_lai(j, time.time() + 3600)              # het lan nua: giu gio bat dau phien DAU
    assert j["chay_tiep_tu"] == 100.0
    assert q.huy(1) == "da_huy" and q.jobs == []  # QA van huy duoc job dang cho


def test_nhac_tab_da_xong(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    xong = out / "run-pkg.a-S1-rating.luot.json"
    xong.write_text(json.dumps({"xong": True, "records": [{"verdict": "PASS"}]}))
    do = out / "run-pkg.a-S1-widget.luot.json"
    do.write_text(json.dumps({"xong": False, "records": [{"verdict": "PASS"}]}))
    cu = out / "run-pkg.a-S1-checkin.luot.json"
    cu.write_text(json.dumps({"xong": True, "records": [{"verdict": "PASS"}]}))
    os.utime(cu, (50, 50))
    s = hm.nhac_tab_da_xong(tmp_path, "pkg.a", 100)
    assert str(xong) in s and str(do) not in s and str(cu) not in s
    assert hm.nhac_tab_da_xong(tmp_path, "pkg.a", None) == ""
