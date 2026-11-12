"""Cham dong Expected noi ve event Firebase (doc tu log FA-SVC da thu trong lan chay).

Tach khoi `assert_ui` cho file duoi 200 dong. Ba kieu cau that cua bo TC tinh nang (rating/widget/checkin):
  - "Event widget_view fire 1 lan."                       -> event phai co.
  - "Khong co event widget_view."                         -> event phai VANG mat (truoc day cham nguoc: FAIL
                                                             vi 'khong thay event' - AIP893 widget R04-01).
  - "Result hien popup; event placement_name = 'result'"  -> chi neu PARAM, khong neu ten event: khong doan.
"""

from __future__ import annotations

import re

from .verdict_levels import FAIL, NEEDS_HUMAN, PASS, out

# Ten event: chu thuong + gach duoi, it nhat mot gach -> khong an nham tu thuong.
TEN_EVENT_RE = re.compile(r"\b([a-z][a-z0-9]*(?:_[a-z0-9]+)+)\b")
# Token dung ngay sau chu "event" - uu tien hon token dau cau ("Home, result, exit_click: ...
# khong co event rating_placement_viewed" - truoc day lay nham `exit_click` lam ten event).
SAU_EVENT_RE = re.compile(r"\bevent\s+([a-z][a-z0-9]*(?:_[a-z0-9]+)+)\b(?!\s*[=:])", re.I)
# Token ngay sau "event" ma theo sau la `=`: do la param ("event placement_name = 'result'").
PARAM_SAU_EVENT_RE = re.compile(r"\bevent\s+[a-z][a-z0-9_]*\s*=", re.I)
# "Khong co event X" / "khong ban/fire event X" / "X khong fire".
KHONG_EVENT_RE = re.compile(
    r"kh[oô]ng\s+(?:c[oó]|b[aắ]n|fire|log)\s+(?:event\s+)?([a-z][a-z0-9]*(?:_[a-z0-9]+)+)", re.I)


def _ten_event(text: str) -> tuple[str, list[str]] | None:
    sau = SAU_EVENT_RE.findall(text)
    if sau:
        ten = sau[0]
        con_lai = [t for t in TEN_EVENT_RE.findall(text) if t != ten and text.find(t) > text.find(ten)]
        return ten, con_lai
    if PARAM_SAU_EVENT_RE.search(text):
        return None  # chi co param, khong biet event nao
    ten = TEN_EVENT_RE.findall(text)
    return (ten[0], ten[1:]) if ten else None


def _vang_mat(text: str, ten: str, events) -> dict:
    khop = [e for e in events if e["name"] == ten]
    if khop:
        return out(FAIL, f"kỳ vọng không có event `{ten}` nhưng log có {len(khop)} lần", ten)
    # Cau con ve khac ("popup khong hien, khong co event X"): event dung, ve con lai chua ai do.
    bo = KHONG_EVENT_RE.sub("", text)
    bo = re.sub(r"[\s.,;:]+", " ", bo).strip()
    if len(bo.split()) > 2:
        return out(NEEDS_HUMAN, f"không có event `{ten}` trong log (đúng); vế còn lại của câu chưa đo", ten)
    return out(PASS, f"không có event `{ten}` trong log ({len(events)} event FA khác đã đọc được)", ten)


def event_da_ban(text: str, events) -> dict | None:
    """`None` khi cau khong neu ten event nao: de nhanh sau xu ly."""
    events = list(events or ())
    phu_dinh = KHONG_EVENT_RE.search(text)
    if phu_dinh:
        if not events:
            return out(NEEDS_HUMAN, "cả lượt chạy không có dòng log FA-SVC nào — chưa đối chiếu được event",
                       phu_dinh.group(1))
        return _vang_mat(text, phu_dinh.group(1), events)
    tim = _ten_event(text)
    if not tim:
        if PARAM_SAU_EVENT_RE.search(text):
            return out(NEEDS_HUMAN, "câu chỉ nêu param của event, không nêu tên event — đo tay", text)
        return None
    muon, con_lai = tim
    khop = [e for e in events if e["name"] == muon]
    if not khop:
        ban_ra = sorted({e["name"] for e in events})
        if not ban_ra:
            return out(NEEDS_HUMAN,
                       "cả lượt chạy không có dòng log FA-SVC nào — bản build này có thể "
                       "không bật Analytics, chưa đối chiếu được event", muon)
        return out(FAIL, f"không thấy event `{muon}` trong log; đã bắn: {', '.join(ban_ra)}", muon)
    # Cau con neu ten param ("co engagement_time") -> doi param do phai co mat.
    thieu = [p for p in con_lai if not any(p in e["params"] for e in khop)]
    if thieu:
        co = sorted({k for e in khop for k in e["params"]})
        return out(FAIL, f"event `{muon}` có bắn nhưng thiếu param {', '.join(thieu)} "
                         f"— param thấy được: {', '.join(co)}", muon)
    gia_tri = {k: v for e in khop for k, v in e["params"].items() if k in con_lai}
    return out(PASS, f"event `{muon}` bắn {len(khop)} lần"
                     + (f", {gia_tri}" if gia_tri else ""), muon)
