"""`rcr-sdk-check`: cham checklist SDK Next-Gen (muc 1-4) bang code.

  rcr-sdk-check --package P [--muc 1,2,3,4] [--sdk 3.7.0] [--app-label "Ten 1.0"]
      thu bang chung tren may vao out/sdk-<pkg>-<gio>/ roi cham + xuat report
  rcr-sdk-check --cham-lai DIR
      cham lai tu log da thu (khong can may) - cung log, cung ket qua
  rcr-sdk-check --cham-tay DIR --ma EV-07 --ket KHOP|SAI --ly-do "..."
      ghi dong do tay (dong code tra DO_TAY), dung lai report

stdout: mot dong JSON {thu_muc, report, dem}. Log tien do ra stderr.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

from . import sdk_nextgen_cham, sdk_nextgen_report, sdk_nextgen_thu_log
from .adb_client import AdbClient
from .adb_parsers import AdbError
from .cli_check import _stdio_utf8, pick_serial
from .models import RcError


def _log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def _xuat(d: Path, data: dict) -> dict:
    sdk_nextgen_cham.ghi(d, data)
    report = sdk_nextgen_report.ghi(data, d / "report.html")
    return {"thu_muc": str(d), "report": str(report), "dem": sdk_nextgen_cham.dem(data)}


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
    return _xuat(d, sdk_nextgen_cham.cham_thu_muc(d))


def run(args) -> dict:
    if args.cham_lai:
        d = Path(args.cham_lai)
        cu = sdk_nextgen_cham.doc(d) if (d / sdk_nextgen_cham.KET_QUA).exists() else None
        return _xuat(d, sdk_nextgen_cham.giu_cham_tay(sdk_nextgen_cham.cham_thu_muc(d), cu))
    if args.cham_tay:
        d = Path(args.cham_tay)
        data = sdk_nextgen_cham.cham_tay(sdk_nextgen_cham.doc(d), args.ma, args.ket, args.ly_do)
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
