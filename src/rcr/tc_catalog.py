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

class KhongPhaiWorkbookTC(RcError):
    """File khong co tab `TC SDK ...` nao -> la file mot sheet (bo cu viet rieng cho tung app)."""


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
        co_tab_tc_ten = False
        for ws in wb.worksheets:
            m = TAB_RE.match(ws.title)
            if not m:
                continue
            co_tab_tc_ten = True
            rows = [tuple(r) for r in ws.iter_rows(values_only=True)]
            try:
                cases = tc_loader.parse_rows(rows, f"{p.name} / {ws.title}")
            except tc_loader.TabRongError:
                # Mot tab rong (QA dang soan / xoa het case) khong duoc lam hong ca workbook: truoc day
                # loi nay lam tc_select tuong file mot sheet va doc sheet DAU TIEN ("TC SDK Next Gen")
                # cho app 3.5.4 - 46 case SDKNG, 0 chay duoc (tab "TC SDK rating" rong, 09/11/2026).
                continue
            tabs.append(_tab(ws.title, m.group(1), cases))
    finally:
        wb.close()
    if not tabs:
        if co_tab_tc_ten:
            raise RcError(f"{p.name}: co tab 'TC SDK ...' nhung tab nao cung chua co dong case.")
        raise KhongPhaiWorkbookTC(f"{p.name}: khong co tab nao ten 'TC SDK <version|tinh nang>'.")
    return tabs


BAN_SAO_RE = re.compile(r"TC SDK\s+(.+?)\s*$", re.I)


def read_tab_ten(path: str | Path, title: str) -> Tab | None:
    """Tab nguoi dung chi dich danh theo TEN THAT, ten khong bat dau bang `TC SDK` (vd QA nhan ban
    `Ban sao cua TC SDK 3.5.4` roi chot ban sao la ban dung). Tab tra ve mang ten chuan `TC SDK 3.5.4`
    de khoa case (`3.5.4#...`) trung khoa luot cu -> `--gop` de dung record. Khong co tab do -> None."""
    import openpyxl

    want = " ".join(title.split()).lower()
    if not want or TAB_RE.match(title):
        return None  # tab `TC SDK x` thuong: pick_tab lo
    p = Path(path)
    wb = openpyxl.load_workbook(p, read_only=True, data_only=True)
    try:
        ws = next((w for w in wb.worksheets if " ".join(w.title.split()).lower() == want), None)
        m = BAN_SAO_RE.search(ws.title) if ws else None
        if not m:
            return None
        rows = [tuple(r) for r in ws.iter_rows(values_only=True)]
        return _tab(f"TC SDK {m.group(1)}", m.group(1), tc_loader.parse_rows(rows, f"{p.name} / {ws.title}"))
    finally:
        wb.close()


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
