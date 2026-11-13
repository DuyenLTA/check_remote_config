"""`rcr-iaa`: chay bo IAA theo nhom bien the (4 lan lai app thay vi moi case mot lan) + tu cham dong doc duoc tu log.

  rcr-iaa dat   --package P --serial S --bien-the bat|thuong|high|tat   # dat config bien the cho MOI vi tri (giu lai)
  rcr-iaa tra   --package P --serial S                                  # tra config (rcr-check --restore)
  rcr-iaa cham  --package P --luot out/run-x.luot.json --log bat=out/iaa-bat.log [--log tat=...] [--ghi-de]
  rcr-iaa chay  --package P --serial S --luot out/run-x.luot.json [--bien-the-ds bat,thuong,high,tat]
                # tu lai theo data/iaa_duong_lai.yaml cho tung bien the (dat -> lai + ghi log -> tra) roi cham

Cach lai app moi bien the + bay da gap: docs/rc-check/iaa-chay-theo-nhom.md.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from . import cham_tay, iaa_cham_log, iaa_nhom, luot_file, run_batch, tc_iaa_tu_sheet_kt, tc_source, tc_tinh_nang_rieng
from .models import RcError
from .verdict_levels import FAIL, PASS

OUT_MAC_DINH = Path(__file__).resolve().parents[2] / "out"


def _rcr_check() -> str:
    return str(Path(sys.executable).with_name("rcr-check"))


def doc_vi_tri(package: str, out_dir: Path):
    """Tai lai sheet Check thong so KT (ban moi nhat moi lenh) -> vi tri muc 3 cua app."""
    goc = tc_source.tai_ve(tc_tinh_nang_rieng.link_goc("iaa"), out_dir)
    return tc_iaa_tu_sheet_kt.vi_tri_tu_workbook(goc, package)


def dat(args, ds=None) -> dict:
    ds = ds if ds is not None else doc_vi_tri(args.package, args.out_dir)
    gt = iaa_nhom.gia_tri(ds, args.bien_the)
    lenh = [_rcr_check(), "--package", args.package, "--keep", "--no-actions"]
    if args.serial:
        lenh += ["--serial", args.serial]
    if not args.khong_fresh:
        lenh.append("--fresh")              # pm clear: app fetch that config moi (old user giu cache, AIP886 02/11)
    for k, v in gt.items():
        lenh += ["--set", f"{k}={v}"]
    print(f"Đặt biến thể '{args.bien_the}' cho {len(ds)} vị trí ({len(gt)} key)...", file=sys.stderr)
    subprocess.run(lenh, check=True, stdout=sys.stderr)
    adb = ["adb"] + (["-s", args.serial] if args.serial else [])
    for tag in ("FA", "FA-SVC"):
        subprocess.run(adb + ["shell", "setprop", f"log.tag.{tag}", "VERBOSE"], check=False)
    subprocess.run(adb + ["logcat", "-c"], check=False)
    log = Path(args.out_dir) / f"iaa-{args.package}-{args.bien_the}.log"
    return {"bien_the": args.bien_the, "keys": gt, "log_goi_y": str(log),
            "ghi_log": f"{' '.join(adb)} logcat -v epoch -s FA-SVC:V > {log}",
            "vi_tri": [{"so": i, "man": v.man or v.goc, "loai": v.loai,
                        "high": v.high.id if v.high else "", "thuong": v.thuong.id if v.thuong else ""}
                       for i, v in enumerate(ds, 1)]}


def tra(args) -> dict:
    lenh = [_rcr_check(), "--package", args.package, "--restore"] + (["--serial", args.serial] if args.serial else [])
    subprocess.run(lenh, check=True, stdout=sys.stderr)
    return {"restored": True}


def _logs(cap: list[str]) -> dict[str, str]:
    ra = {}
    for c in cap or []:
        ten, sep, duong = c.partition("=")
        iaa_nhom.so_case(ten)
        if not sep or not Path(duong).is_file():
            raise RcError(f"--log phải dạng <biến thể>=<file log có>, nhận được {c!r}")
        ra[ten] = Path(duong).read_text(encoding="utf-8", errors="replace")
    return ra


def ket_qua(ds, logs: dict[str, str]) -> list[tuple[str, int, str, str]]:
    """[(ma case, so dong, PASS|FAIL, ly do)] tu cac log bien the."""
    units = iaa_nhom.ban_do_unit(ds)
    ev = {b: iaa_cham_log.su_kien(t, units) for b, t in logs.items()}
    da_toi = {i for e in ev.get("bat", []) for i in [e["vi_tri"]] if e["ten"] == "track_ad_request"}
    ra = []
    for i, v in enumerate(ds, 1):
        hid, tid = (v.high.id if v.high else ""), (v.thuong.id if v.thuong else "")
        if "bat" in ev and (kq := iaa_cham_log.cham_thu_tu(ev["bat"], i, hid, tid)):
            ra.append((iaa_nhom.ma_case(i, "bat"), 0, *kq))      # 0 = dong cuoi (dong ID) cua case
        if hid and tid:
            for b, bat, tat, ub, ut in (("thuong", "thuong", "high", tid, hid), ("high", "high", "thuong", hid, tid)):
                if b in ev:
                    ra += [(iaa_nhom.ma_case(i, b), *x)
                           for x in iaa_cham_log.cham_mot_tang(ev[b], i, bat, tat, ub, ut, i in da_toi)]
        if "tat" in ev:
            ra += [(iaa_nhom.ma_case(i, "tat"), *x) for x in iaa_cham_log.cham_tat(ev["tat"], i, [hid, tid], i in da_toi)]
    return ra


def cham(args, ds=None) -> dict:
    ds = ds if ds is not None else doc_vi_tri(args.package, args.out_dir)
    kq = ket_qua(ds, _logs(args.log))
    data = luot_file.doc(args.luot, args.package)
    records = data["records"]
    theo_key = {r.get("key"): k for k, r in enumerate(records)}
    ghi, bo = [], []
    for ma, dong, ket, ly in kq:
        k = theo_key.get(ma)
        if k is None:
            bo.append(f"{ma}: không có trong file lượt")
            continue
        lines = records[k].get("lines") or []
        dong = dong or len(lines)
        if dong > len(lines) or (lines[dong - 1].get("v") in (PASS, FAIL) and not args.ghi_de):
            bo.append(f"{ma} dòng {dong}: đã chấm, giữ nguyên")
            continue
        records[k] = cham_tay.cham(records[k], [dong], ket, f"rcr-iaa từ log lượt lái theo nhóm: {ly}", ai="Tool")
        ghi.append(f"{ma} dòng {dong}: {ket} — {ly}")
    meta = {k: v for k, v in data.items() if k not in ("records", "phien_ban", "xong")}
    if data.get("report"):
        run_batch.ghi_report(luot_file.baseline_tu(data), data.get("tc") or {}, records, data.get("app_label", ""),
                             data["report"], lambda m: print(m, file=sys.stderr))
    luot_file.ghi(Path(args.luot), meta, records, bool(data.get("xong")))
    con = [f"{r['key']} dòng {n}" for r in records for n, l in enumerate(r.get("lines") or [], 1)
           if l.get("v") not in (PASS, FAIL)]
    return {"da_ghi": ghi, "bo_qua": bo, "con_cham_tay": con, "report": data.get("report", "")}


def chay(args) -> dict:
    """4 bien the noi tiep tren MOT may: dat config -> lai FO toi Home + tu lai duong IAA (ghi log FA-SVC) -> tra -> cham."""
    import asyncio
    import time
    from . import iaa_khuon, iaa_lai
    from .adb_client import AdbClient
    client = AdbClient(None)
    bat_dau = time.monotonic()

    def _log(m: str) -> None:
        t = int(time.monotonic() - bat_dau)
        print(f"[+{t // 60:02d}:{t % 60:02d}] {m}", file=sys.stderr, flush=True)

    ds = doc_vi_tri(args.package, args.out_dir)      # tai sheet KT MOT lan cho ca luot (4 bien the + cham)
    logs, lai, nguon = [], {}, ""
    for b in [x.strip() for x in args.bien_the_ds.split(",") if x.strip()]:
        iaa_nhom.so_case(b)
        args.bien_the = b
        dat(args, ds)
        try:
            # pm clear (--fresh) dua app ve FO: lai FO toi Home roi moi nhan khuon / lai cac doan (doan nao cung tu Home).
            nhat_ky: list[str] = []
            nguon, doan = asyncio.run(iaa_khuon.chon(client, args.serial, args.package, nhat_ky))
            if not doan:
                raise RcError(f"{args.package}: Home không khớp khuôn nào trong src/rcr/data/iaa_duong_lai.yaml — thêm "
                              "chữ của app vào regex khuôn gần nhất (hoặc khai khuôn mới) theo "
                              "docs/rc-check/iaa-chay-theo-nhom.md.")
            file_log = Path(args.out_dir) / f"iaa-{args.package}-{b}.log"
            _log(f"Lái đường IAA biến thể '{b}' ({nguon})...")
            lai[b] = asyncio.run(iaa_lai.lai(client, args.serial, args.package, doan, file_log, _log))
        finally:
            tra(args)
        logs.append(f"{b}={file_log}")
        _log(f"xong biến thể '{b}'")
    args.log = logs
    kq = cham(args, ds) if args.luot else {}
    return {"duong_lai": nguon, "lai": lai, "logs": logs, "thoi_gian_s": round(time.monotonic() - bat_dau), **kq}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="rcr-iaa", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("lenh", choices=("dat", "tra", "cham", "chay"))
    p.add_argument("--package", required=True)
    p.add_argument("--serial", default="")
    p.add_argument("--bien-the", default="bat", choices=tuple(iaa_nhom.BIEN_THE))
    p.add_argument("--khong-fresh", action="store_true", help="dat config khong pm clear (mac dinh pm clear)")
    p.add_argument("--luot", default="", help="file lượt .luot.json của lượt rcr-check --tc iaa")
    p.add_argument("--log", action="append", metavar="BIEN_THE=FILE", help="log logcat -v epoch của một lượt lái")
    p.add_argument("--ghi-de", action="store_true", help="ghi đè cả dòng đã PASS/FAIL")
    p.add_argument("--bien-the-ds", default="bat,thuong,high,tat", help="chay: các biến thể lái lần lượt")
    p.add_argument("--out-dir", type=Path, default=OUT_MAC_DINH)
    a = p.parse_args(argv)
    try:
        if a.lenh == "cham" and not (a.luot and a.log):
            raise RcError("cham cần --luot và ít nhất một --log <biến thể>=<file>")
        if a.lenh == "chay" and not a.serial:
            raise RcError("chay cần --serial (lái máy thật)")
        ra = {"dat": dat, "tra": tra, "cham": cham, "chay": chay}[a.lenh](a)
    except (RcError, subprocess.CalledProcessError) as exc:
        print(f"LOI: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(ra, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
