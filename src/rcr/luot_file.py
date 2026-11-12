"""File ket qua cua mot luot, ghi SAU MOI CASE - de luot bi tat giua chung van con.

Truoc day ket qua chi ra stdout + report luc chay XONG ca luot. 23/10/2026 luot
19 case Sorapix bi Claude Code tat o case 14 (RAM may tinh can): khong JSON,
khong report, chi con log tien do - 70 phut may chay mat trang.

Giu tren dia: meta luot (package, may, bo TC), danh sach case can chay, record
tung case da xong, va tom tat baseline du de dung lai report khong can may.

    --tiep <file>  chay NOT case chua co trong file (luot truoc bi tat)
    --gop <file>   lay record trong file lam nen, case chay lai thi de len theo key;
                   khong kem --case = chi dung lai report tu cac file, khong can may
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path

from .models import RcError

PHIEN_BAN = 1


@dataclass
class BaselineTom:
    """Phan baseline ma `report_data.page_data` doc - dung lai report khong can may."""
    serial: str
    package: str
    configs: list = field(default_factory=list)
    mirrored_keys: list = field(default_factory=list)


def tom_baseline(baseline) -> dict:
    return {"serial": baseline.serial, "package": baseline.package,
            "configs": sorted(baseline.configs), "mirrored_keys": sorted(baseline.mirrored_keys)}


def duong_dan(report: str, out_dir, package: str) -> Path:
    """Canh report (`run.html` -> `run.luot.json`); khong co report thi dat ten theo gio.

    Duoi `.luot.json` rieng: `--report x.json` ma doi duoi thanh `.json` thi report HTML
    ghi de chinh file luot sau moi case.
    """
    if report:
        p = Path(report)
        return p.with_name(p.stem + ".luot.json")
    return Path(out_dir) / f"luot-{package}-{time.strftime('%y%m%d-%H%M%S')}.luot.json"


def ghi_nguyen_tu(path: Path, text: str) -> None:
    """Ghi qua file tam roi doi ten: bi tat dung luc ghi thi file cu van nguyen.

    Windows: antivirus / indexer / editor dang mo file thi `os.replace` bao
    PermissionError mot lat -> thu lai vai lan.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tam = path.with_name(path.name + ".tmp")
    tam.write_text(text, encoding="utf-8")
    for lan in range(4):
        try:
            os.replace(tam, path)
            return
        except PermissionError:
            if lan == 3:
                raise
            time.sleep(0.5)


def ghi(path: Path, meta: dict, records: list[dict], xong: bool) -> None:
    ghi_nguyen_tu(path, json.dumps({**meta, "phien_ban": PHIEN_BAN, "xong": xong,
                                    "cap_nhat": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                                    "records": records}, ensure_ascii=False))


def da_xong(records: list[dict]) -> frozenset:
    """Key co ket qua that (--tiep bo qua). Case hong vi loi chay (adb treo...) thi chay lai."""
    return frozenset(r["key"] for r in records if not r.get("loi_chay"))


def doc(path: str, package: str) -> dict:
    p = Path(path)
    if not p.exists():
        raise RcError(f"Không thấy file lượt {p}")
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RcError(f"File lượt {p} không phải JSON hợp lệ: {exc}") from exc
    # Ban cu (truoc file luot): stdout cua rcr-check co `cases`, hoac file chi la list record.
    if isinstance(data, list):
        data = {"records": data}
    elif "records" not in data and isinstance(data.get("cases"), list):
        data = {**data, "records": data["cases"]}
    if "records" not in data:
        raise RcError(f"File {p} không phải file lượt của rcr-check (thiếu `records`)")
    # Gop nham luot cua app khac la report tron ket qua hai app ma khong ai biet.
    if data.get("package") and data["package"] != package:
        raise RcError(f"File {p} là lượt của {data['package']}, không phải {package}")
    return data


def gop(*dot: list[dict]) -> list[dict]:
    """Gop nhieu dot record theo `key`: dot sau de dot truoc, giu thu tu xuat hien dau tien."""
    theo_key: dict[str, dict] = {}
    for records in dot:
        for r in records:
            theo_key[r["key"]] = r
    return list(theo_key.values())


# Truong cua case ma doi la thanh case khac: record cu cham theo noi dung cu.
_TRUONG_NOI_DUNG = ("label", "precondition")


def _overrides_doi(r: dict, c: dict) -> bool:
    """Gia tri TC dat cho mot key app CO doc khac voi luc cham -> case da doi noi dung.

    Record khong bao gio bang nguyen van TC: tool tu them key nen (`enable_all_ads_tutorial`
    sau pm clear) va bo key app khong doc (`keys_not_used`, soi DEX). So nguyen dict thi moi
    case deu "doi" va --gop bo sach ket qua (05/11/2026, AIP893 52/52 case bi bo).
    """
    if "overrides" not in r or "overrides" not in c:
        return False
    ro, bo = r.get("overrides") or {}, set(r.get("keys_not_used") or [])
    return any(k not in bo and ro.get(k) != v for k, v in (c.get("overrides") or {}).items())


def loc_theo_tc(records: list[dict], rows: list[dict]) -> tuple[list[dict], list[str], list[str]]:
    """Bo record --gop khong con khop bo TC vua tai -> (giu, key da xoa khoi sheet, key doi noi dung).

    03/11/2026 sheet TC 3.6.1 sua qua dem (61 -> 57 case, RG02 viet lai): gop theo key giu
    nguyen PASS/FAIL cua noi dung cu duoi ma case moi, report noi sai ve case dang co tren sheet.
    """
    theo_key = {c["key"]: c for c in rows}
    giu, da_xoa, doi = [], [], []
    for r in records:
        c = theo_key.get(r["key"])
        if c is None:
            da_xoa.append(r["key"])
        elif any(f in r and f in c and r[f] != c[f] for f in _TRUONG_NOI_DUNG) or _overrides_doi(r, c):
            doi.append(r["key"])
        else:
            giu.append(r)
    return giu, da_xoa, doi


def doc_nhieu(paths: list[str], package: str) -> tuple[dict, list[dict]]:
    """-> (meta cua file CUOI, record da gop). File sau thang file truoc."""
    datas = [doc(p, package) for p in paths]
    return {**datas[-1], "tc": _gop_tc(d.get("tc") or {} for d in datas)}, gop(*(d["records"] for d in datas))


def _gop_tc(tcs) -> dict:
    """Bo TC cua cac file luot gop: moi TAB lay ban cua file SAU CUNG co tab do.

    Gop nhieu tab (rating + widget + daily checkin, moi tab mot luot) ma lay nguyen bo TC cua file
    cuoi thi `loc_theo_tc` coi moi case cua tab khac la "khong con tren sheet" va bo sach
    (AIP893 12/11/2026: 3 file -> report con 14/36 case). Cung tab thi file sau van thang.
    """
    tcs = [t for t in tcs if t]
    if not tcs:
        return {}
    theo_tab: dict[str, list[dict]] = {}
    for t in tcs:
        nhom: dict[str, list[dict]] = {}
        for c in t.get("cases") or ():
            nhom.setdefault(c.get("tab", ""), []).append(c)
        theo_tab.update(nhom)
    cases = [c for nhom in theo_tab.values() for c in nhom]
    notes = list(dict.fromkeys(n for t in tcs for n in t.get("notes") or ()))
    return {**tcs[-1], "cases": cases, "notes": notes, "total": len(cases),
            "runnable": sum(1 for c in cases if c.get("runnable"))}


def baseline_tu(meta: dict) -> BaselineTom:
    b = meta.get("baseline_tom") or {}
    if not b:
        raise RcError("File lượt không có tóm tắt baseline - không dựng lại report được")
    return BaselineTom(b["serial"], b["package"], b.get("configs", []), b.get("mirrored_keys", []))
