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

from . import ad_positions, assert_ad_rules
from .ad_positions import (  # noqa: F401 - tai xuat cho cho goi cu
    case_position,
    vi_tri_cua_case,
)
from .verdict_levels import FAIL, NEEDS_HUMAN, NOT_VERIFIABLE, PASS, out

# Toi 2 chu chen giua "khong" va dong tu: "KHONG phat sinh request",
# "khong duoc goi". Chen khong gioi han thi mot cau khang dinh o ve sau cung bi
# hut vao phu dinh o ve dau.
NEGATIVE_RE = re.compile(
    r"(?:kh[oô]ng|ko)\s+(?:\w+\s+){0,2}?"
    r"(?:load|show|hi[ểe]n|request|g[ọo]i|xu[ấa]t hi[ệe]n)|requests?\s*=\s*0",
    re.I,
)
SHOW_RE = re.compile(r"hi[ểe]n\s*th[ịi]|show|xu[ấa]t\s*hi[ệe]n", re.I)
# Nguon ngoai tool: console AdMob, Firebase - khong doc duoc tu may.
EXTERNAL_RE = re.compile(r"admob\s*console|firebase\s*console|dashboard", re.I)
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
    for code in ad_positions.POS_CODE_RE.findall(text):
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
    # Buoc GoTo da lai xong cung tinh: case 17 di het luong FO toi Home bang
    # DUNG MOT buoc GoTo, khong co cu tap nao trong nhat ky - the ma moi dong ta
    # UI cua no deu bi tra ve "tool moi dung o man mo dau" (do 2026-09-28).
    return any(s.get("action", {}).get("kind") in ("tap", "goto")
               for s in (drive.get("steps") or []))


def where(drive: dict) -> str:
    steps = drive.get("steps") or []
    return steps[-1].get("activity", "") if steps else ""


# "Requests = 0 cho unit OFF" - noi ve request ads ma KHONG neu ten loai ad va
# khong co ma vi tri nao. Khong bat o day thi dong nay roi xuong luat UI va bi
# tra ve "phai nhin mat", trong khi so request la thu duy nhat log noi duoc
# (do 2026-09-28, case 17 va 18: dong quyet dinh cua ca case bi bo qua).
REQUEST_RE = re.compile(r"requests?\b|ph[áa]t\s*sinh\s*request", re.I)


def routes(text: str) -> bool:
    """Dong nay phai do bang log ads du khong neu ten loai ad."""
    return bool(assert_ad_rules.IMPRESSION_RE.search(text) or EXTERNAL_RE.search(text)
                or REQUEST_RE.search(text))


def _units(ads: dict, kind: str) -> list[dict]:
    """`kind` rong -> moi unit (cau khong neu loai, vd dong impression)."""
    return [u for u in (ads.get("units") or {}).values() if not kind or u["type"] == kind]


def ad_line(text: str, kind: str, ads: dict, drive: dict, scope: str = "",
            vi_tri=()) -> dict:
    """`kind` rong nghia la xet moi loai ad.

    `scope` la vi tri unit ma CA case noi toi, dung cho dong khong tu nhac ten
    unit (vd "Impressions = 0" - ten unit nam o dong Expected phia tren).
    `vi_tri` la cac vi tri chinh case nay BAT/TAT (suy tu key da dat) - cau phu
    dinh chung chung ("App KHONG request native ad") noi ve dung chung no.
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

    # Cau nhac console nhung DOI DUNG thu tool do duoc ("Requests = 0 cho unit
    # X") thi cham bang log, khong day sang cho nguoi: so request trong log
    # chinh la so AdMob dem. Chi cau khong co ky vong do duoc moi bo qua.
    if EXTERNAL_RE.search(text) and not (NEGATIVE_RE.search(text)
                                         or assert_ad_rules.IMPRESSION_RE.search(text)):
        return out(NOT_VERIFIABLE,
                   "số liệu trên console AdMob/Firebase — PO đối soát, tester không có quyền vào",
                   actual, scope="po")

    biet = set(ads.get("positions") or ())
    if assert_ad_rules.IMPRESSION_RE.search(text):
        token = ad_positions._position_token(text) or scope
        return assert_ad_rules.impression(
            text, units, actual, token, ad_positions._khop_vi_tri, token in biet)

    # Cau PHU DINH co chu "alternate" ("khong duoc goi ke ca trong alternate")
    # khong phai cau ta thu tu preload - kiem NEGATIVE truoc.
    if assert_ad_rules.ORDER_RE.search(text) and not NEGATIVE_RE.search(text):
        ket = assert_ad_rules.preload_order(kind, units, actual)
        if ket:
            return ket

    if NEGATIVE_RE.search(text):
        token = ad_positions._position_token(text)
        if token:
            return assert_ad_rules.negative(
                text, kind, requested, actual, token, ad_positions._khop_vi_tri, token in biet)
        return assert_ad_rules.negative_theo_case(
            text, kind, requested, actual, tuple(vi_tri), ad_positions._khop_vi_tri, biet)

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


