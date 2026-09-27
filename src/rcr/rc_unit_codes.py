"""Ma vi tri ads trong cau TC -> cap `show_<ma> = gia tri`.

Bo TC dung chung viet key theo MAU, khong viet ten that:

    "4. Remote config tat unit 102-spl-n-inter-high1 (key show_* tuong ung) = false."

Tim cap `key = value` thi khong thay gi, roi ca case bi gat sang "khong co key
nao thuoc remote config" - gat oan 13/16 case cua tab 3.5.0 (do that 2026-09-25).

DAY KHONG PHAI DOAN TEN: ten suy ra chi duoc nhan khi no CO TRONG whitelist key
doc that tu may. Suy ra ma may khong co key do -> bo, khong dat gi ca. Sau do
dex_check van gac tiep: key app khong doc -> KEY_NOT_USED, khong ra PASS gia.

Gia tri lay tu chinh cau, KHONG co mac dinh: uu tien `= true/false` dung ngay
sau ma, khong co thi doc chu `tat`/`bat` cua ve cau truoc ma. Khong doc duoc
gia tri thi khong nhan cap do - dat bua mot nua case la sai ma khong ai biet.
"""

from __future__ import annotations

import re

# "102-spl-n-inter-high1" -> key `show_102_spl_n_inter_high1`
CODE_RE = re.compile(r"\b\d{3}(?:-[a-z0-9]+)+", re.I)
VALUE_RE = re.compile(r"[=:]\s*(true|false)\b", re.I)
# Chi nhan tu khoa ro rang. "on"/"off" thuong trong van xuoi tieng Anh de dinh
# nham nen doi ON/OFF viet hoa dung nhu trong TC.
OFF_RE = re.compile(r"t[ắa]t|\bOFF\b|disable")
ON_RE = re.compile(r"b[ậa]t|\bON\b|enable")


def pairs(text: str, whitelist) -> dict[str, str]:
    """Cap key/value suy ra duoc tu cac ma vi tri trong `text`."""
    found: dict[str, str] = {}
    for line in (text or "").splitlines():
        for key, value in _trong_dong(line, whitelist):
            found.setdefault(key, value)
    return found


def _trong_dong(line: str, whitelist):
    ma = list(CODE_RE.finditer(line))
    for i, m in enumerate(ma):
        key = "show_" + m.group(0).replace("-", "_").lower()
        if key not in whitelist:
            continue
        # Chi doc trong khoang tu sau ma nay toi ma ke tiep: mot dong co the
        # ke hai vi tri voi hai gia tri khac nhau.
        het = ma[i + 1].start() if i + 1 < len(ma) else len(line)
        gia_tri = VALUE_RE.search(line[m.end():het])
        if gia_tri:
            yield key, gia_tri.group(1).lower()
            continue
        truoc = line[:m.start()]
        if OFF_RE.search(truoc):
            yield key, "false"
        elif ON_RE.search(truoc):
            yield key, "true"
