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


def doc_nhieu(paths: list[str], package: str) -> tuple[dict, list[dict]]:
    """-> (meta cua file CUOI, record da gop). File sau thang file truoc."""
    datas = [doc(p, package) for p in paths]
    return datas[-1], gop(*(d["records"] for d in datas))


def baseline_tu(meta: dict) -> BaselineTom:
    b = meta.get("baseline_tom") or {}
    if not b:
        raise RcError("File lượt không có tóm tắt baseline - không dựng lại report được")
    return BaselineTom(b["serial"], b["package"], b.get("configs", []), b.get("mirrored_keys", []))
