"""Tach tin build cua dev tren Discord -> ma app, version, loai ban can cai, package.

Mau tin (do 2026-10-27, kenh build):
    @QA Ban build AIP882---AI-Video v4.3.0 (40) da duoc hoan thien. Please check
    apply tutorial 3.6.1 (revert next-gen)
    <link Drive>
Bot chi can ma app + version; link Drive chi de ASO submit nen bo qua.

Loai ban quyet dinh bang CHU next-gen trong tin, khong bang so tutorial: next-gen
ads va ban tutorial doc lap. Ban release khong debuggable -> chi cham duoc
checklist Next-Gen; moi nhanh khac phai patch Remote Config -> can ban debug.

Package tra tu sheet "Check thong so KT": tab trung ma app, dong "Package name".
Khong doan theo ten app trong tin.
"""

from __future__ import annotations

import re

# Dau noi giua ma va ten: dev go 1 hoac 3 gach; co tin khong co ten app
# ("Ban build AIP920 v1.6.0 (7)", do 2026-10-27).
DONG_DAU_RE = re.compile(
    r"B[ảa]n build\s+(?P<ma>[A-Z]{3}\d{3})(?:-+(?P<ten>.+?))?\s+v(?P<ver>\d+(?:\.\d+)+)\s*\((?P<code>\d+)\)",
    re.I,
)
REVERT_RE = re.compile(r"revert\s+next[\s-]?gen", re.I)
NEXT_GEN_RE = re.compile(r"next[\s-]?gen", re.I)
TUTORIAL_RE = re.compile(r"\b\d+\.\d+\.\d+\b")
LINK_RE = re.compile(r"https?://\S+")
# Dau dinh dang markdown Discord: dev go "Ban build **AIP920** v1.6.0 (7)" (do 2026-10-27).
MARKDOWN_RE = re.compile(r"\*\*|__|~~|\|\||`|\*")
# Tutorial 3.7.0 = Next-Gen (user chot 2026-10-27) - cham duoc tren ban release.
NEXT_GEN_TUTORIAL = "3.7.0"


def tach(text: str) -> dict | None:
    """{ma, ten, version, next_gen, tutorial} hoac None neu tin khong dung mau.

    `next_gen`: False khi "revert next-gen", True khi nhac next-gen, None khi khong nhac.
    `tutorial`: so x.y.z o phan ghi chu sau dong dau (bo link) - khong lay version build.
    """
    text = MARKDOWN_RE.sub("", text or "")
    m = DONG_DAU_RE.search(text)
    if not m:
        return None
    ghi_chu = LINK_RE.sub(" ", text[m.end():])
    if REVERT_RE.search(ghi_chu):
        next_gen = False
    elif NEXT_GEN_RE.search(ghi_chu):
        next_gen = True
    else:
        next_gen = None
    tut = TUTORIAL_RE.search(ghi_chu)
    return {
        "ma": m.group("ma").upper(),
        "ten": (m.group("ten") or "").strip(" -"),
        "version": f"{m.group('ver')} ({m.group('code')})",
        "next_gen": next_gen,
        "tutorial": tut.group(0) if tut else "",
    }


def loai_ban(tin: dict) -> str:
    """"release" khi tin ghi next-gen (hoac tutorial 3.7.0) ma khong revert, con lai "debug"."""
    if tin["next_gen"] is False:
        return "debug"
    if tin["next_gen"] or tin["tutorial"] == NEXT_GEN_TUTORIAL:
        return "release"
    return "debug"


def package_cua(path, ma: str) -> str:
    """Package o dong "Package name" cua tab ten `ma` trong sheet KT, "" neu khong co."""
    import openpyxl

    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        ws = next((w for w in wb.worksheets if w.title.strip().upper() == ma.upper()), None)
        if ws is None:
            return ""
        for r in ws.iter_rows(values_only=True):
            o = [str(v).strip() for v in r if v not in (None, "")]
            if len(o) >= 2 and o[0].lower() == "package name":
                return o[1]
        return ""
    finally:
        wb.close()
