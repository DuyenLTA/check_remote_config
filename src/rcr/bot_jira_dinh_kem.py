"""Anh bang chung cua case FAIL -> file dinh kem issue Jira (thay cho link report trong description).

User chot 17/11/2026: log Jira kem anh / video bug, khong dan link report. Anh lay tu file luot
(`out/run-*.luot.json`) cua dung package + case: anh do tay (`anh_tay`, Claude chon dung man loi)
truoc, roi anh chup cac buoc tool lai (`steps[].shot`, lay cac buoc cuoi - man loi hien ra o cuoi).
Ca hai luu dang data URI JPEG/PNG trong file luot nen khong phu thuoc file anh tren dia.
"""

from __future__ import annotations

import base64
import json
import logging
import re
from pathlib import Path

log = logging.getLogger(__name__)

TOI_DA_ANH = 6
# Jira Server mac dinh gioi han 10 MB/file; anh chup man ~100-300 KB - bo anh hong / qua lon.
MAX_BYTE = 10 * 1024 * 1024
DATA_URI_RE = re.compile(r"^data:image/(png|jpe?g|webp);base64,(.+)$", re.S)
TEN_RE = re.compile(r"[^\w.-]+")


def _cung_case(key: str, case: str) -> bool:
    """Case trong bug co the la `tab#TC ID` (tu file luot) hoac chi TC ID (Claude tra ve)."""
    return bool(key) and (key == case or key.split("#")[-1] == case.split("#")[-1])


def _giai_anh(src: str) -> tuple[str, bytes] | None:
    m = DATA_URI_RE.match(src or "")
    if not m:
        return None
    try:
        du_lieu = base64.b64decode(m.group(2), validate=False)
    except (ValueError, TypeError):
        return None
    if not du_lieu or len(du_lieu) > MAX_BYTE:
        return None
    return ("jpg" if m.group(1).startswith("jp") else m.group(1)), du_lieu


def _record(out: Path, package: str, case: str) -> dict | None:
    """Record moi nhat cua case (uu tien record FAIL) trong cac file luot cua package."""
    du_phong = None
    for f in sorted(out.glob("run-*.luot.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        if package not in f.name:
            continue
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if d.get("package") not in (None, package):
            continue
        for r in d.get("records") or []:
            if _cung_case(str(r.get("key") or ""), case):
                if r.get("verdict") == "FAIL":
                    return r
                du_phong = du_phong or r
    return du_phong


def anh_cua_case(out: Path, package: str, case: str, toi_da: int = TOI_DA_ANH) -> list[tuple[str, bytes]]:
    """-> [(ten file, bytes)] anh bang chung cua case, toi da `toi_da` anh; khong co -> []."""
    r = _record(Path(out), package, case)
    if not r:
        return []
    ma = TEN_RE.sub("_", case.split("#")[-1])[:60]
    ra: list[tuple[str, bytes]] = []
    for i, a in enumerate(r.get("anh_tay") or [], 1):
        g = _giai_anh(str((a or {}).get("src") or "")) if isinstance(a, dict) else None
        if g:
            ten = TEN_RE.sub("_", str(a.get("ten") or f"anh{i}"))[:60]
            ra.append((f"{ma}_{ten}.{g[0]}", g[1]))
    con = max(0, toi_da - len(ra))
    buoc = [s for s in r.get("steps") or [] if isinstance(s, dict) and s.get("shot")]
    for s in buoc[-con:] if con else []:
        g = _giai_anh(str(s["shot"]))
        if g:
            ten = TEN_RE.sub("_", f"buoc{s.get('n', '')}_{s.get('k', '')}")[:60]
            ra.append((f"{ma}_{ten}.{g[0]}", g[1]))
    # Ten trung (2 buoc cung so + loai) -> them so thu tu de Jira khong ghi de.
    thay: dict[str, int] = {}
    kq = []
    for ten, b in ra[:toi_da]:
        n = thay[ten] = thay.get(ten, 0) + 1
        kq.append((ten if n == 1 else ten.replace(".", f"_{n}.", 1), b))
    return kq


def dinh_kem_issues(url: str, token: str, out: Path, package: str, issues: list[dict]) -> dict[str, int]:
    """Dinh kem anh cho tung issue vua log -> {key: so anh da gan}. Loi mot issue khong chan issue khac."""
    from . import bot_jira_rest as jira_rest
    ra: dict[str, int] = {}
    for i in issues:
        key, case = str(i.get("key") or ""), str(i.get("case") or "")
        if not key or not case:
            continue
        anh = anh_cua_case(out, package, case)
        if not anh:
            ra[key] = 0
            continue
        try:
            jira_rest.dinh_kem(url, token, key, anh)
            ra[key] = len(anh)
        except jira_rest.JiraLoi as exc:
            log.warning("dinh kem anh %s loi: %s", key, exc)
            ra[key] = -1
    return ra
