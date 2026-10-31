"""Bang chung them cho case_run: man xa nhat Expected nhac, ban dich chuoi, mau primary, lai not toi Home.

Moi ham sinh ra tu mot FAIL / PASS gia tren AIP886 2.7.0 (31/10/2026) - xem tung ham.
"""

from __future__ import annotations

import re

from . import fo_screens

NGOAC_RE = re.compile(r"[\"“”'‘’]([^\"“”'‘’]{3,80})[\"“”'‘’]")
PRIMARY_RE = re.compile(r"m[àa]u\s+(?:primary|ch[ủu]\s*[đd][ạa]o)", re.I)
# "vao thang Home", "Vao Home binh thuong", "-> Home"
HOME_RE = re.compile(r"v[àa]o\s+(?:th[ẳa]ng\s+)?home|→\s*home|v[ềe]\s+home", re.I)
# Man chen giua ma luong user cu / sau Question van di qua truoc khi toi Home.
CHUA_TOI_HOME = ("AdActivity", "BillingActivity", "Splash")
TOI_THIEU, GAP = 40, 3


def man_xa(expects) -> str:
    """Man xa nhat ma cac dong Expected nhac ten ("OB2: ...", "OB4: ...") -> "OnboardingActivity#4".

    R01-04: "Di tiep qua OB2" ma Expected doi ca OB4 - lai toi OB3 thi dong OB4 FAIL gia.
    """
    mans = [fo_screens.target_for(e or "") for e in expects]
    # Ten man chac chan (trang OB co so, Question, paywall, Home). "OnboardingActivity" tran (an tu chu
    # "onboard_config...") khong tinh: xep sau moi trang, keo man_can di qua ca luong.
    mans = [m for m in mans if m and (m.startswith("OnboardingActivity#") or m in MAN_CHAC)]
    return max(mans, key=fo_screens.thu_tu) if mans else ""


MAN_CHAC = ("QuestionActivity", "BillingActivity", "MainActivity")


def can_tai_nguyen(expects) -> bool:
    return any(NGOAC_RE.search(e or "") or PRIMARY_RE.search(e or "") for e in expects)


def ban_dich_cho(expects, tai: dict) -> dict:
    """{chuoi trong ngoac cua Expected: [ban dich trong APK]} - khop khong phan biet hoa thuong
    (TC viet 'Swipe to next', resource 'Swipe to Next')."""
    theo_thuong = {k.casefold(): v for k, v in ((tai or {}).get("ban_dich") or {}).items()}
    ra = {}
    for e in expects:
        for chu in NGOAC_RE.findall(e or ""):
            dich = theo_thuong.get(chu.strip().casefold())
            if dich:
                ra[chu.strip()] = dich
    return ra


def mau_primary(expects, drive: dict, hex_: str, ban_dich: dict) -> dict | None:
    """Dong "text 'X' dung mau primary": dem pixel mau `color/primary` trong khung chu X (hoac ban dich cua X)."""
    dong = next((e for e in expects if PRIMARY_RE.search(e or "")), "")
    if not dong or not hex_:
        return None
    chu = [c.strip() for c in NGOAC_RE.findall(dong)]
    can = {c.casefold() for c in chu} | {d.casefold() for c in chu for d in ban_dich.get(c, [])}
    tot = None
    for st in (drive or {}).get("steps") or []:
        for m in st.get("mau") or []:
            if (m.get("text") or "").strip().casefold() in can and hex_ in m["dem"]:
                trong, doi = m["dem"][hex_]
                if tot is None or trong > tot[0]:
                    tot = (trong, doi, m["text"])
    if tot is None:
        return {"hex": hex_, "pixel": None}
    trong, doi, text = tot
    return {"hex": hex_, "pixel": trong, "chu": text, "khop": trong >= TOI_THIEU and trong >= GAP * doi,
            "thay": f"{trong} px trong khung, {doi} px dải đối chứng"}


def chu_chua_thay(expects, drive: dict) -> list[str]:
    """Chu trong ngoac cua Expected chua thay o dump nao (khong tinh ve phu dinh "khong co 'X'")."""
    dumps = [(s.get("dump") or "").casefold() for s in (drive or {}).get("steps") or []]
    ra = []
    for e in expects:
        for m in NGOAC_RE.finditer(e or ""):
            truoc = re.split(r"[,;]", (e or "")[:m.start()])[-1]
            chu = re.sub(r"\s*(?:\.{3}|…)\s*$", "", m.group(1)).strip()
            if re.search(r"\bkh[ôo]ng\b", truoc, re.I) or not chu:
                continue
            if not any(chu.casefold() in d for d in dumps):
                ra.append(chu)
    return ra


def can_ve_home(expects, drive: dict) -> bool:
    """Expected doi "vao (thang) Home" ma man sau buoc cuoi con la inter / paywall / splash.

    O02-01 (user cu, tat Question): tool cham luc inter splash con hien -> FAIL gia "dang o AdActivity".
    """
    cuoi = ((drive or {}).get("final") or {}).get("activity") or ""
    return bool(cuoi) and any(HOME_RE.search(e or "") for e in expects) and any(m in cuoi for m in CHUA_TOI_HOME)

