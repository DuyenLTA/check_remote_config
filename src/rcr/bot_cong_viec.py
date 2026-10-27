"""Phan viec cua bot build-watch khong dinh toi Discord: tra package, goi rcr-cai-build, soan tin.

Tach khoi `discord_bot` de test khong can Discord / may.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from . import ad_units_sheet, build_ma_app, tc_source
from .models import RcError

TIMEOUT_CAI = 900
# Gioi han file dinh kem cua bot o server khong boost.
MAX_DINH_KEM = 10 * 1024 * 1024
TRANG_THAI = {"XONG": ("✅", "Xong"), "DUNG": ("⚠️", "Dừng — cần người xem"),
              "LOI": ("⛔", "Lỗi"), "HET_GIO": ("⏱️", "Hết giờ")}


def package_cua(ma: str, out_dir: Path) -> str:
    """Ma app -> package qua sheet "Check thong so KT" (tai ban moi, hong thi dung ban cu)."""
    link = os.environ.get("RC_AD_UNITS_SHEET") or ad_units_sheet.LINK
    try:
        path = tc_source.tai_ve(link, out_dir)
    except RcError:
        path = Path(out_dir) / f"tc-{tc_source.SHEET_RE.search(link).group(1)}.xlsx"
        if not path.exists():
            return ""
    return build_ma_app.package_cua(path, ma)


def _cli(args: list[str], timeout: int) -> dict:
    """Chay `rcr-cai-build` -> JSON, hoac {"loi": "..."} (dong LOI cua stderr)."""
    cmd = [sys.executable, "-m", "rcr.cli_cai_build", *args]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"loi": f"rcr-cai-build quá {timeout // 60} phút"}
    if p.returncode == 0:
        return json.loads(p.stdout.strip().splitlines()[-1])
    dong = [d for d in p.stderr.splitlines() if d.startswith("LOI:")]
    return {"loi": dong[-1][4:].strip() if dong else (p.stderr or p.stdout)[-300:]}


def cai(package: str, version: str, loai: str, serial: str) -> dict:
    return _cli(["--package", package, "--version", version, "--loai", loai, "--serial", serial], TIMEOUT_CAI)


def ten_may(serial: str, model: str) -> str:
    return f"{model} ({serial[-4:]})" if model else serial


def dau_tin(c: dict) -> str:
    return f"**{c['ma']}** {c['ten']} `{c['version']}` — `{c['package']}`"


def tin_hoi(c: dict) -> str:
    """Tin o kenh QA khi thay build moi: hoi co chay khong."""
    goc = f"\n[Tin build]({c['link_tin']})" if c.get("link_tin") else ""
    ghi = {"release": "next-gen → tải bản release",
           "debug": "không phải next-gen → tải bản có note `debug`"}[c["loai_ban"]]
    return f"{dau_tin(c)}\n{ghi} từ App Tester rồi chạy /rc-check. Chạy không?{goc}"


def file_report(kq: dict, out_dir: Path) -> Path | None:
    """File HTML de dinh kem khi KHONG co link artifact (user chot 27/10/2026: co link thi chi gan link).

    `link` do Claude ghi -> chi nhan file .html nam trong `out_dir`, khong dinh kem file bat ky.
    """
    link = kq.get("link") or ""
    if not link or link.startswith("https://"):
        return None
    try:
        f = Path(link).resolve()
        f.relative_to(Path(out_dir).resolve())
    except (OSError, ValueError):
        return None
    if f.suffix.lower() != ".html" or not f.is_file() or f.stat().st_size > MAX_DINH_KEM:
        return None
    return f


def tin_ket_qua(c: dict, kq: dict, dinh_kem: Path | None = None) -> str:
    dau, chu = TRANG_THAI.get(kq["trang_thai"], ("•", kq["trang_thai"]))
    dong = [f"{dau} {dau_tin(c)} — {chu}", kq.get("tom_tat", "")[:300]]
    if kq.get("link", "").startswith("https://"):
        dong.append(f"Report: {kq['link']}")
    elif dinh_kem:
        dong.append(f"Report: file `{dinh_kem.name}` đính kèm (chưa publish được artifact)")
    elif kq.get("link"):
        dong.append(f"Report trên máy chạy bot: `{kq['link']}`")
    if kq.get("phut") is not None:
        dong.append(f"{kq['phut']} phút · ${kq.get('chi_phi') or 0:.2f}")
    return "\n".join(d for d in dong if d)
