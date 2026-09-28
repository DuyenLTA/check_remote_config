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

from . import assert_ad_rules
from .verdict_levels import FAIL, NEEDS_HUMAN, NOT_VERIFIABLE, PASS, out

NEGATIVE_RE = re.compile(
    r"(?:kh[oô]ng|ko)\s+(?:c[óo]\s+|[đd][ưu][ợo]c\s+)?"
    r"(?:load|show|hi[ểe]n|request|g[ọo]i|xu[ấa]t hi[ệe]n)|requests?\s*=\s*0",
    re.I,
)
SHOW_RE = re.compile(r"hi[ểe]n\s*th[ịi]|show|xu[ấa]t\s*hi[ệe]n", re.I)
# Nguon ngoai tool: console AdMob, Firebase - khong doc duoc tu may.
EXTERNAL_RE = re.compile(r"admob\s*console|firebase\s*console|dashboard", re.I)
# Ma vi tri ads trong TC: 101-spl-a-banner, 105-spl-n-native-high, "tren splash"...
POSITION_RE = re.compile(r"\b\d{3}\b|splash|home|onboarding|lfo|ob\d|result|tab\s+\w+", re.I)
# Ma vi tri (202, 304...) khong kem chu "native"/"inter" -> tra loai tu TEN
# KEY RC THAT cua app (`show_202_lfo2_n_native_high` -> native). Du lieu that,
# khong phai bang tu doan.
POS_CODE_RE = re.compile(r"\b(\d{3})\b")
# Ma day du trong cau TC: "303-onb3-n-native-high1" -> khop key RC
# `id_303_onb3_n_native_high1`. Chi co 3 so ("105", "tren splash") thi lay so.
TC_CODE_RE = re.compile(r"\b\d{3}(?:-[a-z0-9]+)+", re.I)

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
    return bool(assert_ad_rules.IMPRESSION_RE.search(text) or EXTERNAL_RE.search(text))


def _position_token(text: str) -> str:
    """Vi tri ma cau dang noi toi, dang khop duoc voi ten key RC."""
    day_du = TC_CODE_RE.search(text)
    if day_du:
        return day_du.group(0).replace("-", "_").lower()
    chi_so = POS_CODE_RE.search(text)
    return chi_so.group(1) if chi_so else ""


def _khop_vi_tri(unit: dict, token: str) -> bool:
    """Khop TRON VEN: `..._high` khong duoc an vao `..._high1`.

    Hai cai do la hai unit khac nhau voi hai ky vong khac nhau - so bang
    `in` thi request cua high1 bi tinh cho high, bao oan theo chieu nguoc lai.
    """
    sau_token = re.compile(re.escape(token) + "(?![a-z0-9])")
    return any(sau_token.search(k.lower()) for k in (unit.get("rc_keys") or ()))


def _units(ads: dict, kind: str) -> list[dict]:
    """`kind` rong -> moi unit (cau khong neu loai, vd dong impression)."""
    return [u for u in (ads.get("units") or {}).values() if not kind or u["type"] == kind]


def ad_line(text: str, kind: str, ads: dict, drive: dict, scope: str = "") -> dict:
    """`kind` rong nghia la xet moi loai ad.

    `scope` la vi tri unit ma CA case noi toi, dung cho dong khong tu nhac ten
    unit (vd "Impressions = 0" - ten unit nam o dong Expected phia tren).
    """
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

    if assert_ad_rules.IMPRESSION_RE.search(text):
        return assert_ad_rules.impression(
            text, units, actual, _position_token(text) or scope, _khop_vi_tri)

    # Cau PHU DINH co chu "alternate" ("khong duoc goi ke ca trong alternate")
    # khong phai cau ta thu tu preload - kiem NEGATIVE truoc.
    if assert_ad_rules.ORDER_RE.search(text) and not NEGATIVE_RE.search(text):
        ket = assert_ad_rules.preload_order(kind, units, actual)
        if ket:
            return ket

    if NEGATIVE_RE.search(text):
        return assert_ad_rules.negative(
            text, kind, requested, actual, _position_token(text), _khop_vi_tri)

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




def case_position(lines) -> str:
    """Vi tri unit ma CA case noi toi, "" neu cac dong noi ve nhieu vi tri.

    Dong "Impressions = 0" khong tu nhac ten unit; ten no nam o dong Expected
    phia tren cua cung case. Chi nhan khi CA khoi Expected noi ve DUNG MOT vi
    tri - nhieu vi tri thi lay cai nao cung la doan.
    """
    tokens = {t for t in (_position_token(l or "") for l in lines) if t}
    return tokens.pop() if len(tokens) == 1 else ""
