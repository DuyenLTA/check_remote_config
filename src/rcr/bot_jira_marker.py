"""Marker may doc duoc trong description bug tren Jira + hop nhat ung vien verify.

Moi bug tool log (bot Discord, rc-check trong terminal, checklist Next-Gen) mang label `auto-qa` va mot dong
trong description: `AUTOQA case=<ma case> ban=<debug|release> pkg=<package>`. Bot verify tim bug Reviewing
theo label, doc dong nay de biet chay lai case nao tren ban nao. Dinh dang tranh ky tu wiki Jira (`[ ]`, `{ }`,
`*`) de khong bi render/escape; doc nghiem: dung mau + tung gia tri qua regex, sai mau -> coi nhu khong co marker.
"""

from __future__ import annotations

import re

from . import bot_verify_jira as v
from .bot_chay_claude import PACKAGE_RE

LABEL = "auto-qa"
LOAI_BAN = ("debug", "release")
MARKER_RE = re.compile(r"^AUTOQA case=(.{1,120}?) ban=(debug|release) pkg=(\S{1,200})[ \t]*$", re.M)


def dong_marker(case: str, loai_ban: str, package: str) -> str:
    """Dong marker de dua vao description; gia tri sai -> ValueError (khong log marker hong)."""
    if v.loai_case(case) is None:
        raise ValueError(f"case không hợp lệ: {case!r}")
    if loai_ban not in LOAI_BAN:
        raise ValueError(f"loại bản không hợp lệ: {loai_ban!r}")
    if not PACKAGE_RE.match(package or ""):
        raise ValueError(f"package không hợp lệ: {package!r}")
    return f"AUTOQA case={case} ban={loai_ban} pkg={package}"


def doc_marker(description) -> dict | None:
    """{case, loai_ban, package} tu description, hoac None. Dong dau tien dung mau va hop le thang."""
    if not isinstance(description, str):
        return None
    # Jira co the escape ky tu wiki bang `\\`; bo truoc khi doc.
    for m in MARKER_RE.finditer(description.replace("\\", "")):
        case, loai_ban, pkg = m.group(1).strip(), m.group(2), m.group(3)
        if v.loai_case(case) and PACKAGE_RE.match(pkg):
            return {"case": case, "loai_ban": loai_ban, "package": pkg}
    return None


def gop(jira_items: list[dict], state_uv: list[dict]) -> list[dict]:
    """Ung vien = bug label `auto-qa` tren Jira (chinh) + ung vien tu state (bug cu chua co label), khong trung key.
    jira_items: [{key, link, summary, marker}] (marker None khi thieu). Issue Jira khong co marker ma state
    cung khong biet -> case rong (phan_loai se bo kem ly do)."""
    cu = {u["key"]: u for u in state_uv}
    ra: dict[str, dict] = {}
    for i in jira_items:
        m = i.get("marker")
        if m:
            ra[i["key"]] = {"key": i["key"], "link": i.get("link", ""), "case": m["case"],
                            "bug": {"tieu_de": i.get("summary", "")}, "loai_ban_goc": m["loai_ban"],
                            "package": m["package"]}
        elif i["key"] in cu:
            ra[i["key"]] = cu[i["key"]]
        else:
            ra[i["key"]] = {"key": i["key"], "link": i.get("link", ""), "case": "",
                            "bug": {"tieu_de": i.get("summary", "")}, "loai_ban_goc": ""}
    for k, u in cu.items():
        ra.setdefault(k, u)
    return list(ra.values())
