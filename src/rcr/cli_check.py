"""CLI mot luot: doc baseline -> nap bo testcase -> dat config cua 1 case.

Sinh ra de slash command `/rc-check` goi duoc ma khong phai mo web UI:
stdout la DUNG MOT DONG JSON, tien do ra stderr.

CLI NAY KHONG CHAM PASS/FAIL. No dat duoc config va xac nhan config con song
sau khi mo lai app - het. Cham hanh vi app la phase 5; goi "PASS" o day la pass
gia vi chua ai nhin man hinh app.

Ket qua cua buoc dat config chi co 3 gia tri:
    CONFIG_OK    - gia tri song qua lan mo app, test duoc tiep (bang tay)
    BLOCKED      - app fetch de mat patch, CHUA test duoc. Khong phai app sai.
    KEY_NOT_USED - app khong doc key do (khong co chuoi trong DEX) -> cham kieu
                   gi cung ra PASS GIA. Khong mo app, khong patch.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

from . import case_run, rc_baseline, run_batch, sdk_probe, tc_select
from .adb_client import AdbClient
from .adb_parsers import AdbError
from .models import RcError

# Snapshot config goc nam ngoai git (xem .gitignore) - no la anh chup mot may cu the.
DEFAULT_OUT = Path(__file__).resolve().parents[2] / "out"


def _log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


async def pick_serial(client, wanted: str | None) -> str:
    devices = [d for d in await client.devices() if d.ready]
    if wanted:
        if wanted not in [d.serial for d in devices]:
            raise AdbError(f"Khong thay may {wanted} o trang thai `device`.")
        return wanted
    if not devices:
        raise AdbError("Khong co may nao san sang. Cam cap, bat USB debugging, bam Allow.")
    if len(devices) > 1:
        names = ", ".join(f"{d.serial} ({d.label})" for d in devices)
        raise AdbError(f"Co {len(devices)} may - phai chi dinh --serial: {names}")
    return devices[0].serial


def parse_sets(pairs: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for raw in pairs:
        if "=" not in raw:
            raise RcError(f"--set phai co dang key=value, nhan duoc: {raw!r}")
        key, value = raw.split("=", 1)
        out[key.strip()] = value.strip()
    return out


async def run(args: argparse.Namespace) -> dict:
    client = AdbClient(args.adb)
    serial = await pick_serial(client, args.serial)
    _log(f"May: {serial} · App: {args.package}")

    if args.restore:
        _log("Tra config ve ban da luu o luot --keep truoc...")
        return {"serial": serial, "package": args.package,
                **await case_run.restore_saved(client, args.package, serial, args.out_dir)}

    _log("Doc baseline...")
    baseline = await rc_baseline.read(client, serial, args.package)
    _log(
        f"  {len(baseline.configs)} key remote config, "
        f"{len(baseline.mirrored_keys)} key bi mirror, duong ghi {baseline.write_mode}"
    )

    out: dict = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "serial": serial,
        "package": args.package,
        "baseline": baseline.summary,
    }

    runs: tuple[dict[str, str], ...] = ()
    # `--fresh` cho duong --set: khong co file TC thi khong co Precondition de doc.
    precondition = "first open" if args.fresh else ""
    steps: tuple[str, ...] = ()
    expects: tuple[str, ...] = ()
    if args.set:
        runs = (parse_sets(args.set),)
    if args.tc:
        sdk, source = args.sdk, "tham so --sdk"
        if not sdk and not args.tab and tc_select.needs_sdk(Path(args.tc)):
            # Bo chung chia tab theo ban SDK - do that con hon bat nguoi go tay,
            # go nham ban la cham bang TC cua ban khac ma khong ai biet.
            _log("Bo TC chung - do ban SDK First Open tu logcat...")
            probe = await sdk_probe.detect(client, serial, args.package)
            sdk, source = probe["version"], probe["source"]
            _log(f"  SDK FO: {sdk} ({source})")
        rows, runnable, notes = tc_select.load_cases(args.tc, baseline, sdk, args.tab)
        out["tc"] = {
            "file": args.tc, "sdk": sdk, "sdk_source": source, "notes": notes,
            "total": len(rows), "runnable": len(runnable), "cases": rows,
        }
        _log(f"Bo TC: {len(rows)} case, {len(runnable)} case tool chay duoc")
        for note in notes:
            _log(f"  ghi chu: {note}")
        if args.case:
            out["cases"] = await run_batch.run_cases(
                client, baseline, args, runnable, rows, out["tc"], _log
            )
            return out
    elif args.case:
        raise RcError("--case can di kem --tc <file.xlsx>.")

    if runs:
        _log(f"Chay (--set) - {len(runs)} luot:")
        result, _ = await case_run.run_case(
            client, baseline, runs, precondition, steps, expects,
            keep=args.keep, out_dir=args.out_dir, dex=not args.no_dex_check, log_fn=_log,
        )
        out["run"] = {"case": "", **result}
    return out


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="rcr-check",
        description="Doc baseline remote config, nap bo testcase, dat config cua 1 case.",
    )
    p.add_argument("--package", required=True, help="package id cua app")
    p.add_argument("--serial", help="serial may (bat buoc khi cam nhieu may)")
    p.add_argument("--tc", help="file testcase .xlsx (bo chung nhieu tab hoac 1 sheet)")
    p.add_argument("--sdk", default="",
                   help="ban SDK FO cua app, vd 3.2.0 - mac dinh tu do tu logcat")
    p.add_argument("--tab", default="",
                   help="chi chay dung mot tab, vd `--tab 3.4.0` (khong keo theo base + delta)")
    p.add_argument("--case",
                   help="case can chay: `3.2.0#12` hoac `12` neu so do chi co o mot tab")
    p.add_argument("--set", action="append", metavar="KEY=VALUE",
                   help="dat thang key/value, khong can file TC (lap lai duoc)")
    p.add_argument("--keep", action="store_true",
                   help="GIU config da dat de tu mo app xem (mac dinh: tra ve nguyen trang)")
    p.add_argument("--restore", action="store_true",
                   help="tra config ve ban da luu o luot --keep truoc do")
    p.add_argument("--out-dir", default=str(DEFAULT_OUT),
                   help=f"noi luu snapshot config goc (mac dinh {DEFAULT_OUT})")
    p.add_argument("--no-actions", action="store_true",
                   help="chi dat config, khong lai app qua cac buoc Action cua case")
    p.add_argument("--fresh", action="store_true",
                   help="ep app ve trang thai chua tung mo (reset mem, hoac pm clear)")
    p.add_argument("--no-dex-check", action="store_true",
                   help="bo buoc soi key trong DEX (nhanh hon, nhung co the cham ra PASS gia)")
    p.add_argument("--app-label", default="",
                   help="ten app hien tren tieu de report, vd `Piclux 2.8.0`")
    p.add_argument("--report", default="",
                   help="ghi report HTML tu chua (kem anh tung buoc) ra duong dan nay")
    p.add_argument("--adb", help="duong dan adb neu khong nam trong PATH")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = asyncio.run(run(args))
    except (AdbError, RcError) as exc:
        _log(f"LOI: {exc}")
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
