"""Dong Expected "... giu nguyen" sau khi an app / keo notification (AIP936 3.6.1, nhom RG01 / RG08):

- "Item da chon giu nguyen"  (man Question, sau Home -> mo lai)
    So item co dau tick (ivQuestionTick) o dump TRUOC buoc dau tien voi dump man cuoi (sau khi dong ad resume).
    Truoc do chua chon item nao (chay le, khong noi tu case chon) -> khong co gi de so -> None (de nguoi xem).
- "Native <vi tri> giu nguyen, khong reload" (+ "Van o OB3")
    Log ad cua case: moi unit cua vi tri request toi da 1 lan va show toi da 1 lan -> trong ca case khong co lan
    load lai nao -> PASS. Co unit request >= 2: log khong co moc thoi gian theo buoc nen KHONG biet lan request
    them nam truoc hay sau thao tac -> None (de nguoi xem), khong ket luan FAIL bua.

Nguyen tac: chi tra PASS/FAIL khi bang chung du chac; mo ho thi tra None.
"""

from __future__ import annotations

import re

from . import ad_positions, assert_ui, ui_dump
from .verdict_levels import CONFIG_BLOCKED, FAIL, PASS, out, worst

ITEM_GIU_RE = re.compile(r"item\s+(?:đã|da)\s+chọn\s+giữ\s+nguyên", re.I)
KHONG_RELOAD_RE = re.compile(r"giữ\s+nguyên\s*,?\s*(?:và\s+)?không\s+reload", re.I)
VI_TRI_RE = re.compile(r"\b(\d{3})[-_][a-z]", re.I)
VAN_O_RE = re.compile(r"vẫn\s+ở\s+([^,;.]+)", re.I)
TICK_ID, TITLE_ID = "ivQuestionTick", "tvQuestionTitle"


def _item_chon(xml: str) -> list[str]:
    """Ten item dang co dau tick: tieu de nam ngay duoi tick, cung cot."""
    nodes = ui_dump.parse_dump(xml or "")
    titles = [n for n in nodes if n.resource_id == TITLE_ID and not n.bounds.empty]
    chon = []
    for t in (n for n in nodes if n.resource_id == TICK_ID and n.visible and not n.bounds.empty):
        cx = (t.bounds.left + t.bounds.right) // 2
        duoi = [x for x in titles if x.bounds.left <= cx <= x.bounds.right and x.bounds.top >= t.bounds.bottom]
        if duoi:
            chon.append(min(duoi, key=lambda x: x.bounds.top).text or "?")
    return sorted(chon)


def _cham_item(text: str, drive: dict) -> dict | None:
    truoc = next((s for s in drive.get("steps") or []
                  if "QuestionActivity" in (s.get("activity") or "") and s.get("dump")), None)
    cuoi = drive.get("final_sau_dong") or drive.get("final") or {}
    if not truoc or "QuestionActivity" not in (cuoi.get("activity") or "") or not cuoi.get("dump"):
        return None
    try:
        a, b = _item_chon(truoc["dump"]), _item_chon(cuoi["dump"])
    except Exception:
        return None                          # dump hong -> khong doc duoc, de nguoi xem
    if not a:
        return None                          # truoc thao tac chua chon gi -> khong co gi de "giu nguyen"
    if a == b:
        return out(PASS, f"item đã chọn trước khi ẩn app: {', '.join(a)} — sau khi mở lại vẫn được chọn", ", ".join(b))
    return out(FAIL, f"trước khi ẩn app chọn {', '.join(a)}, sau khi mở lại: "
                     f"{', '.join(b) if b else 'không còn item nào được chọn'}", ", ".join(b))


def _cham_khong_reload(text: str, units: list[dict], drive: dict) -> dict | None:
    m = VI_TRI_RE.search(text)
    if not m:
        return None
    vt = m.group(1)
    u = [x for x in units if ad_positions._khop_vi_tri(x, vt)]
    req = sum(x.get("requested", 0) for x in u)
    show = sum(x.get("shown", 0) for x in u)
    if req and not show and not any(x.get("loaded") for x in u):
        # Kho khong fill: khong co ad nao de kiem "giu nguyen" -> thieu dieu kien (BLOCKED), khong doan PASS/FAIL.
        return out(CONFIG_BLOCKED, f"native {vt} request {req} lần nhưng kho không fill lần nào — không có ad hiện "
                   "để kiểm 'giữ nguyên, không reload'", f"{vt}: request {req}, load 0")
    if not show:
        # 0 request: khong thay duoc ad da hien that hay chua -> khong ket luan.
        return None
    if any(x.get("requested", 0) >= 2 or x.get("shown", 0) >= 2 for x in u):
        return None                          # khong biet lan request them truoc hay sau thao tac
    ly_do = f"native {vt}: {len(u)} unit, mỗi unit request tối đa 1 lần, show {show} lần trong cả case — không có lần load lại"
    ket = out(PASS, ly_do, f"{vt}: request {req}, show {show}")
    van_o = VAN_O_RE.search(text)
    if van_o:
        d = dict(drive or {})
        if d.get("final_sau_dong"):
            d["final"] = d["final_sau_dong"]
        man = assert_ui._man_da_toi(van_o.group(1), d)
        if man is None:
            return None
        return out(worst([man["verdict"], ket["verdict"]]), f"{man['reason']}; {ly_do}", text)
    return ket


def cham(text: str, units: list[dict], drive: dict) -> dict | None:
    t = text or ""
    if ITEM_GIU_RE.search(t):
        return _cham_item(t, drive or {})
    if KHONG_RELOAD_RE.search(t):
        return _cham_khong_reload(t, units, drive or {})
    return None
