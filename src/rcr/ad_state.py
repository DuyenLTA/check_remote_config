"""Ep trang thai load cua 1 vi tri ad bang cach doi ID ad trong Remote Config.

File TC ghi dieu kien kieu `102-spl-n-inter-high: fail`, `105-spl-n-native: loaded`.
Tester lam tay bang Ad Inspector (lac may -> chon nguon Meta) - khong phai app nao
cung co nguon Meta. Tool lam theo TUNG unit: dat key RC chua ID ad thanh
  - fail   -> ID sai: request chac chan loi
  - loaded -> ID test Google cung loai ad: chac chan co fill
Da do: high = ID sai -> onAdFailedToLoad -> fallback unit thuong (ID test) loaded.

Ky hieu -> key LAY TU BANG DA DO (`data/ad_id_keys.yaml`), khong suy tu ten: key
`id_<vi_tri>` co trong RC chua chac SDK doc. Vi tri chua co trong bang -> tra ve
`unresolved` de case danh NEEDS_HUMAN, khong doan.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

MARKER_RE = re.compile(r"\b(\d{3}(?:-[a-z0-9]+)+)\s*:\s*(fail|failed|loaded)\b", re.I)
# Moi cho co trang thai - de bat ky hieu viet tat MARKER_RE khong doc duoc
STATE_RE = re.compile(r":\s*(?:fail|failed|loaded)\b", re.I)
INVALID_ID = "ca-app-pub-0000000000000000/0000000000"
# ID test chinh thuc cua Google theo loai ad (developers.google.com/admob/android/test-ads)
TEST_IDS = {
    "inter": "ca-app-pub-3940256099942544/1033173712",
    "native": "ca-app-pub-3940256099942544/2247696110",
    "banner": "ca-app-pub-3940256099942544/9214589741",
}
DATA = Path(__file__).parent / "data" / "ad_id_keys.yaml"


def find(text: str) -> dict[str, str]:
    """{ky_hieu: 'fail'|'loaded'} theo thu tu xuat hien."""
    out: dict[str, str] = {}
    for m in MARKER_RE.finditer(text):
        state = m.group(2).lower()
        out[m.group(1).lower()] = "fail" if state.startswith("fail") else "loaded"
    return out


def unreadable(text: str) -> list[str]:
    """Dong co `: fail`/`: loaded` ma khong doc ra ky hieu (vd `102-n-high/high1: fail`).

    Bo qua im lang la chay case KHONG ep ad -> ket qua sai ma khong ai biet.
    """
    return [l.strip() for l in text.splitlines()
            if len(STATE_RE.findall(l)) > len(MARKER_RE.findall(l))]


def resolve(markers: dict[str, str], whitelist) -> tuple[dict[str, str], list[str]]:
    """-> (overrides ID ad, ky hieu `fail` khong ep duoc)."""
    table = _table()
    overrides: dict[str, str] = {}
    unresolved: list[str] = []
    for marker, state in markers.items():
        key = table.get(marker)
        kind = _kind(marker)
        if not key or key not in whitelist or (state == "loaded" and not kind):
            # `loaded` khong ep duoc van chay: ban debug dung ID test, ad tu fill.
            # Phase cham phai thay unit do loaded trong log, khong thi BLOCKED.
            if state == "fail":
                unresolved.append(marker)
            continue
        overrides[key] = INVALID_ID if state == "fail" else TEST_IDS[kind]
    return overrides, unresolved


def _kind(marker: str) -> str:
    for kind in TEST_IDS:
        if kind in marker:
            return kind
    return ""


@lru_cache(maxsize=1)
def _table() -> dict[str, str]:
    import yaml

    data = yaml.safe_load(DATA.read_text(encoding="utf-8")) or {}
    return {str(k).lower(): str(v) for k, v in (data.get("markers") or {}).items()}
