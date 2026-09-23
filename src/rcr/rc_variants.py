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
