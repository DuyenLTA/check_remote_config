"""Dong Expected ve LUONG man quanh quang cao ma truoc day roi xuong "khong neu ro ky vong" / "phai nhin mat"
(chay thu AIP936 1.9.0 tren Pixel 6, 03/11/2026, nhom RG01 / RG08):

- "Splash chay tiep, luong sang Inter Splash binh thuong"  -> inter splash 102 co show (khong fill: request dung la dat)
- "Dong inter -> sang LFO1 binh thuong"                   -> man SAU khi tool dong ad la LFO1
- "App chay lai tu Splash, hien lai LFO1"                  -> co splash_view trong luot + man cuoi la LFO1
- "Sau khi bam tick: KHONG hien thi Inter Splash 2 (102)" -> 102 show toi da 1 lan (lan o splash), cham bang SHOW
  chu khong bang request: request 102 luc o splash la dung cho (truoc day FAIL gia "van co request 102")
- "Chua chon: an nut CTA, co ban tay hint" o man Question  -> dump Question dau tien: khong co nut CTA, co ban tay
"""

from __future__ import annotations

import re

from . import assert_ui, ui_dump
from .verdict_levels import FAIL, PASS, out

SANG_INTER_SPLASH_RE = re.compile(r"sang\s+inter\s*splash", re.I)
DONG_INTER_SANG_RE = re.compile(r"đóng\s+inter\s*(?:→|->|rồi)?\s*sang\s+(.+)", re.I)
CHAY_LAI_SPLASH_RE = re.compile(r"chạy\s+lại\s+từ\s+splash", re.I)
KHONG_INTER_SPLASH_2_RE = re.compile(r"kh[ôo]ng\s+(?:hiển\s+thị|hi[eệ]n|show)\s+inter\s*splash\s*2", re.I)
CTA_HINT_RE = re.compile(r"chưa\s+chọn.{0,20}(?:ẩn|không\s+có)\s+(?:nút\s+)?cta", re.I)
HINT_RE = re.compile(r"bàn\s+tay|hint", re.I)
CTA_IDS = ("btnNextQuestion", "btnNextOnboardingImage")
HINT_IDS = ("lottieQuestion", "lottieHandPoint")


# Inter splash 102: key `id_102_spl_*`, hoac app doc ID tu key rieng `splash_inter_high_n_id`, `splash_inter_n_id`...
# (AIP872 1.9.0: log chi co …751 cua `splash_inter_high_n_id`, khong co ID `id_102_*` cua checklist -> truoc day
# FAIL gia "khong co request nao cua inter splash 102").
INTER_SPLASH_KEY_RE = re.compile(r"102_spl|^splash_inter\w*_id$")


def _102(units: list[dict]) -> list[dict]:
    return [u for u in units if any(INTER_SPLASH_KEY_RE.search(k) for k in u.get("rc_keys") or [])]


def _final(drive: dict) -> dict:
    d = dict(drive or {})
    if d.get("final_sau_dong"):
        d["final"] = d["final_sau_dong"]          # man app sau khi tool dong ad dang che
    return d


def cham(text: str, units: list[dict], drive: dict, events=()) -> dict | None:
    t = text or ""
    if KHONG_INTER_SPLASH_2_RE.search(t):
        show = sum(u.get("shown", 0) for u in _102(units))
        if show <= 1:
            return out(PASS, f"inter 102 show {show} lần trong cả luồng"
                       + (" (lần ở splash) — không có Inter Splash 2" if show else ""), t)
        return out(FAIL, f"inter 102 show {show} lần — có Inter Splash 2", t)
    if SANG_INTER_SPLASH_RE.search(t):
        u = _102(units)
        if any(x.get("shown") for x in u):
            return out(PASS, "inter splash 102 show: " + ", ".join(f"…{x['unit'][-3:]}" for x in u if x.get("shown")), t)
        if any(x.get("requested") for x in u):
            return out(PASS, "inter splash 102 được request nhưng kho không fill — request đúng là đạt", t)
        return out(FAIL, "không có request nào của inter splash 102", t)
    m = DONG_INTER_SANG_RE.search(t)
    if m:
        return assert_ui._man_da_toi(m.group(1), _final(drive))
    if CHAY_LAI_SPLASH_RE.search(t):
        man = assert_ui._man_da_toi(re.split(CHAY_LAI_SPLASH_RE, t)[-1], _final(drive))
        if man is None:
            return None
        co_splash = any((e.get("name") or "").startswith("splash_view") for e in events or ())
        if not co_splash:
            return out(FAIL, f"không có splash_view sau khi mở lại; {man['reason']}", t)
        return out(man["verdict"], f"có splash_view (chạy lại từ Splash); {man['reason']}", t)
    if CTA_HINT_RE.search(t):
        for st in (drive or {}).get("steps") or []:
            if "QuestionActivity" in (st.get("activity") or "") and st.get("dump"):
                nodes = ui_dump.parse_dump(st["dump"])
                cta = [n for n in nodes if n.resource_id in CTA_IDS and n.visible and not n.bounds.empty]
                tay = any(n.resource_id in HINT_IDS and n.visible for n in nodes)
                ok = not cta and (tay or not HINT_RE.search(t))
                return out(PASS if ok else FAIL,
                           f"màn Question lúc chưa chọn: nút CTA {'không có' if not cta else 'ĐANG HIỆN'}, "
                           f"bàn tay hint {'có' if tay else 'không có'}", t)
        return None
    return None
