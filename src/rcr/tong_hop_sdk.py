"""Tab "Tong hop SDK x" cua sheet TC: kien thuc nen (ad load tai man nao, resume, OB5...) QA ghi de tool khong log
nham bug (user chot 06/11/2026). Ban tho tung tab luu o `sdk-check/references/tong-hop-sdk/<ver>.txt`; kien thuc
da doc nam o `sdk-check/references/logic-preload-load-ads-fo-co-ban.md`.

Moi luot chay so sheet vua tai voi ban tho da luu: tab moi / tab doi -> canh bao de Claude doc lai va cap nhat
kien thuc, roi `rcr-tong-hop --ghi` chot ban tho moi.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

THU_MUC = Path(__file__).resolve().parents[2] / "sdk-check" / "references" / "tong-hop-sdk"
TAB_RE = re.compile(r"^\s*t[ổo]ng\s+h[ợo]p\b", re.IGNORECASE)


def _ten_file(title: str) -> str:
    return re.sub(r"[^0-9A-Za-z.]+", "-", title.split("SDK", 1)[-1].strip()).strip("-") or "khac"


def doc_tabs(xlsx: str | Path) -> dict[str, str]:
    """{ten file: noi dung tho} cua moi tab "Tong hop ..." (o trong bo, giu vi tri cot bang ' | ')."""
    import openpyxl

    wb = openpyxl.load_workbook(xlsx, read_only=True, data_only=True)
    try:
        ra = {}
        for ws in wb.worksheets:
            if not TAB_RE.match(ws.title):
                continue
            dong = []
            for r in ws.iter_rows(values_only=True):
                o = ["" if c is None else str(c).strip() for c in r]
                while o and not o[-1]:
                    o.pop()
                if any(o):
                    dong.append(" | ".join(o))
            ra[_ten_file(ws.title)] = f"# {ws.title}\n" + "\n".join(dong) + "\n"
        return ra
    finally:
        wb.close()


def so_sanh(xlsx: str | Path, thu_muc: Path = THU_MUC) -> list[str]:
    """Tab Tong hop moi hoac doi so voi ban tho da luu -> danh sach mo ta; trong = da cap nhat het."""
    ra = []
    for ten, noi_dung in doc_tabs(xlsx).items():
        f = thu_muc / f"{ten}.txt"
        if not f.is_file():
            ra.append(f"moi: {ten}")
        elif f.read_text(encoding="utf-8") != noi_dung:
            ra.append(f"doi: {ten}")
    return ra


def ghi(xlsx: str | Path, thu_muc: Path = THU_MUC) -> list[str]:
    """Chot ban tho moi nhat cua moi tab Tong hop (goi SAU khi da cap nhat file kien thuc)."""
    thu_muc.mkdir(parents=True, exist_ok=True)
    tabs = doc_tabs(xlsx)
    for ten, noi_dung in tabs.items():
        (thu_muc / f"{ten}.txt").write_text(noi_dung, encoding="utf-8")
    return sorted(tabs)


def main() -> None:
    p = argparse.ArgumentParser(prog="rcr-tong-hop",
                                description="So / chot ban tho cac tab 'Tong hop SDK x' cua sheet TC")
    p.add_argument("--tc", required=True, help="link Google Sheet TC hoac file .xlsx")
    p.add_argument("--ghi", action="store_true", help="chot ban tho moi (sau khi da cap nhat file kien thuc)")
    p.add_argument("--out-dir", default="out")
    a = p.parse_args()
    from . import tc_source

    xlsx = tc_source.tai_ve(a.tc, a.out_dir)
    if a.ghi:
        print("da chot:", ", ".join(ghi(xlsx)))
    else:
        doi = so_sanh(xlsx)
        print("\n".join(doi) if doi else "cac tab Tong hop SDK khop ban da luu")


if __name__ == "__main__":
    main()
