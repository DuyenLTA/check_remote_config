"""Doi chieu build voi plan tuan cua QA: build khac yeu cau trong plan -> preflight LOI, dung luot.

User chot 30/10/2026: AIP882 4.3.0 plan ghi "- SDK 3.6.1" nhung build in SDK 3.7.0, tool chay checklist
Next-Gen vo nghia. Tu nay khac plan thi dung lai, bao QA o qa-auto (bot dang ket qua DUNG duoi tin build).

Plan la Google Sheet (link trong bien `RC_PLAN_TUAN_SHEET`, khong ghi vao repo public), moi tuan mot tab ten
`<ddmm>-<ddmmyyyy>` (`2610-30102026` = 26/10 - 30/10/2026; tab cu thang 1 chu so nhu `108 - 1482026`
khong doc - chi can tab tuan hien tai). Dong cua app:
o ma app (`AIP882`, `AIP882 (từ 3.6.0)`) + o noi dung (`- SDK 3.6.1`, `- Apply SDK Next Gen`). Dong QA
(`test v4.3.0 doing`) khong co so SDK nen tu bo qua.
"""

from __future__ import annotations

import datetime as dt
import re

from . import build_ma_app, sdk_probe, tc_catalog, tc_source
from .models import RcError

ENV = "RC_PLAN_TUAN_SHEET"
# Version QA ghi trong plan: dong cong viec "test v1.9.0 rls", Detail iOS "v7.9.3:" / "ver3.2.0:". Bat buoc co "v" /
# "ver" truoc so - so trong "- SDK 3.6.1" la ban SDK, khong phai version app (bo phan SDK truoc khi do).
PLAN_VER_RE = re.compile(r"(?<![A-Za-z0-9])v(?:er(?:sion)?)?\s*\.?\s*(\d+\.\d+\.\d+)", re.I)
RELEASE_RE = re.compile(r"(?<![A-Za-z])(?:rls|release)(?![A-Za-z])", re.I)
DEBUG_RE = re.compile(r"(?<![A-Za-z])debug(?![A-Za-z])", re.I)
# O Detail (scope ban build): dong gach dau dong "- Apply photo picker" hoac co ghi SDK.
SCOPE_RE = re.compile(r"(?:^|\n)\s*-\s*\S")
TAB_RE = re.compile(r"^\s*(\d{1,2})(\d{2})\s*-\s*(\d{1,2})(\d{2})(\d{4})\s*$")


def tuan_cua_tab(ten: str) -> tuple[dt.date, dt.date] | None:
    """'2610-30102026' -> (26/10/2026, 30/10/2026); ten khong dung mau -> None."""
    m = TAB_RE.match(ten or "")
    if not m:
        return None
    d1, m1, d2, m2, nam = (int(x) for x in m.groups())
    try:
        cuoi = dt.date(nam, m2, d2)
        return dt.date(nam - 1 if m1 > m2 else nam, m1, d1), cuoi   # tuan vat qua nam moi
    except ValueError:
        return None


def ma_cua_package(path, package: str) -> str:
    """Ten tab (ma app) co dong "Package name" = `package` trong sheet Check thong so KT; "" khi khong co."""
    import openpyxl

    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        for ws in wb.worksheets:
            for r in ws.iter_rows(values_only=True):
                o = [str(v).strip() for v in r if v not in (None, "")]
                if len(o) >= 2 and o[0].lower() == "package name" and o[1] == package:
                    return ws.title.strip().upper()
        return ""
    finally:
        wb.close()


def yeu_cau(path, ma: str, ngay: dt.date) -> dict | None:
    """Yeu cau cua app `ma` trong tab tuan chua `ngay`: {tab, sdk: [X.Y.Z], next_gen, dong: [noi dung SDK],
    version: [X.Y.Z], loai: "release"|"debug"|"", pham_vi: [o Detail]}.
    Khong co tab tuan -> None; app khong co dong nao ghi gi -> cac truong rong.
    User 03/11/2026: plan ghi app + version + scope ban build de check dev build nham version / apply nham SDK."""
    import openpyxl

    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        ws = next((w for w in wb.worksheets if (t := tuan_cua_tab(w.title)) and t[0] <= ngay <= t[1]), None)
        if ws is None:
            return None
        ra = {"tab": ws.title.strip(), "sdk": [], "next_gen": False, "dong": [], "version": [], "loai": "",
              "pham_vi": []}
        cot: dict[str, int] = {}
        for r in ws.iter_rows(values_only=True):
            tieu_de = cot_tieu_de(r)
            if tieu_de:
                cot = tieu_de        # bang moi (co cot "App version"): doc dung cot tu day tro xuong
                continue
            o = [str(v).strip() for v in r if isinstance(v, str) and v.strip()]
            if not any((m := build_ma_app.MA_RE.match(c)) and m.group(1).upper() == ma for c in o):
                continue
            if cot:
                _doc_theo_cot(r, cot, ra)
                continue
            for c in o:
                bo_sdk = build_ma_app.SDK_RE.sub(" ", c)
                ra["version"] += [v for v in PLAN_VER_RE.findall(bo_sdk) if v not in ra["version"]]
                if RELEASE_RE.search(c):
                    ra["loai"] = "release"
                elif DEBUG_RE.search(c) and not ra["loai"]:
                    ra["loai"] = "debug"
                if (SCOPE_RE.search(c) or build_ma_app.SDK_RE.search(c)) and c not in ra["pham_vi"]:
                    ra["pham_vi"].append(c)
                so = [s for s in build_ma_app.SDK_RE.findall(c) if s not in ra["sdk"]]
                ng = bool(build_ma_app.NEXT_GEN_RE.search(c)) and not build_ma_app.REVERT_RE.search(c)
                if so or ng:
                    ra["sdk"] += so
                    ra["next_gen"] = ra["next_gen"] or ng
                    ra["dong"].append(" ".join(c.split()))
        return ra
    finally:
        wb.close()


def _chuan(o) -> str:
    return " ".join(str(o).split()).casefold() if isinstance(o, str) else ""


def cot_tieu_de(r) -> dict[str, int]:
    """Dong tieu de bang plan moi (03/11/2026): "Loai du an | OS | Ten du an | App version | Detail | ..." ->
    {"ten", "version", "detail"} -> chi so cot. Khong phai dong tieu de -> {}."""
    ten = {_chuan(v): i for i, v in enumerate(r)}
    if "app version" not in ten or "detail" not in ten:
        return {}
    return {"ten": ten.get("tên dự án", -1), "version": ten["app version"], "detail": ten["detail"]}


def _doc_theo_cot(r, cot: dict[str, int], ra: dict) -> None:
    """Mot dong app cua bang co cot: version tu cot "App version", SDK + scope tu cot "Detail"."""
    def o(ten):
        i = cot.get(ten, -1)
        v = r[i] if 0 <= i < len(r) else None
        return "" if v is None else str(v).strip()
    ver, detail = o("version"), o("detail")
    ra["version"] += [v for v in re.findall(r"\d+\.\d+\.\d+", ver) if v not in ra["version"]]
    for c in (ver, detail):
        if RELEASE_RE.search(c):
            ra["loai"] = "release"
        elif DEBUG_RE.search(c) and not ra["loai"]:
            ra["loai"] = "debug"
    if detail:
        if detail not in ra["pham_vi"]:
            ra["pham_vi"].append(detail)
        so = [s for s in build_ma_app.SDK_RE.findall(detail) if s not in ra["sdk"]]
        ng = bool(build_ma_app.NEXT_GEN_RE.search(detail)) and not build_ma_app.REVERT_RE.search(detail)
        if so or ng:
            ra["sdk"] += so
            ra["next_gen"] = ra["next_gen"] or ng
            ra["dong"].append(" ".join(detail.split()))


def lech(yc: dict, sdk_khai: str, sdk_log: str) -> list[str]:
    """Cac diem build khac plan (rong = khop). So theo X.Y.Z, bo hau to -alphaNN."""
    ra = []
    can = {tc_catalog.parse_version(s) for s in yc["sdk"]}
    for nguon, sdk in (("tin build ghi", sdk_khai), ("app in log", sdk_log)):
        v = tc_catalog.parse_version(sdk)
        if v is None:
            continue
        if can and v not in can:
            ra.append(f"{nguon} SDK {sdk}, plan ghi {' / '.join(yc['sdk'])}")
        elif not can and yc["next_gen"] and not sdk_probe.la_nextgen(sdk):
            ra.append(f"{nguon} SDK {sdk}, plan ghi Next-Gen")
    return ra


def lech_ban(yc: dict, ver_app: str, loai_app: str) -> list[str]:
    """Version / loai ban dang cai khac plan (rong = khop hoac plan khong ghi). `ver_app` dang '1.9.0' hay
    '1.9.0 (11)'; so theo X.Y.Z."""
    ra = []
    co = re.search(r"\d+\.\d+\.\d+", ver_app or "")
    if yc.get("version") and co and co.group(0) not in yc["version"]:
        ra.append(f"máy đang cài version {co.group(0)}, plan ghi v{' / v'.join(yc['version'])}")
    if yc.get("loai") and loai_app and loai_app != yc["loai"]:
        ra.append(f"máy đang cài bản {loai_app}, plan ghi bản {yc['loai']}")
    return ra


def tai(link: str, out_dir) -> str:
    try:
        return tc_source.tai_ve(link, out_dir)
    except RcError as exc:
        raise RcError(f"không tải được plan tuần: {exc}") from None
