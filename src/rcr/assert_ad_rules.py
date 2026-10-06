"""Tung luat cham cho mot dong Expected noi ve quang cao.

Tach khoi `assert_ads` de moi file duoi 200 dong: `assert_ads` doc log va phan
loai cau, file nay la cac luat cham - impression, thu tu preload, cau phu dinh.
"""

from __future__ import annotations

import re

from .ad_positions import da_biet
from .verdict_levels import FAIL, NEEDS_HUMAN, NOT_VERIFIABLE, PASS, out

# "Impression fire dung 1 lan khi ad show" - dem dong "occurred for ad unit".
IMPRESSION_RE = re.compile(r"impression", re.I)
ZERO_RE = re.compile(r"=\s*0\b|kh[oô]ng\s+(?:c[óo]\s+)?impression", re.I)
# "SDK preload banner 101 theo alternate: high truoc, thuong sau" - doc THU TU
# request trong log. Khong biet unit nao la high (ID bi che), nhung dem duoc.
ORDER_RE = re.compile(r"preload|alternate|tr[ưu][ớo]c.*sau", re.I)
# "khong load BAT KY banner nao" - phu dinh toan loai, khong gioi han vi tri.
ANY_RE = re.compile(r"b[ấa]t\s*k[ỳy]|nào\b|any\b", re.I)


def impression(text: str, units: list[dict], actual: dict, token: str, khop,
               biet_id: bool = False) -> dict:
    """Dong noi ve impression.

    `token` la vi tri ma dong - hoac ca case - dang noi toi. Cau "Impressions = 0"
    KHONG tu nhac ten unit: ten no nam o dong Expected phia tren. Khong lay vi
    tri cua ca case thi day dem impression cua MOI unit trong app, va mot vi tri
    khac show ad la case bi bao FAIL - do that 2026-09-28, case #2/#3/#4 cua bo
    TC SDK 3.5.0: tat mot unit khong lam ca app het quang cao.
    """
    if token:
        thuoc = [u for u in units if khop(u, token)]
        if not thuoc:
            # Biet ID cua vi tri ma log khong co unit nao mang ID do -> vi tri
            # nay khong he chay, impression cua no bang 0. Ket luan duoc.
            if biet_id:
                if ZERO_RE.search(text):
                    return out(PASS, f"không unit nào của `{token}` chạy nên impression = 0 "
                                     "— đúng kỳ vọng", actual | {"impressions": 0})
                return out(NEEDS_HUMAN, f"vị trí `{token}` không chạy lượt này nên chưa có "
                                        "impression để đối chiếu", actual)
            return out(
                NOT_VERIFIABLE,
                f"không unit nào trong log map được về vị trí `{token}` nên không "
                "quy impression cho vị trí đó được — ID trong log bị che còn 3 số cuối",
                actual,
            )
        units = thuoc
    fired = sum(u["impressions"] for u in units)
    shown = [u for u in units if u["shown"]]
    requested = [u for u in units if u["requested"]]
    if ZERO_RE.search(text):
        if fired:
            return out(FAIL, f"impression bắn {fired} lần, kỳ vọng 0",
                       actual | {"impressions": fired})
        return out(PASS, "không có impression nào — đúng kỳ vọng", actual)
    if fired == 0 and not requested:
        return out(NEEDS_HUMAN, "chưa thấy unit nào được request nên không có impression", actual)
    if fired == 0 and not shown:
        # Khong co ad nao show thi khong co impression la DUNG (user chot: khong
        # fill ma request dung la dat).
        return out(PASS, "ad được request đúng nhưng không fill nên chưa có impression — "
                         "request đúng là đạt", actual)
    if ("1 lần" in text or "đúng 1" in text.lower()) and fired != 1:
        return out(FAIL, f"impression bắn {fired} lần, kỳ vọng đúng 1",
                   actual | {"impressions": fired})
    if fired:
        return out(PASS, f"impression bắn {fired} lần", actual | {"impressions": fired})
    return out(NOT_VERIFIABLE, "không thấy dòng impression nào trong log của app", actual)


def preload_order(kind: str, units: list[dict], actual: dict) -> dict | None:
    order = [u["unit"] for u in units if u["requested"]]
    if len(order) >= 2:
        return out(PASS, "request đúng thứ tự " + " → ".join(order)
                   + " (ID bị che nên không khẳng định được unit nào là high)", actual)
    if len(order) == 1:
        if any(u["loaded"] or u["shown"] for u in units):
            # Unit dau fill duoc thi SDK khong can goi alternate - dung thiet ke.
            return out(PASS, f"chỉ 1 unit {kind} được request vì unit đó fill luôn, "
                             "không cần gọi alternate", actual)
        return out(FAIL, f"chỉ có 1 unit {kind} được request, không có alternate", actual)
    return None


def negative(text: str, kind: str, requested: list[dict], actual: dict, token: str,
             khop, biet_id: bool = False) -> dict:
    """Cau phu dinh: ky vong KHONG co request."""
    if not requested:
        return out(PASS, f"không unit {kind} nào được request", actual)
    if ANY_RE.search(text):
        # "khong load BAT KY banner nao" - khong gioi han vi tri, moi request deu sai
        return out(FAIL, f"vẫn có request {kind}", actual)
    if not token:
        # Cau phu dinh khong neu vi tri nao -> moi unit map duoc deu tinh.
        if any(u.get("rc_keys") for u in requested):
            return out(FAIL, f"vẫn có request {kind}", actual)
        return out(NOT_VERIFIABLE,
                   f"có {len(requested)} request {kind} nhưng ID bị che, không map được unit "
                   "về vị trí nào — không quy được cho vị trí trong câu", actual)
    # Map duoc ve MOT key bat ky la chua du: request cua man khac
    # (id_301_onb1_n_native) bi tinh cho 303-onb3-n-native-high1 la bao oan dung
    # mot bug khong ton tai. Chi FAIL khi unit map ve DUNG vi tri cau noi.
    charged = [u["unit"] for u in requested if khop(u, token)]
    if charged:
        return out(FAIL, f"vẫn có request {kind} của {token}", actual | {"charged": charged})
    if biet_id:
        # ID cua vi tri nay co trong bang, ma khong request nao mang ID do ->
        # vi tri nay KHONG duoc request. Dung cai ma cau phu dinh doi hoi.
        return out(PASS, f"không request {kind} nào của `{token}` — ID vị trí này đã biết "
                         f"nên đối chiếu được, {len(requested)} request còn lại thuộc vị trí khác",
                   actual)
    khac = sorted({k for u in requested for k in (u.get("rc_keys") or ())})
    return out(NOT_VERIFIABLE,
               f"có {len(requested)} request {kind} nhưng không unit nào map được về vị trí "
               f"`{token}` — không quy được cho vị trí trong câu"
               + (f" — các unit map được thuộc vị trí khác: {', '.join(khac)}" if khac
                  else " — ID trong log bị che còn 3 số cuối"), actual)


def negative_theo_case(text: str, kind: str, requested: list[dict], actual: dict,
                       vi_tri: tuple[str, ...], khop, biet: set) -> dict:
    """Cau phu dinh khong nhac ma vi tri -> xet cac vi tri CHINH CASE NAY tat.

    "App KHONG request/load native ad" trong mot case tat `show_302_*` noi ve
    302, khong noi ve ca app: 301 va 303 van preload cho man sau, do la thiet ke.
    """
    if not requested:
        return out(PASS, f"không unit {kind} nào được request", actual)
    if ANY_RE.search(text):
        return out(FAIL, f"vẫn có request {kind}", actual)
    if not vi_tri:
        # Khong biet case noi ve vi tri nao -> giu cach cu.
        if any(u.get("rc_keys") for u in requested):
            return out(FAIL, f"vẫn có request {kind}", actual)
        return out(NOT_VERIFIABLE,
                   f"có {len(requested)} request {kind} nhưng ID bị che, không map được unit "
                   "về vị trí nào — không quy được cho vị trí trong câu", actual)
    ban = [u["unit"] for u in requested if any(khop(u, t) for t in vi_tri)]
    if ban:
        return out(FAIL, f"vẫn có request {kind} của {', '.join(sorted(set(vi_tri)))}",
                   actual | {"charged": ban})
    if all(da_biet(t, biet) for t in vi_tri):
        return out(PASS,
                   f"không request {kind} nào của {', '.join(vi_tri)} — ID các vị trí này đã "
                   f"biết nên đối chiếu được, {len(requested)} request còn lại thuộc vị trí khác",
                   actual)
    return out(NOT_VERIFIABLE,
               f"có {len(requested)} request {kind} nhưng chưa biết ID của "
               f"{', '.join(t for t in vi_tri if not da_biet(t, biet))} nên không quy được", actual)
