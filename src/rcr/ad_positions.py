"""Vi tri ads: doc ma vi tri tu cau TC, va khop mot unit ve vi tri.

Tach khoi `assert_ads` de moi file duoi 200 dong: `assert_ads` phan loai cau
Expected va goi luat cham, file nay chi tra loi "cau/case nay noi ve vi tri
nao" va "unit nay co thuoc vi tri do khong".
"""

from __future__ import annotations

import re

# Ma vi tri ads trong TC: 101-spl-a-banner, 105-spl-n-native-high, "tren splash"...
POSITION_RE = re.compile(r"\b\d{3}\b|splash|home|onboarding|lfo|ob\d|result|tab\s+\w+", re.I)
# Ma vi tri (202, 304...) khong kem chu "native"/"inter" -> tra loai tu TEN
# KEY RC THAT cua app (`show_202_lfo2_n_native_high` -> native). Du lieu that,
# khong phai bang tu doan.
POS_CODE_RE = re.compile(r"\b(\d{3})\b")
# Ma day du trong cau TC: "303-onb3-n-native-high1" -> khop key RC
# `id_303_onb3_n_native_high1`. Chi co 3 so ("105", "tren splash") thi lay so.
TC_CODE_RE = re.compile(r"\b\d{3}(?:-[a-z0-9]+)+", re.I)


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



def da_biet(token: str, biet) -> bool:
    """Vi tri `token` co ID da biet khong. "302" phai khop `302_onb2_n_native`:
    so nguyen van thi vi tri viet tat KHONG BAO GIO khop, dong phu dinh ve 302
    thanh khong cham duoc du bang ID co du (do 2026-10-06, OB2-002/008).
    """
    sau = re.compile(r"(?<![a-z0-9])" + re.escape(token) + "(?![a-z0-9])")
    return bool(token) and any(sau.search(p.lower()) for p in biet)


def case_position(lines) -> str:
    """Vi tri unit ma CA case noi toi, "" neu cac dong noi ve nhieu vi tri.

    Dong "Impressions = 0" khong tu nhac ten unit; ten no nam o dong Expected
    phia tren cua cung case. Chi nhan khi CA khoi Expected noi ve DUNG MOT vi
    tri - nhieu vi tri thi lay cai nao cung la doan.
    """
    tokens = {t for t in (_position_token(l or "") for l in lines) if t}
    return tokens.pop() if len(tokens) == 1 else ""



def vi_tri_cua_case(overrides) -> tuple[str, ...]:
    """Cac vi tri ads ma case nay bat/tat, suy tu ten key da dat.

    Cau phu dinh trong bo TC hay viet chung chung ("App KHONG request native
    ad") va khong nhac ma vi tri nao. Ma vi tri nam o KEY case dat
    (`show_302_onb2_n_native_high`), do moi la thu case dang noi toi. Khong lay
    thi moi request cua vi tri KHAC - 301/303 preload cho man sau - deu bi tinh
    la loi (do that 2026-09-28, case 20 FAIL oan).
    """
    ra = set()
    for key in overrides or ():
        m = re.match(r"(?:show|enable|id)_(\d{3}_.+)$", key)
        if m:
            ra.add(m.group(1))
    return tuple(sorted(ra))
