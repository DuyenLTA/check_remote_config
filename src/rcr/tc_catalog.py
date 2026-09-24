"""Chon bo testcase theo ban SDK cua app, tu workbook nhieu tab.

Workbook TC SDK (1 tab / version) to chuc:
  - BASE: `TC SDK 6.4.0` - luong Splash -> OB5 day du (spec tutorial 3.0.2).
    "6.4.0" la so hieu noi bo cua bo base, KHONG so thu tu voi dong 3.x.
  - DELTA: `TC SDK 3.2.0`, `3.3.0`, ... - moi tab chi ghi phan thay doi so voi ban
    truoc. App o ban X can base + moi delta <= X.
  - TINH NANG: `TC SDK rating`, `widget`, `daily checkin` - SDK rieng, chi lay khi
    app co key cua tinh nang do (app khong tich hop thi moi case deu khong co key).
Lay version theo TEN TAB, khong theo dong `Spec:` dau tab: tab 3.2.0 ghi spec 3.0.2.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from . import rc_extract, tc_loader
from .models import Case, RcError

TAB_RE = re.compile(r"^\s*TC SDK\s+(.+?)\s*$", re.I)
VERSION_RE = re.compile(r"(\d+)\.(\d+)\.(\d+)")
SDK_LOG_RE = re.compile(r"VslTemplate4FirstOpenSDK[^:\n]*:\s*Using version\s+(\S+)")
BASE_TAB = "TC SDK 6.4.0"
DELTA_MAJOR = 3  # dong SDK tutorial hien hanh


@dataclass
class Tab:
    name: str
    kind: str  # base | delta | feature
    version: tuple[int, int, int] | None
    cases: list[Case] = field(default_factory=list)


def sdk_version(log_text: str) -> str:
    """Ban SDK FO tu logcat lan mo app. Khong thay -> ''."""
    m = SDK_LOG_RE.search(log_text)
    return m.group(1) if m else ""


def parse_version(text: str) -> tuple[int, int, int] | None:
    """'3.5.4-alpha02' -> (3, 5, 4)."""
    m = VERSION_RE.search(text or "")
    return tuple(int(x) for x in m.groups()) if m else None


def read_tabs(path: str | Path) -> list[Tab]:
    """Doc moi tab `TC SDK ...`. Tab khong co bang TC -> RcError neu ro."""
    import openpyxl

    p = Path(path)
    wb = openpyxl.load_workbook(p, read_only=True, data_only=True)
    try:
        tabs = []
        for ws in wb.worksheets:
            m = TAB_RE.match(ws.title)
            if not m:
                continue
            rows = [tuple(r) for r in ws.iter_rows(values_only=True)]
            tabs.append(_tab(ws.title, m.group(1), tc_loader.parse_rows(rows, f"{p.name} / {ws.title}")))
    finally:
        wb.close()
    if not tabs:
        raise RcError(f"{p.name}: khong co tab nao ten 'TC SDK <version|tinh nang>'.")
    return tabs


def select(tabs: list[Tab], app_version: str, whitelist) -> tuple[list[Tab], list[str]]:
    """-> (tab can chay theo thu tu base, delta tang dan, tinh nang; ghi chu)."""
    v = parse_version(app_version)
    if not v:
        raise RcError(f"Khong doc duoc ban SDK cua app: {app_version!r}")
    notes: list[str] = []
    base = [t for t in tabs if t.kind == "base"]
    if not base:
        notes.append(f"Workbook khong co tab base {BASE_TAB!r} - chi chay delta.")
    deltas = sorted((t for t in tabs if t.kind == "delta"), key=lambda t: t.version)
    chosen_deltas = [t for t in deltas if t.version <= v]
    skipped = [t.name for t in deltas if t.version > v]
    if skipped:
        notes.append(f"Bo qua delta moi hon app {app_version}: {', '.join(skipped)}")
    if deltas and v > deltas[-1].version:
        notes.append(
            f"App {app_version} moi hon delta moi nhat ({deltas[-1].name}) - "
            "phan thay doi cua ban app chua co TC."
        )
    features = []
    for t in (t for t in tabs if t.kind == "feature"):
        if any(rc_extract.extract(c, whitelist).runnable for c in t.cases):
            features.append(t)
        else:
            notes.append(f"Bo qua {t.name}: app khong co key nao cua tinh nang nay (khong tich hop SDK do?).")
    return base + chosen_deltas + features, notes


def _tab(name: str, suffix: str, cases: list[Case]) -> Tab:
    version = parse_version(suffix)
    if name.strip().lower() == BASE_TAB.lower():
        return Tab(name, "base", version, cases)
    if version and version[0] == DELTA_MAJOR:
        return Tab(name, "delta", version, cases)
    return Tab(name, "feature", version, cases)
