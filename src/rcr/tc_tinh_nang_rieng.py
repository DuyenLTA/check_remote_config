"""`--tc iaa` / `--tc gen-ngam`: bo TC tinh nang khong nam trong sheet TC chung.

- `iaa`: dung tu muc "3. ID ads inapp" cua tab app trong sheet "Check thong so KT" (QA dan kich ban IAA).
- `gen-ngam`: sheet TC gen ngam rieng (tab "TC Gen ngam" dung khuon bo TC, tab checklist cu tu bi bo qua).

Moi lenh (ca --gop / --tiep) tai lai sheet goc roi dung lai file `.xlsx` dung khuon bo TC (mot sheet
`Test Cases`) -> phan con lai cua rcr-check (chon case, dat RC, report, --gop) chay nhu bo TC thuong.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from . import ad_units_sheet, tc_iaa_tu_sheet_kt, tc_loader, tc_source
from .models import Case

NGUON = ("iaa", "gen-ngam")
# Sheet TC gen ngam QA gui 12/11/2026. Doi sheet thi dat RC_TC_GEN_NGAM (link cung khuon), khong sua code.
LINK_GEN_NGAM = "https://docs.google.com/spreadsheets/d/1FORGiI5X_N6HTmYyFdSiXCsAu7q91vTd59BfoGULT8c/edit"
HEADER = ("TC ID", "Feature", "Test Description", "Sub-scenario", "User State", "Test Data", "Precondition",
          "Action", "Expected Result")


def la_nguon(tc: str) -> bool:
    return (tc or "").strip().lower() in NGUON


def link_goc(tc: str) -> str:
    """Link sheet goc cua nguon (bien moi truong thang mac dinh)."""
    if tc.strip().lower() == "iaa":
        return os.environ.get("RC_AD_UNITS_SHEET") or ad_units_sheet.LINK
    return os.environ.get("RC_TC_GEN_NGAM") or LINK_GEN_NGAM


def _so(steps: tuple[str, ...]) -> str:
    return "\n".join(f"{i}. {s}" for i, s in enumerate(steps, 1))


def _dau_van(cases: list[Case]) -> list[list[str]]:
    """Noi dung case de so ban truoc / ban nay (file xlsx moi lan ghi khac byte du noi dung y het)."""
    return [[c.n, c.test_data, *c.actions, "|", *c.expects] for c in cases]


def ghi_xlsx(cases: list[Case], dich: Path) -> None:
    import openpyxl

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Test Cases"
    ws.append(HEADER)
    for c in cases:
        ws.append((c.n, c.feature, c.description, c.sub_scenario, c.user_state, c.test_data, c.precondition,
                   _so(c.actions), _so(c.expects)))
    dich.parent.mkdir(parents=True, exist_ok=True)
    wb.save(dich)


def dung(tc: str, package: str, out_dir) -> tuple[str, bool, str]:
    """-> (duong dan xlsx vua dung, noi dung case khac lan dung truoc?, link sheet goc). Loi -> RcError."""
    ten = tc.strip().lower()
    link = link_goc(ten)
    goc = tc_source.tai_ve(link, out_dir)
    if ten == "iaa":
        cases = tc_iaa_tu_sheet_kt.tu_workbook(goc, package)
    else:
        cases = tc_loader.load(goc)                  # sheet dau tien co header bo TC
    dich = Path(out_dir) / f"tc-{ten}-{package}.xlsx"
    dau = dich.with_suffix(".cases.json")
    moi = _dau_van(cases)
    cu = json.loads(dau.read_text(encoding="utf-8")) if dau.is_file() else None
    ghi_xlsx(cases, dich)
    dau.write_text(json.dumps(moi, ensure_ascii=False), encoding="utf-8")
    return str(dich), cu is not None and cu != moi, link
