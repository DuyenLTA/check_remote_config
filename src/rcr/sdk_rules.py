"""Soat case TC theo luat SDK truoc khi chay (`data/sdk_rules.yaml`).

Case mau thuan luat SDK (vd chi bat `_high` ma key thuong dang tat, lai ky vong
ad hien) chay ra FAIL nhung loi nam o TC, khong phai app. Bao truoc de tester
sua TC, thay vi chay roi doc FAIL gia.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

from .models import Case, RcCaseData

DATA = Path(__file__).parent / "data" / "sdk_rules.yaml"
HIGH_RE = re.compile(r"^(show_(\d{3})_.+?)_high\d*$")
NEGATIVE_RE = re.compile(r"\bkhông\b|\bkhong\b|\bnot\b|\bno\b", re.I)


def lint(case: Case, data: RcCaseData, baseline: dict[str, str]) -> list[str]:
    """Canh bao cho tung luot chay cua case (rong = khong thay mau thuan)."""
    out: list[str] = []
    for rule in rules():
        if rule.get("kind") == "master_switch":
            out += _master_switch(case, data, baseline, rule)
        elif rule.get("kind") == "key_sai":
            out += _wrong_key(data, rule)
    return list(dict.fromkeys(out))


@lru_cache(maxsize=1)
def rules() -> tuple[dict, ...]:
    import yaml

    return tuple((yaml.safe_load(DATA.read_text(encoding="utf-8")) or {}).get("rules") or ())


def _master_switch(case: Case, data: RcCaseData, baseline: dict[str, str], rule: dict) -> list[str]:
    # Chi vi tri da do dung luat - vi tri khac co the bat/tat tung tier (vd 202)
    positions = {str(p) for p in rule.get("vi_tri") or ()}
    # Case co y test "tat" (moi dong ky vong deu phu dinh) -> khong phai mau thuan
    if case.expects and all(NEGATIVE_RE.search(e) for e in case.expects):
        return []
    out = []
    for run in data.runs:
        for key, val in run.items():
            m = HIGH_RE.match(key)
            if not m or val != "true":
                continue
            normal = m.group(1)
            if m.group(2) not in positions or normal not in baseline:
                continue  # app khong co key thuong -> khong ap duoc luat
            effective = run.get(normal, baseline[normal])
            if effective == "false":
                src = "case dat" if normal in run else "mac dinh cua app"
                out.append(
                    f"[{rule['id']}] {key}=true nhung {normal}={effective} ({src}) -> "
                    f"SDK tat ca vi tri, ad se khong hien. Them `{normal}=true` vao Precondition "
                    "neu case muon thay ad."
                )
    return out


def _wrong_key(data: RcCaseData, rule: dict) -> list[str]:
    """Case dat key spec khong co (app khong doc) -> ket qua chay vo nghia."""
    if not any(rule["key"] in run for run in data.runs):
        return []
    return [f"[{rule['id']}] key `{rule['key']}` khong ton tai theo spec -> dung {rule['thay_bang']}. "
            f"Nguon: {rule['nguon']}"]
