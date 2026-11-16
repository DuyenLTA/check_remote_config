"""Dung som khi app chua co cong thuc gen cua tab rating (`data/rating_gen.yaml`).

Case dau tien bao "app chưa có công thức gen <loai>" thi moi case sau can buoc "Gen anh / Gen video" cung loai
(va case "Tiep noi" cac case do) chac chan dung dung buoc do: chay chi ton ~2-3 phut/case ma ket qua y het
(AIP921 fitness 16/11/2026: 23 case rating chay 34 phut, 18 case NEEDS_HUMAN vi cung mot ly do). Bo qua cac case
do, ghi NEEDS_HUMAN kem ly do de Claude khai cong thuc (hoac do tay) roi chay lai dung cac case nay.
"""

from __future__ import annotations

import json
import re

from . import act_rating, fo_ngon_ngu

THIEU_RE = re.compile(r"app chưa có công thức gen (anh|ảnh|video)", re.I)


def _loai(chu: str) -> str:
    return "video" if chu.lower() == "video" else "anh"


def loai_thieu(result: dict | None) -> set[str]:
    """Loai gen (anh / video) ma ket qua case bao chua co cong thuc."""
    if not result:
        return set()
    return {_loai(m.group(1)) for m in THIEU_RE.finditer(json.dumps(result, ensure_ascii=False))}


def loai_can(actions) -> set[str]:
    """Loai gen ma cac buoc Action cua case can."""
    ra = set()
    for buoc in actions or ():
        m = act_rating.GEN_RE.match(str(buoc))
        if m:
            ra.add(_loai(m.group(1)))
    return ra


def ly_do_bo(chosen: dict, thieu: set[str], bo_truoc: set[str]) -> str:
    """'' neu case van chay; khong thi ly do bo qua (case can gen loai chua co cong thuc, hoac noi tiep case da bo)."""
    can = loai_can(chosen.get("actions")) & thieu
    if can:
        return (f"app chưa có công thức gen {', '.join(sorted(can))} trong data/rating_gen.yaml (case trước đã báo) — "
                "không chạy; khai công thức rồi chạy lại / đo tay")
    m = fo_ngon_ngu.TIEP_NOI_RE.search(chosen.get("precondition") or "")
    if m and any(k.endswith(m.group(1)) for k in bo_truoc):
        return f"tiếp nối {m.group(1)} — case đó đã bỏ qua vì app chưa có công thức gen"
    return ""


def record_bo_qua(key: str, row: dict, chosen: dict, ly_do: str) -> dict:
    """Case khong chay: moi dong Expected NEEDS_HUMAN kem ly do (cho do tay / chay lai sau khi khai cong thuc)."""
    from . import report_data
    run = {"assert": {"lines": [{"verdict": "NEEDS_HUMAN", "expected": " ".join((e or "").split()), "reason": ly_do}
                                for e in chosen.get("expects") or ()],
                      "pending": len(chosen.get("expects") or ()), "po": 0},
           "drive": {"status": "NEEDS_HUMAN", "steps": []}}
    rec = report_data.case_record(key, row, {"verdict": "NEEDS_HUMAN", "runs": [run]})
    return rec | {"actual": f"không chạy — {ly_do}"}
