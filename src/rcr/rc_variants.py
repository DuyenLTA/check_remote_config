"""Gia tri lua chon trong Test Data -> nhieu luot chay.

`layout1/2/3`, `layout1/layout2`, `layout1 / layout2` = "mot trong cac gia tri",
khong phai gia tri that - patch nguyen chuoi la ghi rac vao config. Nhan ra moi
gia tri mot luot; nhieu key lua chon -> tich Descartes.
"""

from __future__ import annotations

import itertools
import re

# ID AdMob `ca-app-pub-<pub>/<unit>` cung co '/' nhung la 1 gia tri. URL co `://`.
CHOICES_RE = re.compile(r"(?!ca-app-pub-)[\w.-]+(?:\s*/\s*[\w.-]+)+")
MAX_VARIANTS = 16  # qua muc nay la TC viet nham, khong tu no ra hang chuc luot


def split(overrides: dict[str, str]) -> tuple[dict[str, str], tuple[dict[str, str], ...], str]:
    """-> (key gia tri don, cac to hop key lua chon, ly do tu choi neu qua nhieu)."""
    choices = {k: expand(v) for k, v in overrides.items() if CHOICES_RE.fullmatch(v)}
    if not choices:
        return overrides, (), ""
    keys = list(choices)
    combos = list(itertools.product(*(choices[k] for k in keys)))
    if len(combos) > MAX_VARIANTS:
        return {}, (), f"{len(combos)} to hop gia tri - qua {MAX_VARIANTS}, tach case trong file TC"
    rest = {k: v for k, v in overrides.items() if k not in choices}
    return rest, tuple(dict(zip(keys, c)) for c in combos), ""


def expand(val: str) -> list[str]:
    """`layout1/2/3` -> [layout1, layout2, layout3]; phan chi co so muon tien to phan dau."""
    parts = [p.strip() for p in val.split("/")]
    prefix = re.sub(r"\d+$", "", parts[0])
    return [prefix + p if p.isdigit() else p for p in parts]


# --- quy uoc cua bo TC 3.5.0 (sheet "Automation Convention") ------------------

# `key=<absent>`: server KHONG tra key -> xoa key khoi config va khoi mirror.
ABSENT = "<absent>"
# `key=v1 | v2`: chay case 2 lan, moi lan 1 gia tri.
PIPE = "|"
ARROW_RE = re.compile(r"\s*(?:→|->|=>|⇒)\s*")
# Ghi chu "(doi khi app dang chay)": doi config luc app CON CHAY - tool chi doi
# duoc bang cach tat app roi mo lai, tai hien khong dung -> khong chay.
DANG_CHAY_RE = re.compile(r"đang\s*chạy|dang\s*chay|while\s+running|at\s+runtime", re.I)
GHI_CHU_RE = re.compile(r"\s*\([^()]*\)\s*$")


def _gia_tri(part: str) -> str:
    """Bo khoang trang va dau nhay boc ngoai: `"abc"` -> abc, `""` -> rong."""
    part = GHI_CHU_RE.sub("", part).strip()
    if len(part) >= 2 and part[0] == part[-1] and part[0] in "\"'":
        return part[1:-1]
    return part


def split_pipe(overrides: dict[str, str]) -> tuple[dict[str, str], tuple[dict[str, str], ...]]:
    """`null | <absent>` -> moi gia tri mot luot. Nhieu key co `|` -> tich Descartes."""
    choices = {k: [_gia_tri(p) for p in v.split(PIPE)] for k, v in overrides.items()
               if PIPE in v and not ARROW_RE.search(v)}
    if not choices:
        return overrides, ()
    keys = list(choices)
    rest = {k: v for k, v in overrides.items() if k not in choices}
    return rest, tuple(dict(zip(keys, c)) for c in itertools.product(*choices.values()))


def split_runtime(overrides: dict[str, str]) -> tuple[dict[str, str], tuple[dict[str, str], ...], str]:
    """`a → b → c` -> chuoi luot CO THU TU: luot i dat gia tri thu i.

    Khac voi gia tri lua chon: giua cac luot KHONG reset app - chi doi config,
    tat app, mo lai. Do la cai case runtime hoi (app co nhan gia tri moi khi
    van con cache cu khong). Nhieu key co mui ten thi so buoc phai bang nhau.
    """
    seqs = {k: [_gia_tri(p) for p in ARROW_RE.split(v)] for k, v in overrides.items()
            if ARROW_RE.search(v)}
    if not seqs:
        return overrides, (), ""
    if any(DANG_CHAY_RE.search(v) for k, v in overrides.items() if k in seqs):
        return {}, (), ("runtime toggle (doi gia tri khi app dang chay) - tool chi doi "
                        "config bang cach tat app roi mo lai, khong tai hien duoc luc app dang chay")
    lens = {len(s) for s in seqs.values()}
    if len(lens) > 1:
        return {}, (), ("cac key runtime co so buoc khac nhau: "
                        + ", ".join(f"{k} ({len(s)} buoc)" for k, s in seqs.items()))
    rest = {k: v for k, v in overrides.items() if k not in seqs}
    n = lens.pop()
    return rest, tuple({k: s[i] for k, s in seqs.items()} for i in range(n)), ""
