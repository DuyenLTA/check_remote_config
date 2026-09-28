"""Nhung dau hieu buoc `rc_extract` phai danh NEEDS_HUMAN thay vi doan.

Tach khoi `rc_extract` de moi file duoi 200 dong. `rc_extract` noi TRINH TU boc
key; file nay noi tung dau hieu "cho nay khong duoc doan" trong ra sao.
"""

from __future__ import annotations

import re

from . import rc_unit_codes

# Chuoi gia tri noi bang mui ten: `true -> false -> true`, `OFF -> ON -> OFF`.
# Doi it nhat HAI gia tri that: "ON 102-spl-n-inter-high1 -> load & show" cung co
# mui ten nhung ve sau khong phai gia tri, do la cau ta ket qua.
TOGGLE_RE = re.compile(
    r"\b(?:true|false|on|off)\b\s*(?:->|→|=>)\s*\b(?:true|false|on|off)\b", re.I)
# Gia tri la cho trong chua dien: `<id template dang test>`, `<gia tri tuong ung>`
PLACEHOLDER_RE = re.compile(r"<[^<>]*>")
# Key co dau '.' -> sua field trong JSON (vd restore.enable)
DOTTED_RE = re.compile(r"\b[A-Za-z][\w]*\.[A-Za-z][\w]*\s*[:=]")
# Tu chi quang cao trong van xuoi cua Precondition.
AD_WORDS_RE = re.compile(
    r"native|banner|inter|reward|app\s*open|\baoa\b|\bads?\b|quảng\s*cáo|quang\s*cao", re.I)
# Gia tri bat/tat. CHI cap dang nay moi la mot cong tac: `source = ads_screen` co
# chu "ads" nhung khong tat gi ca, con `OB2 = OFF` thi co.
ONOFF_RE = re.compile(r"^(?:on|off|true|false|bật|bat|tắt|tat|enable|disable)$", re.I)


def cong_tac_ads_chua_map(text: str, found: dict, ignored, whitelist) -> list[str]:
    """Ve van xuoi bat/tat mot vi tri quang cao ma key khong thuoc RC cua app.

    `Remote native OB2 = OFF` boc ra cap `OB2 = OFF`; `OB2` khong phai key nen
    bi whitelist loai, va truoc day loai IM LANG. Case van chay - tren may quang
    cao OB2 con bat - roi bi cham FAIL vi "van co request native". Do that
    2026-09-25, case 3.5.0#20: FAIL do tool khong dat duoc dieu kien, khong phai
    app sai. Tha bao can nguoi con hon bao sai cho dev.
    """
    out = []
    for key in ignored:
        if not ONOFF_RE.match(found.get(key, "")):
            continue
        for ve in re.split(r"[\n;]", text):
            if not re.search(rf"\b{re.escape(key)}\b", ve) or not AD_WORDS_RE.search(ve):
                continue
            # Ve viet unit theo ma (`unit 102-spl-n-inter-high1 = true`) da duoc
            # rc_unit_codes doi thanh key that; cap rac `high1 = true` cat ra tu
            # chinh no khong phai mot cong tac bo sot.
            if rc_unit_codes.pairs(ve, whitelist):
                continue
            out.append(ve.strip())
            break
    return out


def mentioned(text: str, whitelist) -> set[str]:
    """Key cua app xuat hien nhu mot tu rieng trong van ban."""
    words = set(re.findall(r"[A-Za-z][A-Za-z0-9_]*", text))
    return words & set(whitelist)
