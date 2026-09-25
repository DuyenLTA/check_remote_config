"""Chon bo case can chay tu file TC, roi boc ra cac luot config.

Dung giua `tc_catalog`/`tc_loader` (doc file) va `cli_check` (chay): mot cho
duy nhat tra loi "file nay ra nhung case nao, moi case bao nhieu luot mo app".

Hai dang file, khong tu doan:
  - workbook bo chung nhieu tab `TC SDK <version>` -> PHAI biet ban SDK cua app
    moi chon dung base + delta. Thieu thi dung lai, khong lay bua tab dau tien:
    lay nham tab la cham bang TC cua ban khac.
  - file mot sheet (bo cu viet rieng cho tung app) -> doc thang.
"""

from __future__ import annotations

from pathlib import Path

from . import rc_extract, tc_catalog, tc_loader
from .models import RcError


def needs_sdk(path: Path) -> bool:
    """File co phai workbook bo chung nhieu tab `TC SDK <version>` khong."""
    try:
        tc_catalog.read_tabs(path)
    except RcError:
        return False
    return True


def pick_tab(tabs, wanted: str):
    """Chi lay dung mot tab nguoi dung neu ten. Khong thay -> liet ke tab co that."""
    key = wanted.strip().lower().removeprefix("tc sdk").strip()
    hit = [t for t in tabs if t.name.lower().removeprefix("tc sdk").strip() == key]
    if not hit:
        raise RcError(
            f"Khong co tab nao ten 'TC SDK {wanted}'. Tab co trong file: "
            + ", ".join(t.name for t in tabs)
        )
    return hit


def tab_for_version(tabs, sdk: str):
    """Ban SDK cua app -> DUNG MOT tab so tuong ung.

    Bo TC khong co tab cho tung ban le (app 3.5.4 khong co tab 3.5.4), nen lay
    tab so LON NHAT ma <= ban app: phan thay doi tu ban do tro xuong la phan app
    dang chay. Khong co tab so nao <= thi lay tab base.

    KHONG dong toi tab tinh nang (widget, rating, daily checkin): do la SDK
    rieng, khong lien quan ban First Open - chay vao la mat thoi gian tren may.
    """
    version = tc_catalog.parse_version(sdk)
    if not version:
        raise RcError(f"Khong doc duoc ban SDK: {sdk!r}")
    deltas = sorted((t for t in tabs if t.kind == "delta" and t.version), key=lambda t: t.version)
    fit = [t for t in deltas if t.version <= version]
    if fit:
        return fit[-1]
    base = [t for t in tabs if t.kind == "base"]
    if base:
        return base[0]
    raise RcError(
        f"Bo TC khong co tab nao cho ban SDK {sdk}. Tab co trong file: "
        + ", ".join(t.name for t in tabs)
    )


def read_cases(path: Path, whitelist, sdk: str, tab: str = "") -> tuple[list[tuple], list[str]]:
    """-> ([(ten_tab, Case)], ghi chu cua tc_catalog).

    `tab` co gia tri: CHI chay dung tab do, khong keo theo base + delta. Nguoi
    dung neu dich danh mot ban SDK thi ho muon dung phan do, chay them tab khac
    la mat thoi gian tren may that.
    """
    try:
        tabs = tc_catalog.read_tabs(path)
    except RcError:
        return [("", c) for c in tc_loader.load(path)], []
    if tab:
        chosen = pick_tab(tabs, tab)
        return [(t.name, c) for t in chosen for c in t.cases], [f"Chỉ chạy tab {chosen[0].name}"]
    if sdk:
        one = tab_for_version(tabs, sdk)
        note = f"Bản SDK của app là {sdk} → chạy tab {one.name}"
        if one.kind == "base":
            note += " (bộ base, vì không có tab số nào ≤ bản app)"
        return [(one.name, c) for c in one.cases], [note]
    if not sdk:
        names = ", ".join(t.name for t in tabs)
        raise RcError(
            f"{path.name} la workbook bo chung ({names}) - phai co --sdk <X.Y.Z> "
            "de biet lay base + delta nao.\n"
            "Ban SDK doc o logcat lan mo app: `VslTemplate4FirstOpenSDK: Using version X`."
        )
    raise RcError("Thiếu bản SDK để chọn tab.")


def case_key(tab: str, n) -> str:
    """Khoa case: `<ban SDK>#<so>`.

    So case KHONG unique trong workbook bo chung - so `1` co o ca 5 tab. Lay
    mot minh con so lam khoa la case nay de len case kia, im lang: dem ra 120
    case trong khi that ra co 347.
    """
    suffix = tab.replace("TC SDK", "").strip() if tab else ""
    return f"{suffix}#{n}" if suffix else str(n)


def pick(runnable: dict, wanted: str) -> str:
    """Khoa that su tu cai nguoi dung go. Mo ho -> dung lai, khong chay bua."""
    if wanted in runnable:
        return wanted
    same_number = [k for k in runnable if k.rsplit("#", 1)[-1] == wanted]
    if len(same_number) == 1:
        return same_number[0]
    if same_number:
        raise RcError(
            f"Case {wanted} co o nhieu tab: {', '.join(sorted(same_number))}. "
            "Ghi ro tab, vd --case " + sorted(same_number)[0]
        )
    raise RcError(
        f"Case {wanted} khong chay tu dong duoc (hoac khong ton tai). "
        f"Co {len(runnable)} case chay duoc, vd: {', '.join(sorted(runnable)[:5])}"
    )


def load_cases(path, baseline, sdk: str = "", tab: str = "") -> tuple[list[dict], dict, list[str]]:
    """-> (bang case de in, {khoa_case: {runs, precondition, actions}}, ghi chu)."""
    whitelist = rc_extract.whitelist_of(baseline)
    pairs, notes = read_cases(Path(path), whitelist, sdk, tab)
    rows: list[dict] = []
    runnable: dict[str, dict] = {}
    for tab, case in pairs:
        data = rc_extract.extract(case, whitelist)
        if data.runnable:
            # Kem Precondition: device_reset doc no de biet case doi state sach
            # hay chi can force-stop.
            runnable[case_key(tab, case.n)] = {
                "runs": data.runs,
                "precondition": case.precondition,
                "actions": case.actions,
                "expects": case.expects,
            }
        rows.append({
            "n": case.n,
            "key": case_key(tab, case.n),
            "tab": tab,
            "feature": case.feature,
            "precondition": case.precondition,
            "label": case.label,
            "steps": len(case.actions),
            "assertions": len(case.expects),
            # Gia tri lua chon (`layout1/2/3`) -> moi gia tri mot luot mo app.
            "runs": len(data.runs),
            **data.summary,
        })
    return rows, runnable, notes
