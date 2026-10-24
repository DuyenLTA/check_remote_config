"""Case chua ra PASS/FAIL thi co dang chay lai khong.

run_batch chay lai toi da `LAN_CHAY_LAI` lan khi verdict lo lung: doc file trung
luc SDK ghi, ad chua fill, tool nhin tre - lan sau co the ra ket qua. Nhung dong
"phai nhin mat", "khong neu ro ky vong" suy tu CAU CHU, chay lai van y het: mot
luot 22 case Piclux 2.4.0 (24/10/2026) ton gap ~3 lan thoi gian vi cac dong nay.
"""

from __future__ import annotations

from .verdict_levels import FAIL, PASS


def _dong(result: dict) -> list[dict]:
    """Moi dong Expected cua moi luot gia tri, tru dong cua PO (khong tinh verdict)."""
    return [l for r in result.get("runs") or []
            for l in (r.get("assert") or {}).get("lines") or []
            if l.get("scope") != "po"]


def dau_van(result: dict) -> tuple:
    """Dau van cua mot lan chay: verdict + ly do tung dong. Hai lan giong nhau = tat dinh."""
    return tuple((l.get("n"), l["verdict"], l["reason"]) for l in _dong(result))


def ly_do_khong_chay_lai(result: dict, dau_truoc: tuple | None) -> str:
    """Ly do KHONG chay lai, "" neu nen chay lai.

    Chi xet case ra NEEDS_HUMAN / NOT_VERIFIABLE: BLOCKED (config bi fetch de, ad
    LFO2 show som) la dieu kien cua lan chay, lan sau co the khac.
    """
    if result.get("verdict") not in ("NEEDS_HUMAN", "NOT_VERIFIABLE"):
        return ""
    if any((r.get("verdict") == "BLOCKED") for r in result.get("runs") or []):
        return ""
    con_mo = [l for l in _dong(result) if l["verdict"] not in (PASS, FAIL)]
    if con_mo and all(l.get("tinh") for l in con_mo):
        return f"{len(con_mo)} dòng chưa chấm đều suy từ câu chữ (phải nhìn mắt / không nêu kỳ vọng)"
    if dau_truoc is not None and dau_van(result) == dau_truoc:
        return "lần này ra y hệt lần trước ở mọi dòng"
    return ""
