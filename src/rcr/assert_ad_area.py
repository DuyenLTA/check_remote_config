"""Cham dong Expected noi ve VUNG AD tren man, khong noi ve so request.

Tach khoi `assert_ad_rules` (luat ve request/impression) vi hai thu tra loi
bang hai nguon khac nhau: file kia dem dong log, file nay hoi "man hinh co ad
nao cua vi tri do khong".

Hai dong hay gap trong bo TC OB2/OB3:
  "Phan ads khong load duoc de TRONG (khong blank trang vo layout, khong crash)"
  "Neu ad tra ve muon sau timeout: KHONG chen de gay nhay layout"
Dong dau truoc day roi vao luat "khong crash" - dung ket qua nhung sai ly do:
ve chinh cua cau (vung ad co trong khong) khong ai cham. Dong sau roi xuong
"phai nhin mat" du no do duoc.
"""

from __future__ import annotations

import re

from .verdict_levels import CONFIG_BLOCKED, FAIL, PASS, out

# "Phan ads ... de TRONG", "vung ad de trong", "vung ad trong"
VUNG_TRONG_RE = re.compile(
    r"(?:v[ùu]ng|ph[ầa]n)\s+ads?\b.{0,40}?(?:tr[ốo]ng|kh[ôo]ng\s+load)"
    r"|(?:v[ùu]ng|ph[ầa]n)\s+ads?\s+tr[ốo]ng",
    re.I,
)
# Cau co dieu kien: "Neu ad tra ve muon sau timeout: KHONG chen de..."
DIEU_KIEN_RE = re.compile(r"^\s*(?:n[ếe]u|if)\b\s*(.{3,70}?)\s*(?::|th[ìi]\b)", re.I)
# Dieu kien noi ve viec ad tra ve / load duoc.
AD_VE_RE = re.compile(r"ad\b.{0,24}(?:tr[ảa]\s*v[ềe]|v[ềe]\s*mu[ộo]n|load)"
                      r"|(?:tr[ảa]\s*v[ềe]|load).{0,12}\bad\b", re.I)
NO_CRASH_RE = re.compile(r"kh[oô]ng\s+(?:b[ịi]\s+)?crash", re.I)


def _cua_case(units, vi_tri, khop):
    """Cac unit thuoc vi tri ma CHINH case nay bat/tat."""
    if not vi_tri:
        return list(units)
    return [u for u in units if any(khop(u, t) for t in vi_tri)]


def vung_trong(text: str, units, actual: dict, crash: dict, vi_tri, khop) -> dict:
    """"Vung ad de TRONG" - do bang: co unit nao cua vi tri do show khong.

    Kem luon ve "khong crash" neu cau co nhac: tra PASS cho ca cau trong khi
    app vua crash la sai han.
    """
    thuoc = _cua_case(units, vi_tri, khop)
    hien = [u["unit"] for u in thuoc if u["shown"]]
    if hien:
        return out(FAIL, f"vùng ad KHÔNG trống — {', '.join(hien)} đã show",
                   actual | {"shown": hien})
    if NO_CRASH_RE.search(text) and crash.get("crashed"):
        return out(FAIL, "app crash trong lượt chạy", crash.get("lines", [])[:3])
    xin = sum(u["requested"] for u in thuoc)
    ten = ", ".join(sorted(vi_tri)) if vi_tri else "vị trí của case"
    them = ", không crash" if NO_CRASH_RE.search(text) else ""
    if not thuoc:
        return out(PASS, f"không unit nào của {ten} chạy lượt này nên vùng ad trống{them}",
                   actual)
    return out(PASS, f"{xin} request cho {ten} nhưng không unit nào show — "
                     f"vùng ad trống đúng kỳ vọng{them}", actual)


def dieu_kien_ad(text: str, units, actual: dict, vi_tri, khop) -> dict | None:
    """Cau "Neu ad tra ve muon...": tien de co xay ra trong luot nay khong.

    Tien de khong xay ra thi KHONG duoc bao PASS - luot chay nay khong chung
    minh duoc gi ve hanh vi do. BLOCKED moi dung: chay lai voi dieu kien ep
    duoc thi se co ket luan.
    """
    m = DIEU_KIEN_RE.match(text)
    if not m or not AD_VE_RE.search(m.group(1)):
        return None
    thuoc = _cua_case(units, vi_tri, khop)
    if any(u["loaded"] or u["shown"] for u in thuoc):
        return None  # tien de CO xay ra -> de luat khac cham ve con lai
    ten = ", ".join(sorted(vi_tri)) if vi_tri else "vị trí của case"
    return out(CONFIG_BLOCKED,
               f"điều kiện “{m.group(1)}” không xảy ra: không unit nào của {ten} "
               "load được trong lượt này nên không có gì để chèn đè — cần ép ad "
               "trả về muộn mới kiểm được", actual)
