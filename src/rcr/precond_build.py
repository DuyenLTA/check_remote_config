"""Precondition doi build / dieu kien ngoai ma ban release tren may khong co -> BLOCKED ngay, khong reset may.

TC SDK 3.7.3 (viet lai 19/11/2026) ghi ro o Precondition: "Can build Dev ...", "Can build debug (fetch interval = 0)",
"Can mang cham hoac build Dev ...", "Can PO/Dev chi key ...", "Dev kiem bang code ...". Chay cac case nay tren ban
release la ton 2-4 phut / case (pm clear + lai FO) roi van khong tao duoc dieu kien - va chay duoi trang thai tu
nhien thi con ra PASS/FAIL gia (luat: thieu dieu kien la BLOCKED, khong do thay).

`co_build_dev`: QA da cai build Dev / debug len may (`--co-build-dev`) -> case can build (ke ca "mang cham HOAC
build Dev") van chay; "PO/Dev chi key", "Dev kiem bang code" khong phai build nen van chan.
"""

from __future__ import annotations

import re

CAN_BUILD_RE = re.compile(r"c[ầa]n\s+build\s+(?:dev|debug)\b", re.I)
MANG_CHAM_RE = re.compile(r"c[ầa]n\s+m[ạa]ng\s+ch[ậa]m", re.I)
HOAC_BUILD_RE = re.compile(r"ho[ặa]c\s+build\s+(?:dev|debug)\b", re.I)
CAN_NGUOI_RE = re.compile(r"c[ầa]n\s+(?:PO\s*/\s*)?dev\s+ch[ỉi]\s+key|dev\s+ki[ểe]m\s+b[ằa]ng\s+code", re.I)
GOI_Y = " — chưa có trên máy (đã cài build thì chạy lại với --co-build-dev)"


def _cau(text: str, m: re.Match) -> str:
    """Nguyen dong chua cho khop (bo so thu tu dau dong), de report noi ro thieu gi."""
    dau = text.rfind("\n", 0, m.start()) + 1
    cuoi = text.find("\n", m.end())
    return re.sub(r"^\s*\d+\.\s*", "", text[dau:cuoi if cuoi >= 0 else len(text)]).strip().rstrip(".")


def thieu_build(precondition: str, co_build_dev: bool = False) -> list[str]:
    """Ly do case khong chay duoc tren may / ban nay; [] neu khong doi gi dac biet."""
    text = precondition or ""
    ra: list[str] = []
    m = CAN_BUILD_RE.search(text)
    if m and not co_build_dev:
        ra.append(_cau(text, m) + GOI_Y)
    m = MANG_CHAM_RE.search(text)
    if m:
        cau = _cau(text, m)
        if not (co_build_dev and HOAC_BUILD_RE.search(cau)):
            ra.append(cau + ("" if HOAC_BUILD_RE.search(cau) is None else GOI_Y))
    m = CAN_NGUOI_RE.search(text)
    if m:
        ra.append(_cau(text, m))
    return list(dict.fromkeys(ra))
