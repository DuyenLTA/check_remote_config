"""Boc cap `key = value` tu van ban tu do cua file TC (Test Data / Precondition).

Moi bo TC viet mot kieu, phai doc duoc tat ca:
  - moi key mot dong, dong co danh so:   `1. a=true\n 2. b=false`
  - nhieu cap tren 1 dong:               `a = true, b = false` / `a = true; b = false.`
  - chu thich sau gia tri:               `"x, y" (default).` / `false (hoac chuoi rong).`
  - JSON nhieu dong, sau do la mo ta:    `cfg = {\n "type": "image"\n}\n2. New user...`
  - JSON khong chuan, co dau phay/`:`:   `{addWidgetDialog:{dialogBgColor:'#FF0000', ...}}`
KHONG loc key o day - whitelist key that cua app (rc_extract) moi la bo loc.
"""

from __future__ import annotations

import re

# Mui ten cac kieu tester hay dung cho runtime toggle / mo ta trang thai.
ARROWS = ("→", "->", "=>", "⇒")

# Tim UNG VIEN key (identifier bat ky, khong doi co '_': config that co key nhu
# `AppSettings`), roi `=`/`:`, roi gia tri toi truoc cap ke tiep. Cap ke tiep bat
# dau sau dau phay / cham phay / xuong dong / `(` / khoang trang - van xuoi kieu
# `(hoac pass_lfo_criteria = false)` phai boc duoc. Chu rac lot vao (`user: chua`)
# khong sao: whitelist loc.
_KEY = r"[A-Za-z][A-Za-z0-9_]*"
PAIR_RE = re.compile(
    rf"(?P<key>{_KEY})\s*[:=]\s*(?P<val>.*?)"
    rf"(?=(?:(?:[,;\n(]|\s)\s*(?:\d+\s*[.)]\s*)?{_KEY}\s*[:=])|$)",
    re.DOTALL,
)
OPEN, CLOSE = "[{", "]}"


def pairs(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    skip_to = 0
    for m in PAIR_RE.finditer(text):
        if m.start() < skip_to:
            continue  # cap gia nam ben trong JSON cua cap truoc
        start = m.start("val")
        if text[start:start + 1] in OPEN:
            end = _balanced_end(text, start)
            out[m.group("key")] = text[start:end]
            skip_to = end
        else:
            out[m.group("key")] = clean(m.group("val"))
    return out


def precondition_lines(text: str) -> str:
    """Bo dong co mui ten (mo ta trang thai, vd `high=true -> load fail`)."""
    return "\n".join(l for l in text.splitlines() if not any(a in l for a in ARROWS))


def clean(val: str) -> str:
    """Chuan hoa gia tri thanh dang RC luu (LUON la string).

    Giu chuoi rong: `""` phai ra `""` (khong duoc coi la 'khong co gia tri').
    """
    # Gia tri dung o cuoi dong: dong sau la mo ta (`true\n New user`)
    v = val.strip().split("\n", 1)[0].strip()
    # `true; luong FO ...`, `true, tat ca toggle ads` - sau `;`/`,` la mo ta.
    # Gia tri co dau phay that thi TC phai de trong nhay (`"result, exit_click"`).
    if v[:1] not in "\"'“":
        v = re.split(r"[;,]", v, maxsplit=1)[0].strip()
    prev = None
    while v != prev:
        prev = v
        v = v.rstrip(" .;,")  # dau cau ket thuc cau: `= false.`, `= true;`
        # Ngoac dong thua cua cau bao quanh: `(da xong lfo, pass_lfo_criteria=true)`
        while v.endswith(")") and v.count(")") > v.count("("):
            v = v[:-1].rstrip()
        # Chu thich trong ngoac don o cuoi: `false (mac dinh)`, `2 (default)`
        v = re.sub(r"\s*\([^()]*\)$", "", v).strip()
        # Ngoac MO ma khong dong: chu thich bi cat giua chung khi tach dong/dau
        # phay - `true (key tu SDK cu`. Khong cat la gia tri mang ca cau van xuoi.
        if v.count("(") > v.count(")"):
            v = v[:v.rindex("(")].rstrip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        return v[1:-1]
    if v.startswith("“") and v.endswith("”"):
        return v[1:-1]
    return v.lower() if v.lower() in ("true", "false") else v


def _balanced_end(text: str, start: int) -> int:
    """Vi tri ngay sau ngoac dong khop voi ngoac mo tai `start`.

    Khong dong duoc (TC viet thieu) -> het dong dau tien, de khong nuot mo ta.
    """
    depth, quote = 0, ""
    for i in range(start, len(text)):
        ch = text[i]
        if quote:
            if ch == quote and text[i - 1] != "\\":
                quote = ""
        elif ch in "\"'":
            quote = ch
        elif ch in OPEN:
            depth += 1
        elif ch in CLOSE:
            depth -= 1
            if depth == 0:
                return i + 1
    nl = text.find("\n", start)
    return len(text) if nl < 0 else nl
