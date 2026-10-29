"""`rcr-cai-build`: lay build tu App Tester (Firebase App Distribution) cai len may.

  rcr-cai-build --package P --version "4.3.0 (40)" --loai debug|release
      tai + cai dung release, xac nhan bang dumpsys
  rcr-cai-build --package P --version "4.3.0 (40)" --chi-kiem
      chi xem App Tester da co nhung ban nao cua version do, khong tai/cai

Giu khoa `out/.may-<serial>.lock` suot luot (chung voi bot) -> may khac van chay song song.
stdout: mot dong JSON. Log tien do / loi ra stderr.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from . import app_tester_ui, bot_hang_doi, cai_apk_tu_drive
from .adb_client import AdbClient
from .adb_parsers import AdbError
from .cli_check import _stdio_utf8, pick_serial
from .models import RcError


def _log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


async def _chay(args) -> dict:
    client = AdbClient(args.adb)
    serial = await pick_serial(client, args.serial)
    out = Path(args.out_dir)
    _log(f"May: {serial} · App: {args.package} · Version: {args.version} · "
         + ("chi kiem" if args.chi_kiem else f"cai ban {args.loai}"))
    with bot_hang_doi.giu_may(bot_hang_doi.khoa_may(out, serial)):
        if args.chi_kiem:
            return await app_tester_ui.kiem(client, serial, args.package, args.version, out)
        if args.apk_url:                 # ban debug QA gui link Drive: khong qua App Tester
            return await cai_apk_tu_drive.cai(client, serial, args.package, args.version, args.apk_url, out)
        return await app_tester_ui.cai(client, serial, args.package, args.version, args.loai, out)


def run(args) -> dict:
    if not args.chi_kiem and args.loai not in ("debug", "release"):
        raise RcError("Thiếu --loai debug|release (hoặc --chi-kiem)")
    return asyncio.run(_chay(args))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="rcr-cai-build", description=__doc__.split("\n\n")[0])
    p.add_argument("--package", required=True)
    p.add_argument("--version", required=True, help="đúng như App Tester ghi, vd '4.3.0 (40)'")
    p.add_argument("--loai", default="", help="debug | release")
    p.add_argument("--chi-kiem", action="store_true")
    p.add_argument("--apk-url", default="", help="link Google Drive cua APK (ai co link deu xem duoc) - tai + cai thay App Tester")
    p.add_argument("--serial", default=None)
    p.add_argument("--adb", default=None)
    p.add_argument("--out-dir", default="out")
    return p


def main(argv=None) -> int:
    _stdio_utf8()
    args = build_parser().parse_args(argv)
    try:
        print(json.dumps(run(args), ensure_ascii=False))
        return 0
    except (RcError, AdbError, app_tester_ui.LoiCai, BlockingIOError) as exc:
        _log(f"LOI: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
