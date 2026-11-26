"""QA bao test pass -> bot ghi plan tuan (Trang thai = Released, Release thuc te = ngay pass):
code tim o, `claude -p` voi ket noi Google Sheets chi ghi 2 o do."""

from __future__ import annotations

import asyncio
import datetime as dt
import json
import subprocess
from types import SimpleNamespace
from unittest.mock import AsyncMock

import openpyxl
import pytest

from rcr import bot_testvsl as b
from rcr import plan_tuan_ghi as g
from rcr.models import RcError

NGAY = dt.date(2026, 11, 26)
HD = ["STT", "Loại dự án", "OS", "Tên dự án", "App version ", "Detail ", "Ưu tiên", "PIC", "Trạng thái", "Dev done",
      "Lịch Release", "Release thực tế", "Vấn đề phát sinh"]


@pytest.fixture
def plan(tmp_path):
    """Giong tab that 23/11-27/11/2026 (ban export ten '2311-27112026'): dong 1 'Plan', dong 2 tieu de."""
    wb = openpyxl.Workbook()
    wb.active.title = "draf"
    cu = wb.create_sheet("1611-20112026")
    cu.append(["Plan"]); cu.append(HD); cu.append([1, "", "Android", "AIP919", "2.0.0", "", "", "Duyên", "Released"])
    ws = wb.create_sheet("2311-27112026")
    ws.append(["Plan "])
    ws.append(HD)
    ws.append([1, "VSL - IOS", "iOS", "[IIP032] Artimind", "v7.9.6", "", 1, "Rong", "Released"])
    ws.append([4, "VSL - Inhouse", "Android", "ADA895", "3.2.0", "SDK 3.7.3", 8, "Duyên", "Fixing"])
    ws.append([5, "VSL - Inhouse", "Android", "AIP919", "2.1.0", "- Apply IAA", None, "Duyên", "Fixing"])
    ws.append([6, "VSL - Inhouse", "Android", "AIP933", "2.3.0", "", None, "Duyên", "Fixing"])
    ws.append([7, "VSL - Inhouse", "Android", "AIP933", "2.4.0", "", None, "Duyên", "Testing"])
    p = tmp_path / "plan.xlsx"
    wb.save(p)
    return p


def test_tim_dung_o_cua_app_trong_tab_tuan(plan):
    vt = g.tim_dong(plan, "AIP919", "2.1.0", NGAY)
    assert vt == {"tab": "2311-27112026", "dong": 5, "o_ten": "D5", "o_tt": "I5", "o_rel": "L5", "truoc": "Fixing"}
    assert g.tim_dong(plan, "AIP919", "", dt.date(2026, 11, 29))["dong"] == 5      # CN van tab tuan nay


def test_hai_dong_cung_ma_thi_phan_biet_bang_version(plan):
    assert g.tim_dong(plan, "AIP933", "2.4.0", NGAY)["dong"] == 7
    with pytest.raises(RcError, match="2 dòng khớp AIP933"):
        g.tim_dong(plan, "AIP933", "", NGAY)
    with pytest.raises(RcError, match="không thấy dòng AIP919 2.2.0"):
        g.tim_dong(plan, "AIP919", "2.2.0", NGAY)


def test_version_trong_tin_pass():
    assert g.version_trong("test pass v1.4.0(14) rls") == "1.4.0"
    assert g.version_trong("AIP919 2.1.0 pass") == "2.1.0"
    assert g.version_trong("test pass") == ""


def _gia(monkeypatch, plan, ket_qua: str, gui: list):
    monkeypatch.setenv("RC_PLAN_TUAN_SHEET", "https://docs.google.com/spreadsheets/d/1hqxJI3A1AMXTEUnZPgEsSOjc8uilLBLrHHzYWgbV-_U/edit")
    monkeypatch.setattr(g.plan_tuan, "tai", lambda _l, _o: str(plan))

    def chay(cmd, input, **kw):
        gui.append((cmd, input))
        return subprocess.CompletedProcess(cmd, 0, stdout=json.dumps({"result": "đã ghi\n" + ket_qua}), stderr="")
    return chay


def test_claude_chi_duoc_tool_sheets_va_ghi_dung_2_o(monkeypatch, plan, tmp_path):
    gui = []
    chay = _gia(monkeypatch, plan, 'KET_QUA: {"ok": true, "tab": "23/11-27/11/2026"}', gui)
    kq = g.ghi_test_pass("AIP919", "2.1.0", NGAY, tmp_path, chay=chay)
    assert kq == {"tab": "23/11-27/11/2026", "dong": 5, "truoc": "Fixing"}
    cmd, prompt = gui[0]
    tools = cmd[cmd.index("--allowedTools") + 1:]
    assert tools and all(t.startswith("mcp__claude_ai_Google_Sheets__") for t in tools)
    assert not any("Bash" in t or "Edit" in t for t in tools)
    assert "'2311-27112026'" in prompt and "!I5" in prompt and "!L5" in prompt and "!D5" in prompt
    assert '[["Released"]]' in prompt and '[["26/11/2026"]]' in prompt
    assert "1hqxJI3A1AMXTEUnZPgEsSOjc8uilLBLrHHzYWgbV-_U" in prompt
    cau = g.cau_bao("AIP919", "2.1.0", NGAY, kq)
    assert "Released" in cau and "26/11/2026" in cau and "Fixing" in cau and "23/11-27/11/2026" in cau


def test_claude_bao_loi_thi_raise(monkeypatch, plan, tmp_path):
    chay = _gia(monkeypatch, plan, 'KET_QUA: {"ok": false, "loi": "o D5 khong chua AIP919"}', [])
    with pytest.raises(RcError, match="o D5 khong chua AIP919"):
        g.ghi_test_pass("AIP919", "2.1.0", NGAY, tmp_path, chay=chay)


def test_tat_hoac_chua_co_plan_thi_khong_goi(monkeypatch):
    monkeypatch.setenv("RC_PLAN_TUAN_SHEET", "https://docs.google.com/spreadsheets/d/x/edit")
    monkeypatch.setenv(g.ENV_TAT, "0")
    assert not g.bat()
    assert asyncio.run(b._ghi_plan("AIP919", "test pass v2.1.0")) == ""


def _pass(monkeypatch, tt, plan_dong):
    gui = []

    async def gui_kenh(_bot, text):
        gui.append(text)
        return SimpleNamespace(id=1, edit=AsyncMock())

    async def ghi_plan(_ma, _chu, _out=None):
        return plan_dong

    monkeypatch.setattr(b, "_gui_kenh_condition", gui_kenh)
    monkeypatch.setattr(b, "_ghi_plan", ghi_plan)
    monkeypatch.setattr(b.bot_cong_viec, "package_cua", lambda _m, _o: "com.x")
    monkeypatch.setattr(b.tv, "tim_app", lambda _p: {"project": "proj", "app_id": "1:1"})
    monkeypatch.setattr(b.tv, "trang_thai", lambda _p: tt)
    monkeypatch.setattr(b.tv, "xoa", lambda _p: "Đã xoá `testvsl`.")
    q = SimpleNamespace(jobs=[], bao_lan_dau=lambda _k: True, nho_tin=lambda _c: None, _dang_test=lambda _j: False)
    m = SimpleNamespace(id=5, content="AIP919 2.1.0 (14) test pass", jump_url="https://discord/x")
    assert asyncio.run(b.nhan_tin_pass(SimpleNamespace(kenh_forum=0, q=q), m, "AIP919", b.OUT))
    return gui


def test_pass_co_testvsl_thi_mot_tin_gom_ca_plan(monkeypatch):
    tt = {"co": True, "bieu_thuc": "v", "so_key": 0, "nguoi_tao": "bot@x", "cua_toi": True}
    gui = _pass(monkeypatch, tt, "📋 Plan tuần … Released")
    assert len(gui) == 1 and "đã tự xoá" in gui[0] and "Plan tuần" in gui[0]


def test_pass_khong_con_testvsl_van_bao_plan(monkeypatch):
    gui = _pass(monkeypatch, {"co": False}, "📋 Plan tuần … Released")
    assert len(gui) == 1 and "Plan tuần" in gui[0] and "test pass" in gui[0]


def test_pass_khong_testvsl_plan_tat_thi_im(monkeypatch):
    assert _pass(monkeypatch, {"co": False}, "") == []
