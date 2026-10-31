"""Ngon ngu case doi chon o LFO ("Chon Francais o LFO1", "ngon ngu da chon = Francais") -> `fo_flow` chon dung.

Truoc day luat LFO luon chon English (`data/fo_flow.yaml`), buoc "Chon Francais o LFO1" khong dich duoc:
case dung o Splash (NEEDS_HUMAN) hoac lai luong bang English roi cham noi dung khoi `fr` -> FAIL gia
(AIP886 31/10/2026: R01-03, R02-02, R03-03, R04-01...). Ngon ngu cua case dat vao `CHON` truoc khi reset /
lai luong, MOI lan `fo_flow` qua LFO trong case deu chon no.
"""

from __future__ import annotations

import contextvars
import re

# (ten goc, bien the TC ghi) cua case dang chay; None = luat mac dinh trong fo_flow.yaml.
CHON: contextvars.ContextVar[tuple[str, str] | None] = contextvars.ContextVar("ngon_ngu_case", default=None)

# Ten ngon ngu tren man LFO (ten ban dia + ten tieng Anh). Chi nhan "Chon X" khi X la ngon ngu: "Chon 1 item"
# khong phai.
TEN = {t.casefold() for t in (
    "English", "Français", "French", "Español", "Spanish", "Português", "Portuguese", "Deutsch", "German",
    "हिन्दी", "Hindi", "Chinese", "中文", "Русский", "Russian", "Indonesian", "Bahasa Indonesia", "বাংলা",
    "Bengali", "Afrikaans", "Tiếng Việt", "Vietnamese", "한국어", "Korean", "日本語", "Japanese", "Italiano",
    "Italian", "Türkçe", "Turkish", "العربية", "Arabic", "ไทย", "Thai", "Filipino", "Nederlands", "Dutch",
    "Polski", "Polish")}
CHON_RE = re.compile(r"^\s*(?:ch[ọo]n|select|pick)\s+(?:ng[ôo]n\s*ng[ữu]\s+)?(?P<ten>[^\s(,.]+(?:\s+[^\s(,.]+)?)"
                     r"(?:\s*\((?P<bt>[^)]+)\))?(?:\s+(?:[ởo]|t[ạa]i)\s+LFO\s*\d)?\s*\.?\s*$", re.I)
TIEN_DK_RE = re.compile(r"ng[ôo]n\s*ng[ữu]\s*(?:[đd][ãa]\s*ch[ọo]n)?\s*[=:]\s*(?P<ten>[^\s(),.]+)"
                        r"(?:\s*\((?P<bt>[^)]+)\))?", re.I)
# TC viet ten nuoc day du, app viet tat: "English (United States)" <-> "English (US)".
VIET_TAT = {"united states": "us", "usa": "us", "america": "us", "united kingdom": "uk", "great britain": "uk",
            "britain": "uk", "england": "uk", "brasil": "brazil"}


def _goc(ten: str) -> str | None:
    """Ten ngon ngu (1-2 tu dau) neu la ngon ngu biet, khong thi None."""
    tu = ten.split()
    for n in (2, 1):
        if len(tu) >= n and " ".join(tu[:n]).casefold() in TEN:
            return " ".join(tu[:n])
    return None


def doc_cau(step: str) -> tuple[str, str] | None:
    """"Chon English (United States) o LFO1" -> ("English", "English (United States)"). Khong phai -> None."""
    m = CHON_RE.match(step or "")
    goc = _goc(m.group("ten")) if m else None
    if not goc:
        return None
    return goc, f"{goc} ({m.group('bt').strip()})" if m.group("bt") else goc


def tim(precondition: str, steps=()) -> tuple[str, str] | None:
    """Ngon ngu case doi: buoc Action "Chon X" thang, roi toi precondition "ngon ngu da chon = X"."""
    for st in steps:
        ra = doc_cau(st)
        if ra:
            return ra
    m = TIEN_DK_RE.search(precondition or "")
    goc = _goc(m.group("ten")) if m else None
    if goc:
        return goc, f"{goc} ({m.group('bt').strip()})" if m.group("bt") else goc
    return None


TIEP_NOI_RE = re.compile(r"ti[ếe]p\s*n[ốo]i\s+([A-Za-z0-9]+-[A-Za-z0-9-]+)", re.I)


def tim_theo_chuoi(key: str, cases: dict, sau: int = 10) -> tuple[str, str] | None:
    """Ngon ngu cua case, lan nguoc chuoi "Tiep noi SDK361-R01-03" (cung luot, khong clear data) toi case da chon.

    R01-04 chi ghi "Tiep noi R01-03" - ngon ngu Francais chon o R01-03. Tool chay moi case rieng (pm clear) nen
    phai mang ngon ngu theo, khong thi lai luong bang English roi cham khoi 'fr' -> FAIL gia (AIP886 31/10/2026).
    `cases`: {key: {"precondition", "actions"}}.
    """
    for _ in range(sau):
        c = cases.get(key) or {}
        ra = tim(c.get("precondition", ""), c.get("actions") or ())
        if ra:
            return ra
        m = TIEP_NOI_RE.search(c.get("precondition", ""))
        if not m:
            return None
        key = next((k for k in cases if k.endswith(m.group(1))), "")
        if not key:
            return None
    return None


def tien_dk_chuoi(key: str, cases: dict, sau: int = 10) -> str:
    """Precondition cua case noi them precondition cac case no "Tiep noi" (S03-02 tiep noi S03-01 "Thiet bi
    OPPO" -> S03-02 cung doi may OPPO)."""
    ra = []
    for _ in range(sau):
        c = cases.get(key) or {}
        ra.append(c.get("precondition", ""))
        m = TIEP_NOI_RE.search(c.get("precondition", ""))
        key = next((k for k in cases if m and k.endswith(m.group(1))), "")
        if not key:
            break
    return "\n".join(ra)


def _trong_ngoac(ten: str) -> str:
    m = re.search(r"\(([^)]+)\)", ten)
    if not m:
        return ""
    k = m.group(1).strip().casefold()
    return VIET_TAT.get(k, k)


def khop_bien_the(muon: str, bien_the: list[str]) -> int | None:
    """Chi so bien the khop `muon` trong danh sach chu cua hang thut vao. None = khong co bien the nao khop.

    `muon` khong co ngoac ("Francais"): bien the trung ten goc ("Francais"), khong co thi bien the dau.
    """
    if not bien_the:
        return None
    can = _trong_ngoac(muon)
    if not can:
        same = [i for i, t in enumerate(bien_the) if t.strip().casefold() == muon.strip().casefold()]
        return same[0] if same else 0
    for i, t in enumerate(bien_the):
        if _trong_ngoac(t) == can:
            return i
    return None
