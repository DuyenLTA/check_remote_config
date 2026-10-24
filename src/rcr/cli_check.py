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

from . import (
    ad_units, case_run, cham_tay, luot_file, preflight, rc_baseline, run_batch, sdk_probe, discord_notify,
    discord_run_message, tc_select, tc_source,
)
from .adb_client import AdbClient
from .adb_parsers import AdbError
from .models import RcError

# `--case all`: moi case tool chay duoc trong tab da chon.
TAT_CA = "all"
# Sheet TC chung moi ban SDK - mac dinh cua `--khong-claude` khi khong truyen --tc.
TC_MAC_DINH = "https://docs.google.com/spreadsheets/d/1sNFXM7oGzx_addpimZL7RYk2rXpRs_We6YUHpdtWSqU/edit"

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


def _notify_run(args: argparse.Namespace, out: dict, started: float) -> None:
    """Mot tin Discord cho ca luot. Hong gi cung khong duoc doi stdout / exit code."""
    try:
        tc = out.get("tc") or {}
        summary = discord_run_message.summarize(
            out.get("cases") or [], app=args.app_label, package=args.package,
            sdk=tc.get("sdk") or "", duration_s=time.monotonic() - started,
            report=args.report, khong_claude=args.khong_claude)
        kind, title, lines, action = discord_run_message.build_run_message(summary)
        # Khong co Claude publish artifact: dinh kem chinh file report.
        dinh_kem = Path(args.report) if args.khong_claude and args.report else None
        discord_notify.send(kind, title, lines, action, file=dinh_kem)
    except Exception as exc:  # noqa: BLE001 - thong bao la tien nghi
        _log(f"discord: không dựng được thông báo ({type(exc).__name__})")


def dung_lai_report(args: argparse.Namespace) -> dict:
    """`--gop a.json --gop b.json` khong kem --case: gop record roi dung lai report, KHONG can may."""
    meta, records = luot_file.doc_nhieu(args.gop, args.package)
    report = args.report or str(
        Path(args.out_dir) / f"rc-{args.package}-gop-{time.strftime('%y%m%d-%H%M%S')}.html")
    tc = meta.get("tc") or {}
    run_batch.ghi_report(luot_file.baseline_tu(meta), tc, records,
                         args.app_label or meta.get("app_label", ""), report, _log)
    path = luot_file.duong_dan(report, args.out_dir, args.package)
    luot_file.ghi(path, {**meta, "report": report, "gop_tu": args.gop}, records, True)
    _log(f"Gộp {len(args.gop)} file → {len(records)} case. File lượt: {path}")
    return {"package": args.package, "tc": tc, "cases": records, "report": report, "luot": str(path)}


# Co doi cach chay case - luot tiep phai giong luot dau, khong thi mot report tron hai kieu.
CO_GIU_KHI_TIEP = ("no_walk", "full_walk", "no_actions", "fresh", "no_dex_check", "keep")


def nap_tiep(args: argparse.Namespace) -> list[dict]:
    """`--tiep <file>`: lay lai tham so cua luot bi tat, tra record da xong."""
    meta = luot_file.doc(args.tiep, args.package)
    args.case = args.case or meta.get("case_list", "")
    args.tc = args.tc or meta.get("tc_nguon", "")
    args.tab = args.tab or meta.get("tab", "")
    args.report = args.report or meta.get("report", "")
    args.app_label = args.app_label or meta.get("app_label", "")
    # Ban SDK do lai co the ra tab khac -> nua sau cua luot cham bang TC cua ban khac.
    args.sdk = args.sdk or meta.get("sdk", "")
    for co in CO_GIU_KHI_TIEP:
        setattr(args, co, getattr(args, co) or bool((meta.get("co") or {}).get(co)))
    if not args.case or not args.tc:
        raise RcError(f"File {args.tiep} thiếu danh sách case / bộ TC - truyền --case và --tc")
    return meta["records"]


async def run(args: argparse.Namespace) -> dict:
    started = time.monotonic()
    if args.cham_tay:
        return cham_tay.chay(args, _log)
    if args.gop and not args.case and not args.tiep:
        return dung_lai_report(args)
    goc_tiep = nap_tiep(args) if args.tiep else []
    client = AdbClient(args.adb)
    serial = await pick_serial(client, args.serial)
    _log(f"May: {serial} · App: {args.package}")

    if args.preflight:
        _log("Kiem dieu kien truoc khi chay...")
        kq = await preflight.chay(client, serial, args.package, args.tc or TC_MAC_DINH, args.out_dir)
        preflight.in_bang(kq, _log)
        return {"serial": serial, "package": args.package, "preflight": kq}

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

    if args.case or args.set:
        # ID ads tung vi tri (ca tier high1/high2 RC khong khai) doc thang tu
        # sheet "Check thong so KT", tab chon theo package - de quy request
        # trong log ve DUNG vi tri, khong de ad cua vi tri khac tinh nham.
        ad_units.nap_sheet(args.package, args.out_dir, _log)

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
        tc_nguon = args.tc
        if tc_source.la_link(args.tc):
            _log("Tai bo TC moi nhat tu Google Sheet...")
            out["tc_link"] = args.tc
            args.tc = tc_source.tai_ve(args.tc, args.out_dir)
        sdk, source = args.sdk, "tham so --sdk"
        # Bo TC mot sheet khong can ban SDK de CHON tab, nhung report van phai
        # noi duoc no do ban nao - do tu logcat roi chi dung de hien.
        chi_de_hien = not tc_select.needs_sdk(Path(args.tc))
        if not sdk and not args.tab:
            # Bo chung chia tab theo ban SDK - do that con hon bat nguoi go tay,
            # go nham ban la cham bang TC cua ban khac ma khong ai biet.
            #
            # Bo mot sheet thi ban SDK chi de in len report: luc do KHONG duoc
            # mo lai app chi de doc mot dong log - do la mot luot khoi dong
            # thua cho moi lan chay. Soi buffer co san, khong thay thi de trong.
            _log("Do ban SDK First Open tu logcat..."
                 + (" (chi de in len report)" if chi_de_hien else ""))
            try:
                probe = await sdk_probe.detect(
                    client, serial, args.package, relaunch=not chi_de_hien)
                sdk, source = probe["version"], probe["source"]
                _log(f"  SDK FO: {sdk} ({source})")
            except AdbError:
                if not chi_de_hien:
                    raise
                source = "khong doc duoc tu buffer logcat"
                _log("  khong doc duoc ban SDK - de trong tren report")
        # Ban do duoc chi de hien thi thi KHONG duoc dung de chon tab: bo mot
        # sheet von khong chia ban, truyen vao la doi cach chon case.
        rows, runnable, notes = tc_select.load_cases(
            args.tc, baseline, "" if chi_de_hien else sdk, args.tab)
        out["tc"] = {
            "file": args.tc, "sdk": sdk, "sdk_source": source, "notes": notes,
            "total": len(rows), "runnable": len(runnable), "cases": rows,
        }
        _log(f"Bo TC: {len(rows)} case, {len(runnable)} case tool chay duoc")
        for note in notes:
            _log(f"  ghi chu: {note}")
        if (args.case or "").strip().lower() == TAT_CA:
            # Chay khong Claude: khong ai chon tung case, chay het case tool chay
            # duoc theo dung thu tu trong bo TC.
            args.case = ",".join(runnable)
            _log(f"--case all: chay {len(runnable)} case")
            if not runnable:
                raise RcError("--case all: bo TC khong co case nao tool chay duoc.")
        if args.case:
            # File dang chay tiep la moi nhat -> dung SAU de thang cac file --gop.
            goc = (luot_file.doc_nhieu(args.gop, args.package)[1] if args.gop else []) + goc_tiep
            # Luot tiep ghi vao CHINH file cu: chay tiep may lan van mot file.
            path = Path(args.tiep) if args.tiep else luot_file.duong_dan(
                args.report, args.out_dir, args.package)
            args.luot_path = out["luot"] = str(path)
            _log(f"Ghi kết quả sau mỗi case vào {path}")
            meta = {
                "generated_at": out["generated_at"], "package": args.package, "serial": serial,
                "tc_nguon": tc_nguon, "tc": out["tc"], "tab": args.tab, "case_list": args.case,
                "report": args.report, "app_label": args.app_label, "sdk": args.sdk or sdk,
                "co": {co: getattr(args, co) for co in CO_GIU_KHI_TIEP},
                "baseline_tom": luot_file.tom_baseline(baseline),
            }
            out["cases"] = await run_batch.run_cases(
                client, baseline, args, runnable, rows, out["tc"], _log,
                goc=goc, bo_qua=luot_file.da_xong(goc_tiep),
                luot={"path": path, "meta": meta},
            )
            # Duong dan report phai nam trong JSON stdout: nguoi goi (slash
            # command /rc-check) publish file nay, ma stderr thi khong parse.
            if args.report:
                out["report"] = args.report
            _notify_run(args, out, started)
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
    p.add_argument("--tc", help="file testcase .xlsx, hoac link Google Sheet (tu tai ban moi nhat)")
    p.add_argument("--sdk", default="",
                   help="ban SDK FO cua app, vd 3.2.0 - mac dinh tu do tu logcat")
    p.add_argument("--tab", default="",
                   help="chi chay dung mot tab, vd `--tab 3.4.0` (khong keo theo base + delta)")
    p.add_argument("--case",
                   help="case can chay: `3.2.0#12` hoac `12` neu so do chi co o mot tab; "
                        "`all` = moi case tool chay duoc")
    p.add_argument("--set", action="append", metavar="KEY=VALUE",
                   help="dat thang key/value, khong can file TC (lap lai duoc)")
    p.add_argument("--keep", action="store_true",
                   help="GIU config da dat de tu mo app xem (mac dinh: tra ve nguyen trang)")
    p.add_argument("--restore", action="store_true",
                   help="tra config ve ban da luu o luot --keep truoc do")
    p.add_argument("--out-dir", default=str(DEFAULT_OUT),
                   help=f"noi luu snapshot config goc (mac dinh {DEFAULT_OUT})")
    p.add_argument("--no-walk", action="store_true",
                   help="khong lai qua luong First Open de toi man cua case")
    p.add_argument("--full-walk", action="store_true",
                   help="di het luong FO nhu TC ghi, ke ca khi key cua case nam o man som hon")
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
    p.add_argument("--khong-claude", action="store_true",
                   help="chay khong co agent: --tc mac dinh sheet TC chung, --report tu "
                        "dat ten, Discord dinh kem report va ghi so case can nguoi xem")
    p.add_argument("--preflight", action="store_true",
                   help="chi kiem dieu kien truoc khi chay (may, khoa man, ban debuggable, "
                        "sheet TC + sheet ID ads, RAM may tinh) roi thoat")
    p.add_argument("--tiep", metavar="FILE_LUOT",
                   help="chay not case chua co ket qua trong file luot (luot truoc bi tat giua chung)")
    p.add_argument("--gop", action="append", metavar="FILE_LUOT",
                   help="lay ket qua file luot lam nen (lap lai duoc); kem --case thi case chay "
                        "lai de len, khong kem --case thi chi dung lai report, khong can may")
    p.add_argument("--cham-tay", metavar="FILE_LUOT",
                   help="ghi ket qua cham tay vao file luot (kem --case, --dong, --ket, --ly-do) "
                        "roi dung lai report, khong can may")
    p.add_argument("--dong", default="", help="so dong Expected cham tay, dem tu 1, vd 2 hoac 1,3")
    p.add_argument("--ket", default="", help="PASS | FAIL | NEEDS_HUMAN | NOT_VERIFIABLE")
    p.add_argument("--ly-do", default="", help="so do / cach do, hien tren report")
    p.add_argument("--dieu-kien-dat", default="",
                   help="kem --cham-tay: luot do tay DA tao duoc precondition ma tool khong tao duoc "
                        "- ghi cach tao; bo precondition_thieu cua luot tool (khong go ad_click)")
    p.add_argument("--adb", help="duong dan adb neu khong nam trong PATH")
    return p


def mac_dinh_khong_claude(args: argparse.Namespace) -> None:
    """Dien san nhung gi agent tung tu lay (rc-check.md muc 4) khi chay khong Claude.

    Chi dien cho duong chay case: doc baseline (`rcr-check --package`) khong can TC.
    """
    if not (args.khong_claude and args.case):
        return
    if not args.tc:
        args.tc = TC_MAC_DINH
    if not args.report:
        args.report = str(Path(args.out_dir) / f"rc-{args.package}-{time.strftime('%y%m%d-%H%M%S')}.html")


def _stdio_utf8() -> None:
    """Ep stdout/stderr ve utf-8.

    Console Windows mac dinh cp1252: mot chu tieng Viet trong JSON la
    UnicodeEncodeError, va no no SAU khi da chay xong ca luot tren may that -
    mat trang ket qua vi cai dau ra, khong phai vi app.
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            reconfigure(encoding="utf-8", errors="replace")


def main(argv: list[str] | None = None) -> int:
    _stdio_utf8()
    args = build_parser().parse_args(argv)
    mac_dinh_khong_claude(args)
    try:
        result = asyncio.run(run(args))
    except (AdbError, RcError) as exc:
        _log(f"LOI: {exc}")
        loi = {"error": str(exc)}
        luot = getattr(args, "luot_path", "")
        if luot:
            # Luot chet giua chung (mat may...): cac case da xong van nam trong file nay.
            loi["luot"] = luot
            _log(f"Kết quả các case đã xong: {luot} — chạy tiếp bằng --tiep {luot}")
        print(json.dumps(loi, ensure_ascii=False))
        return 1
    print(json.dumps(result, ensure_ascii=False))
    pf = result.get("preflight")
    return 1 if pf and not pf["ok"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
