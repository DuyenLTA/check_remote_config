"""`rcr-sdk-check`: cham checklist SDK Next-Gen (muc 1-4) bang code.

  rcr-sdk-check --package P [--muc 1,2,3,4] [--sdk 3.7.0] [--app-label "Ten 1.0"]
      thu bang chung tren may vao out/sdk-<pkg>-<gio>/ roi cham + xuat report
  rcr-sdk-check --cham-lai DIR
      cham lai tu log da thu (khong can may) - cung log, cung ket qua
  rcr-sdk-check --cham-tay DIR --ma HV-01 --ket KHOP|SAI|KHONG_AP_DUNG --buoc inter=ok --buoc native=sai --buoc "banner=khong:..."
                --ly-do "..." [--khong-tai-hien "..."]
      ghi dong do tay (dong code tra DO_TAY), dung lai report; KHONG_AP_DUNG = muc ngoai pham vi / N/A.
      Buoc bat buoc tung dong: `sdk_nextgen_buoc_do_tay.BUOC` (stdout `can_do_tay` liet ke dong + buoc con thieu).
  --gop-luot DIR1,DIR2   (kem --package hoac --cham-lai) gop luot cu cung build: dong do tay lay tu luot cu,
      Sai luot cu giu nguyen. Luot moi tu tim luot cu cung package + phien ban trong --out-dir.

stdout: mot dong JSON {thu_muc, report, dem}. Log tien do ra stderr.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
import time
from datetime import date, datetime
from pathlib import Path

from . import (audit_tom_tat, report_tab_audit, sdk_nextgen_buoc_do_tay, sdk_nextgen_cham, sdk_nextgen_gop_luot,
               sdk_nextgen_report, sdk_nextgen_thu_log)
from .adb_client import AdbClient
from .adb_parsers import AdbError
from .cli_check import _stdio_utf8, pick_serial
from .models import RcError


def _log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def _ngay_chay(d: Path) -> date:
    """Ngay luot thu bang chung: tu ten thu muc sdk-<pkg>-YYMMDD-HHMMSS (khong doi khi dung lai report)."""
    m = re.search(r"-(\d{6})-\d{6}$", d.name)
    try:
        return datetime.strptime(m.group(1), "%y%m%d").date() if m else date.today()
    except ValueError:
        return date.today()


def _audit(d: Path, data: dict) -> dict | None:
    """Audit ID ads cua app cho report. Ban da luu trong ket-qua.json (kem audit.html trong thu muc luot)
    duoc uu tien: --cham-tay / --cham-lai dung lai dung noi dung cu du trang audit sau do bi audit ban
    build khac ghi de. Chua co ban luu thi lay audit cung ngay voi luot chay va copy vao thu muc luot."""
    cu = None
    if (d / sdk_nextgen_cham.KET_QUA).exists():
        try:
            cu = sdk_nextgen_cham.doc(d)["meta"].get("audit")
        except (OSError, ValueError, KeyError):
            cu = None
    if cu and (d / report_tab_audit.BAN_SAO).is_file():
        return cu
    tt = audit_tom_tat.tim(data["meta"].get("package") or "", ngay=_ngay_chay(d)) or cu
    return report_tab_audit.luu_ban_sao(tt, d)


def _xuat(d: Path, data: dict) -> dict:
    data["meta"]["audit"] = _audit(d, data)
    sdk_nextgen_cham.ghi(d, data)
    report = sdk_nextgen_report.ghi(data, d / "report.html")
    return {"thu_muc": str(d), "report": str(report), "dem": sdk_nextgen_cham.dem(data),
            "can_do_tay": sdk_nextgen_buoc_do_tay.goi_y(data["ket_qua"]),
            "lech": [x["ma"] for x in sdk_nextgen_gop_luot.lech(data)]}


def _gop(d: Path, data: dict, args) -> dict:
    """Gop luot cu cung build: --gop-luot ghi ro, cong luot cung package + phien ban + sha APK tim trong --out-dir."""
    g = sdk_nextgen_gop_luot
    pkg = data["meta"]["package"]
    cu = [g.doc_luot(Path(x.strip()), pkg) for x in (args.gop_luot or "").split(",")
          if x.strip() and not g.cung_thu_muc(x.strip(), str(d))]
    cu += [l for l in g.tim(Path(args.out_dir), pkg, g.khoa_build(data["meta"]), tru=d)
           if not any(g.cung_thu_muc(l["thu_muc"], c["thu_muc"]) for c in cu)]
    data, lay = sdk_nextgen_gop_luot.gop(data, cu)
    if cu:
        _log(f"Gộp {len(cu)} lượt cũ cùng build: " + ", ".join(l["thu_muc"] for l in cu)
             + (f" · lấy kết quả đo tay cũ cho {', '.join(lay)}" if lay else ""))
    return data


async def _thu(args) -> dict:
    client = AdbClient(args.adb)
    serial = await pick_serial(client, args.serial)
    muc = {m.strip() for m in args.muc.split(",") if m.strip()}
    if not muc or not muc <= {"1", "2", "3", "4"}:
        raise RcError("--muc nhận 1, 2, 3, 4 (vd 1,2,3,4)")
    d = Path(args.out_dir) / f"sdk-{args.package}-{time.strftime('%y%m%d-%H%M%S')}"
    _log(f"May: {serial} · App: {args.package} · Muc: {','.join(sorted(muc))} · Thu muc: {d}")
    bc = await sdk_nextgen_thu_log.thu(client, serial, args.package, d, muc, _log)
    if any(bc.get("ad_click", {}).values()):
        _log(f"CHU Y ad_click trong luot: {bc['ad_click']} - kiem ad test hay ad that truoc khi bao")
    bc_file = d / "bang-chung.json"
    bc.update(sdk=args.sdk, app_label=args.app_label)
    bc_file.write_text(json.dumps(bc, ensure_ascii=False, indent=1), "utf-8")
    return _xuat(d, _gop(d, sdk_nextgen_cham.cham_thu_muc(d), args))


def run(args) -> dict:
    if args.cham_lai:
        d = Path(args.cham_lai)
        cu = sdk_nextgen_cham.doc(d) if (d / sdk_nextgen_cham.KET_QUA).exists() else None
        data = sdk_nextgen_cham.giu_cham_tay(sdk_nextgen_cham.cham_thu_muc(d), cu)
        return _xuat(d, _gop(d, data, args) if args.gop_luot else data)
    if args.cham_tay:
        d = Path(args.cham_tay)
        data = sdk_nextgen_cham.cham_tay(sdk_nextgen_cham.doc(d), args.ma, args.ket, args.ly_do,
                                         buoc=sdk_nextgen_buoc_do_tay.doc_buoc(args.buoc),
                                         khong_tai_hien=args.khong_tai_hien)
        return _xuat(d, data)
    if not args.package:
        raise RcError("Thiếu --package (hoặc --cham-lai / --cham-tay DIR)")
    return asyncio.run(_thu(args))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="rcr-sdk-check", description=__doc__.split("\n\n")[0])
    p.add_argument("--package", default="")
    p.add_argument("--muc", default="1,2,3,4", help="mục checklist: 1 SDK/build, 2 hiển thị, 3 event, 4 KT/MED/CMP/HV")
    p.add_argument("--sdk", default="", help="bản SDK FO in lên report (lấy từ dòng 'Bản SDK FO' của --preflight)")
    p.add_argument("--app-label", default="")
    p.add_argument("--serial", default=None)
    p.add_argument("--adb", default=None)
    p.add_argument("--out-dir", default="out")
    p.add_argument("--cham-lai", default="", metavar="DIR")
    p.add_argument("--cham-tay", default="", metavar="DIR")
    p.add_argument("--ma", default="")
    p.add_argument("--ket", default="")
    p.add_argument("--ly-do", default="")
    p.add_argument("--buoc", action="append", default=[], help="id=ok|sai|khong:<lý do>, mỗi bước một --buoc")
    p.add_argument("--khong-tai-hien", default="", help="đổi dòng đã Sai: đã chạy lại bước tái hiện, ghi kết quả")
    p.add_argument("--gop-luot", default="", metavar="DIR1,DIR2", help="gộp lượt cũ cùng build")
    return p


def main(argv=None) -> int:
    _stdio_utf8()
    args = build_parser().parse_args(argv)
    try:
        print(json.dumps(run(args), ensure_ascii=False))
        return 0
    except (RcError, AdbError) as exc:
        _log(f"LOI: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
