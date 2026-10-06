"""Doc ID ads tung vi tri THANG tu sheet "Check thong so KT" cua team QA.

Truoc day tool chi co ban chep tinh `data/ad_units.yaml` - va chi co Piclux.
Chay app khac thi tier high1/high2 khong co ID nao, dong ads khong quy duoc ve
vi tri, va mot dong "native hien thi" de bi cham bang ad cua vi tri khac (PASS
gia, do 2026-10-06). Nen moi luot tai ban MOI NHAT cua sheet.

Moi app mot tab (ADA895, AIP916...). Tab nao cung cung khuon (do 2026-10-06,
18 tab): dong "Package name | <package>" -> chon tab theo package, khong theo
ten tab. Muc "2. ID ads FO" ghi `<vi tri> | ca-app-pub-...`; muc resume ghi
nguoc `ca-app-pub-... | <vi tri>` -> doc cap o theo noi dung, khong theo cot.
"""

from __future__ import annotations

import re
from pathlib import Path

from . import tc_source
from .models import RcError

LINK = "https://docs.google.com/spreadsheets/d/14XivZl9VPAnyf8hYICgRh-TOUmkGTZDCqoyWmPM57hM/edit"
VI_TRI_RE = re.compile(r"^\d{3}[-_][a-z0-9_-]+$", re.I)
ID_RE = re.compile(r"^ca-app-pub-\d+/\d+$")


def doc_tab(path, package: str) -> dict[str, str]:
    """{id_<vi tri>: ID} cua tab co dong "Package name" = `package`. Khong co -> {}."""
    import openpyxl

    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        for ws in wb.worksheets:
            rows = [[str(v).strip() for v in r if v not in (None, "")]
                    for r in ws.iter_rows(values_only=True)]
            if not any(len(r) >= 2 and r[0].lower() == "package name" and r[1] == package
                       for r in rows):
                continue
            ra: dict[str, str] = {}
            for r in rows:
                vi = next((c for c in r if VI_TRI_RE.match(c)), "")
                ma = next((c for c in r if ID_RE.match(c)), "")
                if vi and ma:
                    # Sheet viet lan `-` va `_` -> dang key remote config `id_<vi_tri>`.
                    ra["id_" + vi.lower().replace("-", "_")] = ma
            return ra
        return {}
    finally:
        wb.close()


def tai(package: str, out_dir, link: str = LINK) -> tuple[dict[str, str], str]:
    """-> (bang ID, ghi chu). Tai hong thi dung ban da tai lan truoc (neu co)."""
    try:
        path = tc_source.tai_ve(link, out_dir)
        nguon = "sheet Check thông số KT (bản mới tải)"
    except RcError as exc:
        sheet_id = tc_source.SHEET_RE.search(link).group(1)
        cu = Path(out_dir) / f"tc-{sheet_id}.xlsx"
        if not cu.exists():
            return {}, f"không tải được sheet Check thông số KT: {exc}"
        path, nguon = cu, "sheet Check thông số KT (bản tải lần trước — lần này tải hỏng)"
    bang = doc_tab(path, package)
    if not bang:
        return {}, f"sheet Check thông số KT không có tab nào ghi package {package}"
    return bang, f"{nguon}: {len(bang)} vị trí"
