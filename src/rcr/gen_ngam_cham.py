"""So do cua `rcr-gen-ngam` -> verdict tung dong Expected trong file luot.

Kich ban ghi `So.ghi(case, mau_dong, dat, ly_do)`: `mau_dong` la regex so voi CHU dong Expected cua TC (khong theo so
thu tu dong - QA sua TC them / bot dong thi van khop). Dong khong co so do nao khop -> giu nguyen, liet ke o
`con_cham_tay`. Dong khop `bo_dong` cua app (data/gen_ngam_cong_thuc.yaml) -> bo khoi record (user chot 16/11/2026: dong
T2I / prompt cua app khong co T2I khong cham, khong hien tren report).
"""

from __future__ import annotations

import re
from pathlib import Path

from . import cham_tay, luot_file, run_batch
from .verdict_levels import FAIL, PASS, worst


class So:
    def __init__(self) -> None:
        self.dong: dict[str, list[tuple[str, bool, str]]] = {}
        self.dieu_kien: dict[str, str] = {}
        self.nho: dict = {}          # so do dung chung giua nhom (vd so video/ngay dem o R06 cho R07-01)
        self.log = None              # in tung so do ngay khi co (theo doi luot dang chay)
        self.luu = None              # ghi file so do sau MOI so do: luot bi kill giua chung khong mat so do da do

    def ghi(self, case: str, mau: str, dat: bool, ly_do: str) -> None:
        self.dong.setdefault(case, []).append((mau, bool(dat), " ".join(str(ly_do).split())))
        if self.log:
            self.log(f"  {case} {'PASS' if dat else 'FAIL'} · {mau}: {' '.join(str(ly_do).split())[:160]}")
        if self.luu:
            self.luu()

    def ep(self, case: str, cach: str) -> None:
        """Case nay tool TU TAO dieu kien (vd doi generating_wait de anh xong truoc popup) - ghi len report."""
        self.dieu_kien[case] = cach


def _bo_dong(record: dict, bo: list[dict]) -> dict:
    giu, bo_ra = [], []
    for l in record.get("lines") or []:
        k = next((b for b in bo if re.search(b["mau"], l.get("e") or "")), None)
        (bo_ra if k else giu).append(l if not k else {"e": l.get("e"), "ly_do": k["ly_do"]})
    if not bo_ra:
        return record
    ke = [l["v"] for l in giu if l.get("scope") != "po"]
    return {**record, "lines": giu, "dong_bo": bo_ra, "verdict": worst(ke) if ke else record.get("verdict"),
            "pending": sum(1 for l in giu if l.get("v") not in (PASS, FAIL))}


def ghi_luot(luot: str, package: str, so: So, bo: list[dict], log_fn) -> dict:
    data = luot_file.doc(luot, package)
    records, ghi, con = [], [], []
    for r in data["records"]:
        r = _bo_dong(r, bo)
        quy = so.dong.get(r.get("key"), [])
        for i, l in enumerate(list(r.get("lines") or []), 1):
            k = next((q for q in quy if re.search(q[0], l.get("e") or "", re.I)), None)
            if k is None:
                if l.get("v") not in (PASS, FAIL):
                    con.append(f"{r['key']} dòng {i}: {l.get('e')}")
                continue
            r = cham_tay.cham(r, [i], PASS if k[1] else FAIL, f"rcr-gen-ngam: {k[2]}", ai="Tool",
                              dieu_kien=so.dieu_kien.get(r.get("key"), ""))
            ghi.append(f"{r['key']} dòng {i}: {'PASS' if k[1] else 'FAIL'}")
        records.append(r)
    meta = {k: v for k, v in data.items() if k not in ("records", "phien_ban", "xong")}
    if data.get("report"):
        run_batch.ghi_report(luot_file.baseline_tu(data), data.get("tc") or {}, records, data.get("app_label", ""),
                             data["report"], log_fn)
    luot_file.ghi(Path(luot), meta, records, bool(data.get("xong")))
    dem = {}
    for r in records:
        dem[r.get("verdict")] = dem.get(r.get("verdict"), 0) + 1
    return {"da_ghi": len(ghi), "con_cham_tay": con, "verdict": dem, "report": data.get("report", "")}
