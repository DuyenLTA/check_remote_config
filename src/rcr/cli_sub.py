"""`rcr-sub`: cong cu tat dinh cho check sub Android - lenh `/sub-check` (Claude) goi tung buoc.

  rcr-sub tc [--chon 1,2,89]                       bo TC sub (tai sheet moi nhat) theo lich chay, JSON
  rcr-sub profile --package P [--ghi '<json>']     xem / ghi profile app (duong vao Paywall, dau hieu Premium...)
  rcr-sub ve-home --serial S --package P           mo app (neu can) va lai qua FO toi Home
  rcr-sub paywall --serial S --package P           ve Home + mo Paywall (theo profile) va doc goi / nut
  rcr-sub mua --serial S --package P --goi weekly [--the approves|declines|slow] [--khong-xac-nhan] [--anh-dir D]
  rcr-sub play --serial S [--package P --sku K]    doc trang Subscriptions / Manage subscription
  rcr-sub cancel|resubscribe --serial S --package P --sku K
  rcr-sub doi-the --serial S --package P --sku K --the declines
  rcr-sub cho-het-ky --serial S --package P --sku K [--toi-da 2400]
  rcr-sub mo-lanh --serial S --package P           kill + mo app, doc log billing -> premium true/false
  rcr-sub may-bay --serial S bat|tat
  rcr-sub report <luot.json> --out <file.html>

Lenh co may giu khoa `out/.may-<serial>.lock` (chung voi bot) suot buoc. stdout: mot dong JSON.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from . import bot_hang_doi, sub_play_store as ps, sub_report, sub_tc
from . import sub_thao_tac as t
from .adb_client import AdbClient
from .adb_parsers import AdbError
from .cli_check import _stdio_utf8, pick_serial
from .models import RcError

LENH_MAY = {"ve-home", "paywall", "mua", "play", "cancel", "resubscribe", "doi-the", "cho-het-ky", "mo-lanh", "may-bay"}


async def _chay_may(args) -> dict:
    client = AdbClient(args.adb)
    serial = await pick_serial(client, args.serial)
    with bot_hang_doi.giu_may(bot_hang_doi.khoa_may(Path(args.out_dir), serial)):
        if args.lenh == "ve-home":
            return await t.ve_home(client, serial, args.package)
        if args.lenh == "paywall":
            return await t.mo_paywall(client, serial, args.package)
        if args.lenh == "mua":
            return await t.mua(client, serial, args.package, args.goi, args.the, not args.khong_xac_nhan,
                               Path(args.anh_dir) if args.anh_dir else None)
        if args.lenh == "play":
            return await ps.mo_play(client, serial, args.package or "", args.sku or "")
        if args.lenh == "cancel":
            return await ps.cancel_play(client, serial, args.package, args.sku)
        if args.lenh == "resubscribe":
            return await ps.resubscribe(client, serial, args.package, args.sku)
        if args.lenh == "doi-the":
            return await ps.doi_the_play(client, serial, args.package, args.sku, args.the)
        if args.lenh == "cho-het-ky":
            return await ps.cho_het_ky(client, serial, args.package, args.sku, args.toi_da)
        if args.lenh == "mo-lanh":
            return await t.mo_lanh(client, serial, args.package)
        await t.may_bay(client, serial, args.trang_thai == "bat")
        return {"may_bay": args.trang_thai}


def run(args) -> dict | list:
    if args.lenh == "tc":
        chon = {s.strip() for s in args.chon.split(",")} if args.chon else None
        return sub_tc.lich(sub_tc.tai(Path(args.out_dir)), chon)
    if args.lenh == "profile":
        if args.ghi:
            return {"da_ghi": str(t.ghi_profile(args.package, json.loads(args.ghi)))}
        return t.doc_profile(args.package) or {"profile": None}
    if args.lenh == "report":
        return {"report": str(sub_report.ghi(Path(args.luot), Path(args.out)))}
    return asyncio.run(_chay_may(args))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="rcr-sub", description=__doc__.split("\n\n")[0])
    p.add_argument("lenh", choices=sorted(LENH_MAY | {"tc", "profile", "report"}))
    p.add_argument("trang_thai", nargs="?", choices=("bat", "tat"), help="may-bay: bat | tat")
    p.add_argument("--serial", default=None)
    p.add_argument("--package", default="")
    p.add_argument("--sku", default="")
    p.add_argument("--goi", default="weekly", choices=("weekly", "monthly", "yearly"))
    p.add_argument("--the", default="approves", choices=("approves", "declines", "slow"))
    p.add_argument("--khong-xac-nhan", action="store_true", help="mo popup Google Play roi dong, khong mua")
    p.add_argument("--anh-dir", default="")
    p.add_argument("--toi-da", type=int, default=40 * 60)
    p.add_argument("--chon", default="", help="tc: chi cac so TC nay (phay ngan cach)")
    p.add_argument("--ghi", default="", help="profile: JSON profile can ghi")
    p.add_argument("--luot", default="", help="report: file luot JSON")
    p.add_argument("--out", default="", help="report: file HTML ra")
    p.add_argument("--adb", default=None)
    p.add_argument("--out-dir", default="out")
    return p


def main(argv=None) -> int:
    _stdio_utf8()
    args = build_parser().parse_args(argv)
    if args.lenh in LENH_MAY - {"may-bay", "play"} and not args.package:
        print("LOI: thiếu --package", file=sys.stderr)
        return 2
    if args.lenh in ("cancel", "resubscribe", "doi-the", "cho-het-ky") and not args.sku:
        print("LOI: thiếu --sku (đọc từ `rcr-sub mua` → log.sku_mua)", file=sys.stderr)
        return 2
    try:
        print(json.dumps(run(args), ensure_ascii=False, default=str))
        return 0
    except (RcError, AdbError, BlockingIOError, ValueError) as exc:
        print(f"LOI: {exc}", file=sys.stderr)
        return 1
