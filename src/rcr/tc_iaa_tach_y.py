"""Tach tung y cua cot Ad description (bo IAA) thanh dong Expected rieng de khong bo sot y nao.

User chot 17/11/2026: check ki TAT CA y trong cot Ad description - moi vi tri preload, moi man hien thi, thoi gian
reload, tung su kien reload, tung key... Mot dong sheet hay gop nhieu y ("Hien thi banner tai chan man A, B, C, D";
"Reload khi user hide app, click vao ad hoac tro ve tu man ads") -> cham ca dong de chi do mot man roi PASS.
Giu NGUYEN VAN dong goc (luat 12/11/2026), them sau no moi y mot dong `↳ ...` - moi dong la mot ket luan rieng.
"""

from __future__ import annotations

import re

MUI_TEN = "↳ "
# Tu dan vao danh sach (man / su kien / key): lay lan xuat hien CUOI trong ve dau.
TU_DAN_RE = re.compile(r"(?:các màn|màn|screens?|ở|tại|dưới|khi|:)\s+", re.I)
DAI_TOI_DA = 120          # y dai hon -> la cau van, khong phai mot muc cua danh sach
# Muc sau co dong tu ads (load / show / khi / =>) -> dong la cau van nhieu ve, khong phai danh sach man / su kien:
# giu nguyen dong, Claude tu tach ve khi cham (doan tien to se ra cau sai nghia).
CAU_VAN_RE = re.compile(r"load\b|\bshow\b|hiển thị|=>|\bkhi\b", re.I)


def _bo_ngoac(s: str) -> str:
    """Thay noi dung trong ngoac bang dau cach (giu do dai) - tu dan / dong tu trong ngoac khong tinh."""
    ra, sau = [], 0
    for ch in s:
        sau += ch == "("
        ra.append(ch if sau == 0 else " ")
        sau -= ch == ")" and sau > 0
    return "".join(ra)


def tach_phay(s: str) -> list[str]:
    """Tach theo `,` ngoai ngoac: 'A (x, y), B' -> ['A (x, y)', 'B']."""
    ra, sau, buf = [], 0, []
    for ch in s:
        sau += (ch == "(") - (ch == ")")
        if ch == "," and sau == 0:
            ra.append("".join(buf).strip())
            buf = []
        else:
            buf.append(ch)
    ra.append("".join(buf).strip())
    return [x for x in ra if x]


def _tach_hoac(muc: str) -> list[str]:
    """'click vao ad hoac tro ve tu man ads' -> hai su kien rieng (ngoai ngoac)."""
    return [x.strip() for x in re.split(r"\s+hoặc\s+(?![^()]*\))", muc) if x.strip()]


def y_cua_dong(dong: str) -> list[str]:
    """Mot dong mo ta -> cac y con (rong neu dong chi co mot y)."""
    phan = tach_phay(dong)
    if len(phan) < 2:
        return []
    dan = list(TU_DAN_RE.finditer(_bo_ngoac(phan[0])))
    if not dan:
        return []
    cuoi = dan[-1].end()
    tien_to, dau = phan[0][:cuoi], phan[0][cuoi:].strip()
    muc = [dau, *phan[1:]] if dau else phan[1:]
    if any(CAU_VAN_RE.search(_bo_ngoac(m)) for m in phan[1:]):
        return []
    muc = [y for m in muc for y in _tach_hoac(m)]
    if len(muc) < 2 or any(len(m) > DAI_TOI_DA for m in muc):
        return []
    return [f"{MUI_TEN}{tien_to}{m}" for m in muc]


def ve_cau_van(dong: str) -> list[str]:
    """Cau van nhieu ve (khong phai danh sach): tach theo `,` / `=>` ngoai ngoac -> cac ve; mot ve thi rong."""
    ve = [v.strip() for p in tach_phay(dong) for v in p.split("=>") if v.strip()]
    return ve if len(ve) >= 2 else []


def dong_expected(mo_ta: str) -> list[str]:
    """Moi dong khong trong (nguyen van) + ngay sau no tung y con cua dong do."""
    ra: list[str] = []
    for d in (x.strip() for x in (mo_ta or "").splitlines()):
        if d:
            y = y_cua_dong(d)
            ve = [] if y else ve_cau_van(d)
            # Cau van: khong doan tien to (ra cau sai nghia) - mot dong nhac du tung ve, ve nao chua do thi khong PASS.
            ra += [d, *y, *([f"{MUI_TEN}Đủ từng vế (vế nào chưa đo được thì không PASS): " + " | ".join(ve)] if ve else [])]
    return ra
