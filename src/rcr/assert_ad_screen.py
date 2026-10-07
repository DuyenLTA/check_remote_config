"""Cham dong "ad cua vi tri X co / KHONG show tai man Y" bang event `ad_show`.

Vi du (bo TC SDK 3.5.3, cum "202 hung sang"):
    "OB1 KHONG hien thi 202 (khong co log show 202 tai OB1)"
    "Logcat khong co log show 202 tai OB2"
    "OB1 hien thi native ad cua unit 202 (log show 202 tai OB1)"

Truoc day cac dong nay roi vao luat REQUEST: 202 duoc request o LFO2 (dung cho
cua no) nen dong nao cung ra "van co request native cua 202" -> FAIL oan
(do 2026-10-07: 5/9 case cum H202). Request khong noi ad show o man nao.

Cach cham, khong gan theo app:
  - moi event `ad_show` (app ban qua Firebase, co `ad_unit_id`) thuoc man cua
    event `<man>_view` gan nhat dung TRUOC no trong log (lfo1_view, ob2_view...);
  - unit -> vi tri qua key RC da map (`id_202_lfo2_n_native_high2`);
  - man "nha" cua vi tri lay tu chinh ten key (`_202_lfo2_`). Cau noi ve man nha
    (vd "LFO2 show 202") de luat cu cham.

Gioi han: `ad_show` la log cua app - do 07/10/2026 co luot log `ad_show` +
impression ma vung ad tren man TRONG. Ly do PASS/FAIL luon ghi "theo log".
"""

from __future__ import annotations

import re

from .verdict_levels import FAIL, NEEDS_HUMAN, PASS, out

MAN_RE = re.compile(r"\b(OB|LFO)\s*(\d)\b", re.I)
# Ma vi tri 3 chu so; bo qua khi nam trong so thap phan / phan tram ("3.5.0", "100%"),
# nhung "202." cuoi cau van la vi tri.
VI_TRI_RE = re.compile(r"(?<!\d)(?<!\d\.)([1-4]\d{2})(?!\d|\.\d|%)")
SHOW_RE = re.compile(r"\bshow\b|hi[ểe]n\s*th[ịi]|h[ứu]ng", re.I)
KHONG_RE = re.compile(r"\bkh[ôo]ng\b|\bnot\b", re.I)   # "no" thi trung "no-fill"
# Cau ve load/request thuoc luat request; "fallback" la y do, khong do bang show.
NGOAI_RE = re.compile(r"\bload|request|fallback", re.I)
VIEW_RE = re.compile(r"^((?:lfo|ob)\d)_view$")
KEY_MAN_RE = re.compile(r"_(\d{3})_((?:lfo|onb|ob)\d)_")


def _man_cua_key(key: str) -> tuple[str, str] | None:
    """`id_202_lfo2_n_native_high2` -> ("202", "lfo2"); `_onb1_` -> "ob1"."""
    m = KEY_MAN_RE.search(key or "")
    if not m:
        return None
    return m.group(1), m.group(2).replace("onb", "ob")


def show_theo_man(events, units) -> list[dict]:
    """[{man, unit, vi_tri}] cho moi `ad_show`, theo thu tu trong log."""
    theo_duoi = {}
    for u in units:
        duoi = (u.get("unit") or "").lstrip("*")[-3:]
        if duoi:
            theo_duoi[duoi] = u
    man, ra = "", []
    ds = list(events or ())
    for i, e in enumerate(ds):
        ten = e.get("name", "")
        m = VIEW_RE.match(ten)
        if m:
            man = m.group(1)
            continue
        if ten != "ad_show":
            continue
        # Ad cua man moi thuong log `ad_show` TRUOC `<man>_view` vai ms (do
        # 2026-10-07: 202 show luc vao LFO2, ad_show 304,820 - lfo2_view 304,836).
        # Event ke tiep la mot `_view` -> ad nay thuoc man do.
        ke = VIEW_RE.match(ds[i + 1].get("name", "")) if i + 1 < len(ds) else None
        uid = (e.get("params") or {}).get("ad_unit_id", "")
        u = theo_duoi.get(uid[-3:]) or {}
        vi_tri = {v for k in (u.get("rc_keys") or ()) if (v := _man_cua_key(k))}
        ra.append({"man": ke.group(1) if ke else man, "unit": "…" + uid[-3:] if uid else "?",
                   "vi_tri": {v[0] for v in vi_tri}, "nha": {v[1] for v in vi_tri}})
    return ra


def cham(text: str, events, units) -> dict | None:
    """None neu dong khong thuoc loai nay (de luat khac cham)."""
    mans = MAN_RE.findall(text)
    vts = set(VI_TRI_RE.findall(text))
    if not mans or len(vts) != 1 or not SHOW_RE.search(text) or NGOAI_RE.search(text):
        return None
    vt = vts.pop()
    man = f"{mans[0][0].lower()}{mans[0][1]}"
    nha = {n for u in units for k in (u.get("rc_keys") or ())
           if (v := _man_cua_key(k)) and v[0] == vt for n in [v[1]]}
    if man in nha or not nha:
        return None                      # cau ve man nha / chua biet vi tri -> luat cu
    views = [e for e in events or () if VIEW_RE.match(e.get("name", ""))]
    if not views:
        return None                      # app khong ban event man -> khong gan duoc
    if not any(e["name"] == f"{man}_view" for e in views):
        return out(NEEDS_HUMAN, f"lượt này không vào {man.upper()} (không có event {man}_view)", "")
    shows = [s for s in show_theo_man(events, units) if s["man"] == man and vt in s["vi_tri"]]
    tom = ", ".join(s["unit"] for s in shows)
    actual = {"show_tai_man": [s["unit"] for s in shows], "man": man, "vi_tri": vt}
    if KHONG_RE.search(text):
        if shows:
            return out(FAIL, f"log có ad_show của {vt} ({tom}) khi đang ở {man.upper()}", actual)
        return out(PASS, f"không có ad_show nào của {vt} khi đang ở {man.upper()} (theo log event "
                         f"ad_show + {man}_view; request {vt} ở {', '.join(sorted(nha)).upper()} là "
                         "đúng chỗ, không tính)", actual)
    if shows:
        return out(PASS, f"log có ad_show của {vt} ({tom}) khi đang ở {man.upper()}", actual)
    return out(FAIL, f"không có ad_show nào của {vt} khi đang ở {man.upper()}", actual)


def ad_man_nha_da_show(events, units, man: str) -> list[str]:
    """Unit cua vi tri co man nha `man` (vd lfo2) da `ad_show` NGAY tai man do.

    Dung de kiem precondition "202 da load nhung CHUA show o LFO2": co thi dieu
    kien chua tao duoc, ket qua cua luot khong noi gi ve nhanh TC hoi.
    """
    return [s["unit"] for s in show_theo_man(events, units) if s["man"] == man and man in s["nha"]]
