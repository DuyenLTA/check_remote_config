"""Case chua ra PASS/FAIL thi co dang chay lai khong.

run_batch chay lai toi da `LAN_CHAY_LAI` lan khi verdict lo lung: doc file trung
luc SDK ghi, ad chua fill, tool nhin tre - lan sau co the ra ket qua. Nhung dong
"phai nhin mat", "khong neu ro ky vong" suy tu CAU CHU, chay lai van y het: mot
luot 22 case Piclux 2.4.0 (24/10/2026) ton gap ~3 lan thoi gian vi cac dong nay.
"""

from __future__ import annotations

import re

from .verdict_levels import FAIL, PASS

# Ly do chac chan lap lai neu chay lai (dieu kien cua app / may, khong phai tool nhin tre): lan 1 da biet -> khong chay
# lai. Truoc day lan 2 LUON chay vi chi so voi lan truoc (lan dau chua co gi de so) - AIP892/AIP893 16/11/2026 ton
# ~10-40 phut/luot cho cac case "khong co shortcut", "chua co cong thuc", "man Result khong dump duoc", "can Android < 8".
TAT_DINH_RE = re.compile(
    r"app không có shortcut|chưa có công thức|could not get idle state|không chụp được màn Result"
    r"|cần máy (?:Android|API)|kho không fill|không fill"
    # Do 13-17/11/2026 tren luot.json 4 ngay (lich_su_dong): cac ly do duoi chay lai 60+ lan, ~6 gio, CHUA lan nao doi
    # sang PASS/FAIL. "khong thay popup/man Rating" KHONG o day: chay lai ra ket qua 7/20 lan.
    r"|chưa thấy popup Add Widget ở màn nào trước đó|gen anh không tới được result|chụp bắt đầu trễ"
    r"|chưa đo được lúc nút X hiện|không có khung chụp ở mốc|không có nút Free Generate"
    r"|tả UI của màn cần lái tới|chưa làm được thao tác", re.I)


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
    if con_mo and all(l.get("tinh") or TAT_DINH_RE.search(l.get("reason") or "") for l in con_mo):
        m = next(TAT_DINH_RE.search(l.get("reason") or "") for l in con_mo if TAT_DINH_RE.search(l.get("reason") or ""))
        return f"lý do lặp chắc chắn ({m.group(0)}) — chạy lại vẫn y hệt"
    if dau_truoc is not None and dau_van(result) == dau_truoc:
        return "lần này ra y hệt lần trước ở mọi dòng"
    return ""


def dong_mo(result: dict) -> list:
    """[(so dong, verdict, ly do rut gon)] cac dong chua PASS/FAIL cua mot lan chay (ghi vao lich su chay lai)."""
    return [(l.get("n"), l["verdict"], (l.get("reason") or "")[:160]) for l in _dong(result)
            if l["verdict"] not in (PASS, FAIL)]
