"""Cham dong "Nhan = gia tri" bang log cua tag da doc o buoc "Xem logcat tag ..." (tag_logcat).

Tim theo NHAN, khong theo gia tri ky vong (29/10/2026 AIP805: chi tim "1.2.9" khong thay roi ghi NOT_VERIFIABLE,
that ra build in "Version Lib Ads: 1.2.10" - phai ra FAIL kem gia tri that).
"""

from __future__ import annotations

import re

from .verdict_levels import FAIL, NEEDS_HUMAN, PASS, out

DONG_RE = re.compile(r"^\s*(?P<nhan>[^=:]{2,50}?)\s*[=:]\s*(?P<gt>.+?)\s*\.?\s*$")
# "SDK = visionlab:tutorial 3.6.1" -> so voi "Using version 3.6.1" cua tag FirstOpenSDK.
SDK_RE = re.compile(r"tutorial\s*v?(\d+(?:\.\d+)+(?:-\w+)?)", re.I)
USING_RE = re.compile(r"Using version\s+(\S+)", re.I)
TAG_SDK = "VslTemplate4FirstOpenSDK"


def _gia_tri_sau_nhan(nhan: str, dongs: list[str]) -> str | None:
    mau = re.compile(re.escape(nhan.strip()) + r"\s*[:=]\s*(.+)$", re.I)
    for d in dongs:
        m = mau.search(d)
        if m:
            return m.group(1).strip()
    return None


def cham(text: str, drive: dict) -> dict | None:
    tag_log = (drive or {}).get("tag_log") or {}
    if not tag_log:
        return None
    m = DONG_RE.match(text or "")
    if not m:
        return None
    nhan, mong = m.group("nhan").strip(), m.group("gt").strip()
    sdk = SDK_RE.search(mong)
    if sdk:
        thay = next((USING_RE.search(d).group(1) for d in tag_log.get(TAG_SDK, []) if USING_RE.search(d)), None)
        if thay is None:
            return out(NEEDS_HUMAN, f"log tag {TAG_SDK} không có dòng 'Using version'", "")
        v = PASS if thay == sdk.group(1) else FAIL
        return out(v, f"tag {TAG_SDK}: 'Using version {thay}' — kỳ vọng {sdk.group(1)}", thay)
    for tag, dongs in tag_log.items():
        thay = _gia_tri_sau_nhan(nhan, dongs)
        if thay is not None:
            v = PASS if thay.casefold() == mong.casefold() else FAIL
            return out(v, f"tag {tag}: '{nhan}: {thay}' — kỳ vọng {mong}", thay)
    if "=" not in text:
        return None             # "OB2: 'FR - OB2 title'" khong phai dong tag - luat khac cham
    return out(NEEDS_HUMAN, f"không thấy nhãn {nhan!r} trong log các tag đã đọc ({', '.join(tag_log)}; "
                            f"{sum(len(d) for d in tag_log.values())} dòng) — tester mode chưa bật?", "")
