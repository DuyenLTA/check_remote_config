"""Luot bot ket thuc LOI / HET_GIO ma khong co dong KET_QUA -> lay bug tu file luot (`*.luot.json`) de van co menu bug.

Menu bug cua bot dung tu `bugs` trong dong KET_QUA phien Claude ghi cuoi luot. Phien chet giua chung (AIP918 2.5.0
12/11/2026: 4 tieng roi Loi) thi mat het bug du tool da cham FAIL trong file luot -> QA khong thay menu. O day doc
cac file luot cua package ghi TRONG luot nay, lay case FAIL (ban ghi moi nhat cua moi case) lam bug. Day la FAIL do
TOOL cham, chua ai xem lai -> ghi ro trong bug de QA tick ky truoc khi log Jira.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from .bot_chay_claude import doc_bugs

log = logging.getLogger(__name__)

TRANG_THAI_CUU = ("LOI", "HET_GIO")
GHI_CHU = "Bug lấy từ file lượt (phiên Claude dừng trước khi ghi kết quả) — FAIL do tool chấm, chưa ai xem lại."
BUOC_BO = ("chup_man", "walk", "noop")


def _file_luot(out: Path, package: str, tu_luc: float) -> list[Path]:
    """File luot cua package ghi tu `tu_luc`, cu truoc moi sau (ban ghi sau de len ban ghi truoc)."""
    ds = []
    for f in Path(out).glob("*.luot.json"):
        try:
            if package in f.name and f.stat().st_mtime >= tu_luc:
                ds.append(f)
        except OSError:
            continue
    return sorted(ds, key=lambda f: f.stat().st_mtime)


def _bug(r: dict) -> dict:
    sai = [ln for ln in r.get("lines") or [] if ln.get("v") == "FAIL"]
    buoc = [str(s.get("s") or "") for s in r.get("steps") or [] if s.get("k") not in BUOC_BO and s.get("s")]
    nhan = str(r.get("label") or r.get("key") or "").strip()
    return {
        "case": str(r.get("key") or nhan),
        "tieu_de": f"{nhan}: {sai[0].get('e', '')}" if sai else nhan,
        "precondition": str(r.get("precondition") or ""),
        "buoc": "\n".join(f"{i}. {b}" for i, b in enumerate(buoc, 1)),
        "expected": "\n".join(str(ln.get("e") or "") for ln in sai),
        "thuc_te": "\n".join(str(ln.get("r") or "") for ln in sai) + f"\n({GHI_CHU})",
        "muc_do": "",
    }


def bug_tu_file_luot(out: Path, package: str, tu_luc: float) -> tuple[list[dict], str]:
    """-> (bug, duong dan report cua file luot moi nhat co report)."""
    cuoi: dict[str, dict] = {}
    report = ""
    for f in _file_luot(out, package, tu_luc):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            log.warning("khong doc duoc file luot %s", f)
            continue
        if d.get("package") not in (None, package):
            continue
        for r in d.get("records") or []:
            khoa = str(r.get("key") or r.get("label") or "")
            if khoa:
                cuoi[khoa] = r
        rp = Path(str(d.get("report") or ""))
        rp = rp if rp.is_absolute() else Path(out).parent / rp
        if rp.suffix == ".html" and rp.is_file():
            report = str(rp.resolve())
    return doc_bugs([_bug(r) for r in cuoi.values() if r.get("verdict") == "FAIL"]), report


def cuu_ket_qua(kq: dict, out: Path, package: str, tu_luc: float | None) -> dict:
    """kq luot LOI/HET_GIO khong co bug -> bo sung bug (va link report neu chua co) tu file luot. Khong thi giu."""
    if kq.get("bugs") or kq.get("trang_thai") not in TRANG_THAI_CUU or not tu_luc:
        return kq
    bugs, report = bug_tu_file_luot(out, package, tu_luc)
    if not bugs and not report:
        return kq
    ra = {**kq, "bugs": bugs}
    if report and not kq.get("link"):
        ra["link"] = report
    if bugs:
        ra["tom_tat"] = (f"{kq.get('tom_tat') or ''}\n{len(bugs)} case FAIL trong file lượt. {GHI_CHU}").strip()
    return ra


def main(argv: list[str] | None = None) -> int:
    """Cuu menu bug cho luot da bao xong ma mat bug: `python -m rcr.bot_bug_tu_file_luot --package P --tu "<gio>"`
    in bug lay tu file luot; them `--tha` de tha vao hop thu bug -> bot chinh dat menu tick len tin cua build."""
    import argparse
    import sys
    from datetime import datetime

    from . import bot_hop_thu_bug

    p = argparse.ArgumentParser(prog="rcr-bug-tu-luot", description="Lay case FAIL trong file luot lam bug")
    p.add_argument("--package", required=True)
    p.add_argument("--tu", required=True, help="gio bat dau luot, vd '2026-11-12 10:25'")
    p.add_argument("--version", default="", help="tim tin build theo version, vd '2.5.0 (23)'")
    p.add_argument("--msg-id", type=int, default=None, help="tin cua build o kenh QA (khong co thi tim theo package)")
    p.add_argument("--link", default="", help="link artifact report https (khong co thi de trong)")
    p.add_argument("--tha", action="store_true", help="tha vao hop thu bug cho bot chinh dang menu")
    p.add_argument("--out", default=str(Path(__file__).resolve().parents[2] / "out"))
    a = p.parse_args(argv)
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    tu = datetime.strptime(a.tu, "%Y-%m-%d %H:%M").timestamp()
    bugs, report = bug_tu_file_luot(Path(a.out), a.package, tu)
    print(json.dumps({"bugs": bugs, "report": report}, ensure_ascii=False, indent=1))
    if not bugs:
        print("Khong co case FAIL nao trong file luot tu gio do.", file=sys.stderr)
        return 1
    if a.tha:
        f = bot_hop_thu_bug.tha_vao_hop(Path(a.out), bugs, a.link if a.link.startswith("https://") else "",
                                        a.msg_id, a.package, a.version)
        print(f"Da tha {len(bugs)} bug vao {f} - bot chinh dang menu trong ~20s.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
