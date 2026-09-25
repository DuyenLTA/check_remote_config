"""Cham dong Expected noi ve quang cao, bang log da doc duoc.

Cham o TANG REQUEST/LOAD, khong doi nhin thay ad: inter load nhanh hon banner
nen no de len truoc khi kip nhin (user chot 2026-09-25). Co log load la du.

KHONG FILL VAN TINH DAT (user chot 2026-09-25): kho quang cao khong tra ad la
chuyen cua kho, logic app van dung. Mien la unit duoc request dung.

Hai cho co y KHONG ket luan:
  - ID trong log bi che, khong map duoc unit ve key RC -> cau gioi han theo vi
    tri (105 / "tren splash") khong quy duoc cho vi tri do
  - tool chua tap gi = van o man mo dau -> ads cua man phai lai toi tat nhien
    chua request, bao FAIL la bao oan app thieu ads
"""

from __future__ import annotations

import re

from .verdict_levels import FAIL, NEEDS_HUMAN, NOT_VERIFIABLE, PASS, out

NEGATIVE_RE = re.compile(
    r"(?:kh[oô]ng|ko)\s+(?:c[óo]\s+|[đd][ưu][ợo]c\s+)?"
    r"(?:load|show|hi[ểe]n|request|g[ọo]i|xu[ấa]t hi[ệe]n)|requests?\s*=\s*0",
    re.I,
)
SHOW_RE = re.compile(r"hi[ểe]n\s*th[ịi]|show|xu[ấa]t\s*hi[ệe]n", re.I)
# "Impression fire dung 1 lan khi ad show" - dem dong "occurred for ad unit".
IMPRESSION_RE = re.compile(r"impression", re.I)
ZERO_RE = re.compile(r"=\s*0\b|kh[oô]ng\s+(?:c[óo]\s+)?impression", re.I)
# "SDK preload banner 101 theo alternate: high truoc, thuong sau" - doc THU TU
# request trong log. Khong biet unit nao la high (ID bi che), nhung dem duoc.
ORDER_RE = re.compile(r"preload|alternate|tr[ưu][ớo]c.*sau", re.I)
# Nguon ngoai tool: console AdMob, Firebase - khong doc duoc tu may.
EXTERNAL_RE = re.compile(r"admob\s*console|firebase\s*console|dashboard", re.I)
# "khong load BAT KY banner nao" - phu dinh toan loai, khong gioi han vi tri.
ANY_RE = re.compile(r"b[ấa]t\s*k[ỳy]|nào\b|any\b", re.I)
# Ma vi tri ads trong TC: 101-spl-a-banner, 105-spl-n-native-high, "tren splash"...
POSITION_RE = re.compile(r"\b\d{3}\b|splash|home|onboarding|lfo|ob\d|result|tab\s+\w+", re.I)
# Ma vi tri (202, 304...) khong kem chu "native"/"inter" -> tra loai tu TEN
# KEY RC THAT cua app (`show_202_lfo2_n_native_high` -> native). Du lieu that,
# khong phai bang tu doan.
POS_CODE_RE = re.compile(r"\b(\d{3})\b")

AD_TYPES = {
    "banner": ("banner",),
    "native": ("native",),
    "interstitial": ("inter", "interstitial"),
}


def worst(verdicts) -> str:
    """Verdict cua case = dong xau nhat."""
    seen = set(verdicts)
    for level in SEVERITY:
        if level in seen:
            return level
    return NOT_VERIFIABLE


def ad_type_in(text: str) -> str:
    """Loai ad ma dong Expected dang noi toi, "" neu khong noi ro."""
    low = text.lower()
    for kind, words in AD_TYPES.items():
        if any(w in low for w in words):
            return kind
    return ""


def type_from_position(text: str, rc_keys) -> str:
    """Ma vi tri trong cau -> loai ad, tra theo ten key remote config cua app."""
    for code in POS_CODE_RE.findall(text):
        for key in rc_keys:
            if f"_{code}_" not in key:
                continue
            low = key.lower()
            for kind, words in AD_TYPES.items():
                if any(w in low for w in words):
                    return kind
    return ""


def tapped(drive: dict) -> bool:
    """Tool da toi duoc man can cham chua.

    Tinh ca chuyen LAI qua luong First Open (`walked`), khong chi cac buoc
    Action: case ve man onboarding thuong khong co buoc tap nao, nhung neu da
    lai toi dung man thi dump/anh la bang chung that.
    """
    if drive.get("walked"):
        return True
    return any(s.get("action", {}).get("kind") == "tap" for s in (drive.get("steps") or []))


def where(drive: dict) -> str:
    steps = drive.get("steps") or []
    return steps[-1].get("activity", "") if steps else ""


def routes(text: str) -> bool:
    """Dong nay phai do bang log ads du khong neu ten loai ad."""
    return bool(IMPRESSION_RE.search(text) or EXTERNAL_RE.search(text))


def _units(ads: dict, kind: str) -> list[dict]:
    """`kind` rong -> moi unit (cau khong neu loai, vd dong impression)."""
    return [u for u in (ads.get("units") or {}).values() if not kind or u["type"] == kind]


def check(line: str, ads: dict, drive: dict, crash: dict, rc_keys=()) -> dict:
    """Cham mot dong Expected -> {verdict, reason, actual}."""
    text = " ".join((line or "").split())
    if not text:
        return out(NOT_VERIFIABLE, "dong rong", "")

    if NO_CRASH_RE.search(text):
        if crash.get("crashed"):
            return out(FAIL, "app crash trong luot chay", crash.get("lines", [])[:3])
        return out(PASS, "khong thay crash nao cua app trong buffer crash", "")

    kind = ad_type_in(text) or type_from_position(text, rc_keys)
    if kind:
        return _ad_line(text, kind, ads, drive)

    quoted = QUOTED_RE.search(text)
    if quoted:
        return _text_on_screen(quoted.group(1), drive)

    return out(NOT_VERIFIABLE, "dong nay khong do duoc bang dump/log - nguoi nhin", text)


def ad_line(text: str, kind: str, ads: dict, drive: dict) -> dict:
    """`kind` rong nghia la xet moi loai ad."""
    units = _units(ads, kind)
    requested = [u for u in units if u["requested"]]
    loaded = [u for u in units if u["loaded"]]
    shown = [u for u in units if u["shown"]]
    actual = {
        "requested": [u["unit"] for u in requested],
        "loaded": [u["unit"] for u in loaded],
        "shown": [u["unit"] for u in shown],
    }

    if EXTERNAL_RE.search(text):
        return out(NOT_VERIFIABLE,
                   "dòng này phải mở console AdMob/Firebase mới biết — ngoài tầm của tool", actual)

    if IMPRESSION_RE.search(text):
        fired = sum(u["impressions"] for u in units)
        want_one = "1 lần" in text or "đúng 1" in text.lower()
        # "Impressions = 0 (Impressions > 0 = loi nang)" - ky vong KHONG co impression.
        if ZERO_RE.search(text):
            if fired:
                return out(FAIL, f"impression bắn {fired} lần, kỳ vọng 0", actual | {"impressions": fired})
            return out(PASS, "không có impression nào — đúng kỳ vọng", actual)
        if fired == 0 and not requested:
            return out(NEEDS_HUMAN,
                       f"chưa thấy {kind or 'unit'} nào được request nên không có impression", actual)
        if fired == 0 and not shown:
            # Khong co ad nao show thi khong co impression la DUNG, khong phai loi app.
            return out(PASS,
                       "không có ad nào show (không fill) nên chưa có impression — "
                       "tính đạt theo luật không-fill", actual)
        if want_one and fired != 1:
            return out(FAIL, f"impression bắn {fired} lần, kỳ vọng đúng 1", actual | {"impressions": fired})
        if fired:
            return out(PASS, f"impression bắn {fired} lần", actual | {"impressions": fired})
        return out(NOT_VERIFIABLE, "không thấy dòng impression nào trong log của app", actual)

    # Cau PHU DINH co chu "alternate" ("khong duoc goi ke ca trong alternate")
    # khong phai cau ta thu tu preload - kiem NEGATIVE truoc.
    if ORDER_RE.search(text) and not NEGATIVE_RE.search(text):
        order = [u["unit"] for u in units if u["requested"]]
        if len(order) >= 2:
            return out(PASS, "request đúng thứ tự " + " → ".join(order)
                       + " (ID bị che nên không khẳng định được unit nào là high)", actual)
        if len(order) == 1:
            if loaded or shown:
                # Unit dau fill duoc thi SDK khong can goi alternate - dung thiet ke.
                return out(PASS,
                           f"chỉ 1 unit {kind} được request vì unit đó fill luôn, "
                           "không cần gọi alternate", actual)
            return out(FAIL, f"chỉ có 1 unit {kind} được request, không có alternate", actual)

    if NEGATIVE_RE.search(text):
        if not requested:
            return out(PASS, f"không unit {kind} nào được request", actual)
        if ANY_RE.search(text):
            # "khong load BAT KY banner nao" - khong gioi han vi tri, moi request deu sai
            return out(FAIL, f"vẫn có request {kind}", actual)
        if any(u.get("rc_keys") for u in requested):
            # Map duoc unit ve key remote config -> quy duoc trach nhiem.
            return out(FAIL, f"vẫn có request {kind}", actual)
        # ID trong log bi che con 3 so cuoi, khong unit nao map duoc ve key ->
        # KHONG biet request nay thuoc vi tri nao. Rat co the la vi tri khac dang
        # preload. Bao FAIL o day la bao oan.
        return out(
            NOT_VERIFIABLE,
            f"có {len(requested)} request {kind} nhưng ID bị che, không map được unit về "
            "vị trí nào — không quy được cho vị trí trong câu",
            actual,
        )

    if not SHOW_RE.search(text):
        return out(NOT_VERIFIABLE, f"câu nói về {kind} nhưng không nêu rõ kỳ vọng", actual)

    if shown:
        return out(PASS, f"{kind} đã show", actual)
    if loaded:
        # User chot: co log load la du. Inter de len truoc khi kip nhin banner.
        return out(PASS, f"{kind} load được — chấm ở tầng load, không đòi nhìn thấy ad", actual)
    if requested:
        # Khong fill van tinh dat: unit duoc request dung la logic app dung. Ghi ro
        # trong reason de nguoi doc biet la chua thay ad tren man hinh.
        return out(PASS, f"{kind} request đúng nhưng kho quảng cáo không trả ad — logic đúng, tính đạt", actual)
    if not tapped(drive):
        # Chua tap gi = van o man mo dau. Ads cua man phai lai toi thi tat nhien
        # chua request - bao FAIL o day la bao oan app thieu ads.
        return out(
            NEEDS_HUMAN,
            f"không có request {kind} nào, nhưng tool chưa lái tới màn nào khác "
            f"(đang ở {where(drive) or 'màn mở đầu'})",
            actual,
        )
    return out(FAIL, f"không có request {kind} nào", actual)


