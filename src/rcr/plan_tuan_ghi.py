"""Ghi trang thai plan tuan khi QA bao test pass: cot "Trạng thái" = Released, "Release thực tế" = ngay bao pass.

User chot 26/11/2026: QA bao test pass thi bot cap nhat luon status cua sheet plan tuan va ghi ngay release thuc te
(truoc do la dau viec QA con lam tay duy nhat). User chon ghi qua ket noi Google Sheets cua Claude (khong Apps Script).

Chia doi de Claude khong phai doan:
  1. Code tai plan (link export, nhu `plan_tuan`), tim tab tuan chua ngay bao pass, dong cua app (ma + version) va
     cot "Trạng thái" / "Release thực tế" -> vi tri o cu the (I7, L7...). Khong thay / nhieu dong khop -> RcError.
  2. `claude -p` chi duoc 3 tool Google Sheets (lay ten tab, doc 1 dong, ghi): doi chieu dong do dung ma app roi ghi
     DUNG 2 o. Ten tab tren Google co dau "/" (23/11-27/11/2026), ban export bo "/" (2311-27112026) -> Claude chon
     tab co ten bo "/" va khoang trang trung ten export.
Can: may bot dang nhap Claude co ket noi Google Sheets, tai khoan do co quyen sua sheet plan. Tat bang
RC_PLAN_TUAN_GHI=0. Loi gi cung chi tra RcError -> bot bao "nho QA cap nhat tay", khong lam hong luong test pass.
"""

from __future__ import annotations

import datetime as dt
import json
import re
import shutil
import subprocess
from pathlib import Path

from . import build_ma_app, plan_tuan, tc_source
from .cau_hinh_bot import env
from .models import RcError

ENV_TAT = "RC_PLAN_TUAN_GHI"
G = "mcp__claude_ai_Google_Sheets__"
TOOLS = [G + "get_spreadsheet", G + "get_values", G + "update_values"]
MAX_TURNS = "10"
TIMEOUT = 4 * 60
GIA_TRI = "Released"
# "test pass v1.4.0(14) rls", "pass 2.1.0", "v3.2.0 (24) pass" -> 1.4.0 / 2.1.0 / 3.2.0
VER_RE = re.compile(r"(?<![\d.])v?\s?(\d+\.\d+\.\d+)(?![\d.])", re.I)
KET_QUA_RE = re.compile(r"KET_QUA:\s*(\{.*\})")


def version_trong(chu: str) -> str:
    m = VER_RE.search(chu or "")
    return m.group(1) if m else ""


def bat() -> bool:
    return bool(env(plan_tuan.ENV)) and env(ENV_TAT) != "0"


def _tab_tuan(wb, ngay: dt.date):
    """Tab "ddmm-ddmmyyyy" chua ngay (tinh ca thu 7, CN); khong co thi tab moi nhat da bat dau."""
    chua, moi = None, None
    for ws in wb.worksheets:
        t = plan_tuan.tuan_cua_tab(ws.title)
        if not t:
            continue
        if t[0] <= ngay <= t[1] + dt.timedelta(days=2):
            chua = ws
        if t[0] <= ngay and (moi is None or t[0] > plan_tuan.tuan_cua_tab(moi.title)[0]):
            moi = ws
    return chua or moi


def tim_dong(path, ma: str, version: str, ngay: dt.date) -> dict:
    """-> {tab, dong, o_ten, o_tt, o_rel, truoc} (o dang A1). Khong thay dong / nhieu dong khop -> RcError."""
    import openpyxl
    from openpyxl.utils import get_column_letter as cot

    wb = openpyxl.load_workbook(path, data_only=True)
    try:
        ws = _tab_tuan(wb, ngay)
        if ws is None:
            raise RcError("plan chưa có tab của tuần này")
        hd, khop = None, []
        for hang in ws.iter_rows():
            gt = [str(c.value).strip() if c.value is not None else "" for c in hang]
            chuan = [" ".join(g.split()).casefold() for g in gt]
            if "trạng thái" in chuan and "tên dự án" in chuan:
                hd = {k: chuan.index(k) for k in ("tên dự án", "trạng thái", "release thực tế", "app version") if k in chuan}
                continue
            if not hd or "release thực tế" not in hd:
                continue
            ten = gt[hd["tên dự án"]] if hd["tên dự án"] < len(gt) else ""
            if not any(m.group(1).upper() == ma.upper() for m in build_ma_app.MA_RE.finditer(ten)):
                continue
            ver_dong = re.findall(r"\d+\.\d+\.\d+", gt[hd["app version"]]) if "app version" in hd else []
            if version and ver_dong and version not in ver_dong:
                continue
            khop.append((hang[0].row, gt))
        if hd is None:
            raise RcError(f"tab {ws.title.strip()} không có dòng tiêu đề «Tên dự án / Trạng thái»")
        if len(khop) != 1:
            ai = f"{ma} {version}".strip()
            raise RcError(f"tab {ws.title.strip()}: " + (f"{len(khop)} dòng khớp {ai}" if khop else f"không thấy dòng {ai}"))
        dong, gt = khop[0]
        return {"tab": ws.title.strip(), "dong": dong, "o_ten": f"{cot(hd['tên dự án'] + 1)}{dong}",
                "o_tt": f"{cot(hd['trạng thái'] + 1)}{dong}", "o_rel": f"{cot(hd['release thực tế'] + 1)}{dong}",
                "truoc": gt[hd["trạng thái"]]}
    finally:
        wb.close()


PROMPT = (
    "Luot nay do bot QA goi, KHONG co nguoi. Chi duoc ghi DUNG 2 o cua Google Sheet plan tuan, khong lam gi khac.\n"
    "spreadsheetId: {sid}\n"
    "1. Goi get_spreadsheet voi fields [\"sheets.properties.title\"]. Chon DUNG MOT tab ma ten, sau khi bo het dau '/' va "
    "khoang trang, bang chinh xac '{tab}'. Khong co, hoac nhieu hon mot -> dung, khong ghi.\n"
    "2. Goi get_values range '<ten tab>'!{o_ten}. O nay phai chua ma app '{ma}'. Khong chua -> dung, khong ghi.\n"
    "3. Goi update_values range '<ten tab>'!{o_tt} values [[\"{gia_tri}\"]].\n"
    "4. Goi update_values range '<ten tab>'!{o_rel} values [[\"{ngay}\"]].\n"
    "Khong doc / ghi o nao khac, khong doi dinh dang. Dong cuoi cung cua cau tra loi la DUNG MOT dong:\n"
    "KET_QUA: {{\"ok\": true, \"tab\": \"<ten tab>\"}}  hoac  KET_QUA: {{\"ok\": false, \"loi\": \"<ly do ngan>\"}}"
)


def lenh() -> list[str]:
    exe = shutil.which("claude") or "claude"
    return [exe, "-p", "--output-format", "json", "--max-turns", MAX_TURNS, "--allowedTools", *TOOLS]


def ghi_test_pass(ma: str, version: str, ngay: dt.date, out_dir: Path, chay=subprocess.run) -> dict:
    """Tim vi tri bang code roi cho Claude ghi 2 o. Tra {tab, dong, truoc}; loi -> RcError."""
    from . import bot_chay_claude, bot_hoi_dap

    link = env(plan_tuan.ENV)
    m = tc_source.SHEET_RE.search(link or "")
    if not m:
        raise RcError(f"chưa cấu hình {plan_tuan.ENV}")
    vt = tim_dong(plan_tuan.tai(link, out_dir), ma, version, ngay)
    prompt = PROMPT.format(sid=m.group(1), tab=vt["tab"], o_ten=vt["o_ten"], o_tt=vt["o_tt"], o_rel=vt["o_rel"],
                           ma=ma.upper(), gia_tri=GIA_TRI, ngay=f"{ngay:%d/%m/%Y}")
    try:
        p = chay(lenh(), input=prompt, capture_output=True, text=True, encoding="utf-8", errors="replace",
                 timeout=TIMEOUT, env=bot_chay_claude.moi_truong())
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RcError(f"không chạy được Claude để ghi plan tuần: {exc}") from None
    tra_loi = bot_hoi_dap.doc_tra_loi(p.stdout or "")
    kq = KET_QUA_RE.findall(tra_loi)
    try:
        d = json.loads(kq[-1]) if kq else {}
    except ValueError:
        d = {}
    if not d.get("ok"):
        raise RcError(f"plan tuần không cập nhật (tab {vt['tab']} ô {vt['o_tt']}): "
                      + (d.get("loi") or (tra_loi[-200:] if tra_loi else f"Claude thoát mã {p.returncode}")))
    return {"tab": d.get("tab") or vt["tab"], "dong": vt["dong"], "truoc": vt["truoc"]}


def cau_bao(ma: str, version: str, ngay: dt.date, kq: dict) -> str:
    truoc = f" (trước: {kq['truoc']})" if kq.get("truoc") else ""
    return (f"📋 Plan tuần `{kq.get('tab', '?')}` dòng {kq.get('dong', '?')}: **{ma}** `{version or '?'}` → "
            f"Trạng thái **{GIA_TRI}**, Release thực tế **{ngay:%d/%m/%Y}**{truoc}.")
