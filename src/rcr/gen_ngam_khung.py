"""Dung file luot (khung 37 case) cho `rcr-gen-ngam` thang tu sheet TC gen ngam, KHONG mo app.

`rcr-check --tc gen-ngam --no-actions` van dat config + clear data + lai FO cho tung case (tab tinh nang luon lai toi
Home) -> 6+ phut chi de co khung (do 16/11/2026). Khung chi can: key, nhan, precondition, overrides tu Test Data,
dong Expected. Meta (baseline_tom, tc...) chep tu luot gen ngam gan nhat cua app de dung report.
"""

from __future__ import annotations

import copy
import re
import time
from pathlib import Path

from . import luot_file, tc_loader, tc_tinh_nang_rieng
from .models import RcError
from .verdict_levels import NEEDS_HUMAN

KV_RE = re.compile(r"^\s*([A-Za-z_][\w]*)\s*=\s*(.+?)\s*$")
GIU_NGUYEN_RE = re.compile(r"gi[áa]\s*tr[ịi]\s*hi[ệe]n\s*t[ạa]i", re.I)
NEN = {"enable_all_ads": "true", "enable_all_ads_tutorial": "true"}
BO_KEY_CU = ("cham_tay", "anh_tay", "dong_bo", "loi_chay")


def overrides(test_data: str) -> dict[str, str]:
    ra = dict(NEN)
    for dong in re.split(r"[\n/]", test_data or ""):
        m = KV_RE.match(dong)
        if m and not GIU_NGUYEN_RE.search(m.group(2)):
            ra[m.group(1)] = m.group(2)
    return ra


def luot_mau(out_dir: Path, package: str) -> dict:
    ds = sorted(Path(out_dir).glob(f"run-{package}-*g*n*.luot.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    for p in ds:
        try:
            d = luot_file.doc(str(p), package)
        except RcError:
            continue
        if d.get("baseline_tom") and str(d.get("tc_nguon", "")).lower() == "gen-ngam":
            return d
    raise RcError(f"chưa có lượt gen ngầm nào của {package} để chép meta — chạy một lần "
                  "`rcr-check --tc gen-ngam --case all --no-actions --no-walk`")


def dung(package: str, serial: str, out_dir: Path, app_label: str = "") -> Path:
    xlsx, _doi, link = tc_tinh_nang_rieng.dung("gen-ngam", package, out_dir)
    cases = tc_loader.load(xlsx)
    mau = luot_mau(out_dir, package)
    theo_key = {r.get("key"): r for r in mau["records"]}
    goc = mau["records"][0]
    records = []
    for c in cases:
        r = copy.deepcopy(theo_key.get(c.n) or goc)
        for k in BO_KEY_CU:
            r.pop(k, None)
        lines = [{"v": NEEDS_HUMAN, "e": e, "r": "chờ rcr-gen-ngam đo"} for e in c.expects]
        r.update(key=c.n, group=c.feature, label=c.label, precondition=c.precondition, overrides=overrides(c.test_data),
                 verdict=NEEDS_HUMAN, actual="", lines=lines, pending=len(lines), precondition_thieu=[],
                 lich_su_verdict=[], lich_su_dong=[], ad_click=0, ads=[], banner_states=[], steps=[], ep_ad_fail="",
                 thoi_gian_s=0)
        records.append(r)
    ts = time.strftime("%H%M%S")
    report = Path(out_dir) / f"run-{package}-{serial}-gn-{ts}.html"
    meta = {k: v for k, v in mau.items() if k not in ("records", "phien_ban", "xong", "cap_nhat")}
    meta.update(generated_at=time.strftime("%Y-%m-%dT%H:%M:%S%z"), serial=serial, report=str(report),
                case_list=",".join(c.n for c in cases), app_label=app_label or mau.get("app_label", ""),
                tc_link=link)
    path = luot_file.duong_dan(str(report), out_dir, package)
    luot_file.ghi(path, meta, records, True)
    return path


def lam_moi(luot: str, package: str, out_dir: Path, log) -> list[str]:
    """Tai lai sheet TC (QA sua giua cac lan chay - user nhac 16/11/2026) va dung lai record theo ban moi: case / dong
    Expected doi thi thay, case moi thi them, case bi bo thi bo. Tra danh sach case co dong Expected doi."""
    xlsx, _doi, link = tc_tinh_nang_rieng.dung("gen-ngam", package, out_dir)
    cases = tc_loader.load(xlsx)
    data = luot_file.doc(luot, package)
    theo_key = {r.get("key"): r for r in data["records"]}
    goc = data["records"][0]
    records, doi = [], []
    for c in cases:
        cu = theo_key.get(c.n)
        # Dong da bo khoi report (bo_dong) nam o `dong_bo`, khong o `lines` -> so ca hai.
        co = [l.get("e") for l in cu.get("lines") or []] + [l.get("e") for l in cu.get("dong_bo") or []] if cu else []
        if cu is not None and sorted(co) == sorted(c.expects) and cu.get("overrides") == overrides(c.test_data):
            records.append(cu)
            continue
        doi.append(c.n)
        r = copy.deepcopy(cu or goc)
        for k in BO_KEY_CU:
            r.pop(k, None)
        lines = [{"v": NEEDS_HUMAN, "e": e, "r": "chờ rcr-gen-ngam đo"} for e in c.expects]
        r.update(key=c.n, group=c.feature, label=c.label, precondition=c.precondition, overrides=overrides(c.test_data),
                 verdict=NEEDS_HUMAN, actual="", lines=lines, pending=len(lines), precondition_thieu=[])
        records.append(r)
    meta = {k: v for k, v in data.items() if k not in ("records", "phien_ban", "xong", "cap_nhat")}
    meta.update(case_list=",".join(c.n for c in cases), tc_link=link)
    luot_file.ghi(Path(luot), meta, records, True)
    log(f"Tải lại sheet TC gen ngầm: {len(cases)} case" + (f", đổi so với file lượt: {', '.join(doi)}" if doi else
                                                         ", không đổi so với file lượt"))
    return doi
