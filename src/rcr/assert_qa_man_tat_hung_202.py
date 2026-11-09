"""Hai luat QA chot 05/11/2026 (AIP893, TC SDK 3.5.4) ma cau chu TC noi nguoc lai.

1. "Hung 202": ad 202 (LFO2) da load ma CHUA show thi man OB DAU TIEN sau LFO show ad 202
   do thay cho ad cua chinh man. Dong "Native 301-onb1-n-native-high hien thi, khong show
   202-lfo2-n-native-high" ma log co `ad_show` 202 tai OB1 la DUNG thiet ke, khong FAIL.
   Do: LFO2 bam doi ngon ngu -> show 202 + request 202 moi, chua kip show thi bam tick ->
   OB1 ad_show dung ad 202 do. Tat OB1 thi OB2 (man OB dau) hung.
2. "Man tat giu logic load": man bi tat (enable_onbN_screen / enable_ob1_old_screen = false)
   thi ad cua man do VAN preload / load o vi tri cu nhu luong thuong, chi khong show. Dong TC
   "Khong co loadAd <ad man tat>" khong ap dung: co request la dung; KHONG co request tier
   high thi phai doi chieu voi luong du (diem preload co nam truoc man tat khong) -> NEEDS_HUMAN.
   Vi du: tat OB Old ma 301-onb1-o-native-high van load o Splash = dung.

Chi nhan dong ma MOI vi tri trong cau deu thuoc luat; dong tron vi tri khac de luat cu cham.
"""

from __future__ import annotations

import re

from .assert_ad_nhieu_ve import LOAD_RE, NEG_RE, REQ_RE, SHOW_RE, ma_vi_tri
from .assert_ad_screen import show_theo_man
from .ad_positions import _khop_vi_tri
from .verdict_levels import NEEDS_HUMAN, PASS, out

MAN_CODE_RE = re.compile(r"^\d{3}_onb(\d)_([no])_")
OB_VIEW_RE = re.compile(r"^ob(\d)_view$")
LUAT_HUNG = "luật QA 05/11/2026: 202 đã load mà chưa show thì màn OB đầu tiên show 202 đó thay ad của màn"
LUAT_TAT = "luật QA 05/11/2026: màn tắt vẫn giữ logic preload/load của ad, chỉ không show"


def key_man(code: str) -> str | None:
    """`301_onb1_o_native_high` -> enable_ob1_old_screen; `302_onb2_n_...` -> enable_onb2_screen.

    Chi OB1-OB4: 305/306 (`onb5`) la ad cua man Question, ten khong chi ra man.
    """
    m = MAN_CODE_RE.match(code)
    if not m or not 1 <= int(m.group(1)) <= 4:
        return None
    return "enable_ob1_old_screen" if m.group(2) == "o" else f"enable_onb{m.group(1)}_screen"


def _man_tat(code: str, cfg) -> bool:
    k = key_man(code)
    return bool(k) and str((cfg or {}).get(k, "")).lower() == "false"


def _ob_dau(events) -> str:
    for e in events or ():
        m = OB_VIEW_RE.match(e.get("name", ""))
        if m:
            return f"ob{m.group(1)}"
    return ""


def _hung_202(text: str, codes: list[str], events, units) -> dict | None:
    hai = [c for c in codes if c.startswith("202")]
    ob = [c for c in codes if MAN_CODE_RE.match(c) and "_n_" in c]
    if not hai or len(ob) != 1 or len(hai) + len(ob) != len(codes) or not SHOW_RE.search(text):
        return None
    man = f"ob{MAN_CODE_RE.match(ob[0]).group(1)}"
    if _ob_dau(events) != man:
        return None
    shows = [s["unit"] for s in show_theo_man(events, units) if s["man"] == man and "202" in s["vi_tri"]]
    if not shows:
        return None
    return out(PASS, f"{man.upper()} là màn OB đầu tiên và show 202 ({', '.join(shows)}) thay "
                     f"`{ob[0]}` — {LUAT_HUNG}", {"show_tai_man": shows, "man": man})


def _man_tat_load(text: str, codes: list[str], units, cfg) -> dict | None:
    if not NEG_RE.search(text) or not (LOAD_RE.search(text) or REQ_RE.search(text)):
        return None
    if not codes or not all(_man_tat(c, cfg) for c in codes):
        return None
    co, thieu = [], []
    for c in codes:
        req = [u["unit"] for u in units if _khop_vi_tri(u, c) and u.get("requested")]
        if req:
            co.append(f"`{c}` request {', '.join(req)}")
        elif c.endswith("_high"):
            thieu.append(c)
    ly_do = "; ".join(co) or "không có request nào"
    if thieu:
        return out(NEEDS_HUMAN, f"{LUAT_TAT}. {ly_do}; tier high {', '.join(thieu)} KHÔNG có request — "
                                "đối chiếu điểm preload ở luồng đủ (trước màn tắt thì phải có)", "")
    return out(PASS, f"{LUAT_TAT}: câu 'không loadAd' của màn tắt không áp dụng. {ly_do}", "")


def cham(text: str, events, units, cfg) -> dict | None:
    """None -> dong khong thuoc hai luat nay."""
    codes = ma_vi_tri(text)
    return _hung_202(text, codes, events, units) or _man_tat_load(text, codes, units, cfg)
