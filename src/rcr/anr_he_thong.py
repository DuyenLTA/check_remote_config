"""Dong hop thoai ANR cua tien trinh HE THONG ("System Launcher isn't responding") dang che man app.

OPPO f3466cdb 18/11/2026: launcher ANR luc 22:00 (Input dispatching timed out), hop thoai nam tren man suot lượt
AIP936 sau do - anh tung buoc deu bi che, tap cua tool roi vao hop thoai -> case BLOCKED roi phai chay lai. ANR cua
launcher / systemui khong phai loi app dang test nen bam "Wait" de man app hien lai. ANR cua CHINH app (hay app thu
ba khac) thi KHONG dong: do la ket qua, cham bang logcat `am_anr` va anh phai giu nguyen.
"""

from __future__ import annotations

import re

from .ui_dump import parse_bounds

# Tien trinh he thong: hop thoai cua chung chi la nhieu cua may, khong phai ket qua cua app.
TIEN_TRINH_HE_THONG = re.compile(
    r"^(android|system|com\.android\.|com\.google\.android\.(apps\.nexuslauncher|gms)|com\.oppo\.|com\.coloros\.|"
    r"com\.oplus\.|com\.heytap\.|com\.miui\.|com\.xiaomi\.|com\.sec\.|com\.samsung\.|com\.vivo\.|com\.bbk\.|"
    r"com\.huawei\.|com\.realme\.|com\.transsion\.|com\.motorola\.)")
_ANR_FOCUS_RE = re.compile(r"Application Not Responding: ([\w.:]+)")
TIEU_DE_ANR = re.compile(r"isn.t responding|not responding|không phản hồi|không phản ứng", re.I)
NUT_DOI = re.compile(r"^(wait|đợi|chờ)$", re.I)


def co_hop_thoai_anr(xml: str) -> bool:
    """Dump UI co dang hop thoai "... isn't responding" khong (kiem re, khong goi adb)."""
    return bool(xml) and ("aerr_wait" in xml or bool(TIEU_DE_ANR.search(xml)))


def tien_trinh_anr(dumpsys_window: str) -> str:
    """Ten tien trinh dang ANR tu cua so focus ("Application Not Responding: com.oppo.launcher"); khong co -> ""."""
    m = _ANR_FOCUS_RE.search(dumpsys_window or "")
    return m.group(1).split(":")[0] if m else ""


def la_he_thong(tien_trinh: str) -> bool:
    return bool(tien_trinh) and bool(TIEN_TRINH_HE_THONG.match(tien_trinh))


def diem_nut_doi(xml: str) -> tuple[int, int] | None:
    """Tam nut "Wait" cua hop thoai ANR trong dump; khong thay -> None."""
    for m in re.finditer(r"<node\b[^>]*>", xml or ""):
        the = m.group(0)
        rid = re.search(r'resource-id="([^"]*)"', the)
        text = re.search(r'text="([^"]*)"', the)
        bounds = re.search(r'bounds="([^"]*)"', the)
        if not bounds:
            continue
        if (rid and rid.group(1).endswith("aerr_wait")) or (text and NUT_DOI.match(text.group(1).strip())):
            return parse_bounds(bounds.group(1)).center
    return None


async def dong_neu_he_thong(client, serial: str, xml: str) -> str:
    """Hop thoai ANR trong `xml` la cua tien trinh he thong -> bam Wait, tra ten tien trinh; khong thi ""."""
    if not co_hop_thoai_anr(xml):
        return ""
    try:
        out, _, _ = await client.shell(serial, "dumpsys", "window", "windows")
    except Exception:                      # noqa: BLE001 - khong doc duoc cua so thi de nguyen
        return ""
    tt = tien_trinh_anr(out)
    diem = diem_nut_doi(xml)
    if not la_he_thong(tt) or diem is None:
        return ""
    await client.shell(serial, "input", "tap", str(diem[0]), str(diem[1]))
    return tt
