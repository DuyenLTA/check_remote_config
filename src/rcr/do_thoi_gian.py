"""`rcr-do-thoi-gian`: do moi case `rcr-check` ton thoi gian vao dau, de biet sua cho nao lam tool nhanh hon.

Ra doi tu lan do AIP918 12/11/2026 (vivo): 3 case 319s, `uiautomator dump` 28%, cho co dinh 18%, Firebase 13%,
bam/vuot chi 1% -> sua dump / cho / Firebase. Chay lai cho app khac khi lượt cham thay cham bat thuong.

  rcr-do-thoi-gian chay --ra out/do.json -- <tham so rcr-check y nhu thuong>   chay + in bang
  rcr-do-thoi-gian bang out/do.json [loai]                                      in lai bang / chi tiet mot loai
  rcr-do-thoi-gian so-dong a.luot.json b.luot.json ...                          so ket qua tung dong giua cac lượt

Cach do: boc (monkeypatch) moi lenh adb (text + nhi phan), subprocess, asyncio.sleep / time.sleep, urllib (HTTP
Firebase / Google) va vai ham Python nang; moi ban ghi kem moc thoi gian + noi goi (file:dong trong rcr).
Chi doc - khong doi hanh vi rcr-check.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
import sys
import time
import traceback
import urllib.request

from . import do_thoi_gian_bang

GHI: list[tuple] = []
T0 = time.monotonic()


def _noi_goi() -> str:
    bo = ("adb_client.py", "do_thoi_gian.py", "ui_dump.py", "screencap.py", "asyncio", "functools")
    ra = []
    for f in reversed(traceback.extract_stack()[:-2]):
        if "/rcr/" in f.filename and not any(b in f.filename for b in bo):
            ra.append(f"{f.filename.rsplit('/', 1)[-1]}:{f.lineno}")
            if len(ra) == 3:
                break
    return " < ".join(ra)


def _ghi(loai: str, mo_ta: str, bat_dau: float) -> None:
    GHI.append((loai, mo_ta, time.monotonic() - bat_dau, bat_dau - T0, _noi_goi()))


def _bo_serial(args) -> list[str]:
    a = [x for x in args if x != "-s"]
    return a[1:] if a and a[0].isalnum() and len(a[0]) > 8 else a


def cai_dat() -> None:
    """Boc cac diem ton thoi gian. Goi MOT lan truoc khi chay rcr-check trong cung tien trinh."""
    from . import adb_client

    run_goc, bin_goc = adb_client.AdbClient._run, adb_client.AdbClient.run_binary

    async def run(self, *args, timeout=None):
        t = time.monotonic()
        try:
            return await run_goc(self, *args, timeout=timeout)
        finally:
            _ghi("adb", " ".join(_bo_serial(args))[:80], t)

    async def run_binary(self, *args, timeout=None):
        t = time.monotonic()
        try:
            return await bin_goc(self, *args, timeout=timeout)
        finally:
            _ghi("adb_bin", " ".join(_bo_serial(args))[:80], t)

    adb_client.AdbClient._run, adb_client.AdbClient.run_binary = run, run_binary

    sp_goc = subprocess.run

    def sp_run(*a, **k):
        t = time.monotonic()
        try:
            return sp_goc(*a, **k)
        finally:
            cmd = a[0] if a else k.get("args")
            _ghi("subproc", " ".join(map(str, cmd))[:80] if isinstance(cmd, (list, tuple)) else str(cmd)[:80], t)

    subprocess.run = sp_run

    ngu_goc = asyncio.sleep

    async def sleep(d, *a, **k):
        t = time.monotonic()
        r = await ngu_goc(d, *a, **k)
        if d >= 0.2:
            _ghi("sleep", f"{d:g}s", t)
        return r

    asyncio.sleep = sleep
    tngu_goc = time.sleep

    def tsleep(d):
        t = time.monotonic()
        tngu_goc(d)
        if d >= 0.2:
            _ghi("sleep", f"{d:g}s (time.sleep)", t)

    time.sleep = tsleep
    mo_goc = urllib.request.urlopen

    def urlopen(req, *a, **k):
        t, loi = time.monotonic(), ""
        try:
            return mo_goc(req, *a, **k)
        except Exception as e:
            loi = f" LOI {getattr(e, 'code', type(e).__name__)}"
            raise
        finally:
            url = getattr(req, "full_url", str(req))
            _ghi("http", f"{getattr(req, 'get_method', lambda: 'GET')()} {url[:70]}{loi}", t)

    urllib.request.urlopen = urlopen


def _chay(ra: str, tham_so: list[str]) -> int:
    from . import cli_check

    cai_dat()
    rc = 1
    try:
        rc = cli_check.main(tham_so)
    finally:
        d = {"tong": time.monotonic() - T0, "tham_so": tham_so, "ghi": GHI}
        with open(ra, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False)
        print(do_thoi_gian_bang.bang(d), file=sys.stderr)
        print(f"Ghi so do vao {ra}", file=sys.stderr)
    return rc


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "chay":
        sau = argv.index("--") if "--" in argv else len(argv)
        p = argparse.ArgumentParser(prog="rcr-do-thoi-gian chay")
        p.add_argument("--ra", default="out/do-thoi-gian.json")
        a = p.parse_args(argv[1:sau])
        return _chay(a.ra, argv[sau + 1:])
    p = argparse.ArgumentParser(prog="rcr-do-thoi-gian", description="Do thoi gian tung phan cua rcr-check")
    sub = p.add_subparsers(dest="lenh", required=True)
    b = sub.add_parser("bang", help="in bang thoi gian tu file .json")
    b.add_argument("file")
    b.add_argument("loai", nargs="?", help="chi tiet mot loai theo noi goi, vd 'uiautomator dump'")
    s = sub.add_parser("so-dong", help="so ket qua tung dong Expected giua cac file .luot.json")
    s.add_argument("files", nargs="+")
    sub.add_parser("chay", help="chay --ra FILE -- <tham so rcr-check>")
    a = p.parse_args(argv)
    if a.lenh == "bang":
        with open(a.file, encoding="utf-8") as f:
            print(do_thoi_gian_bang.bang(json.load(f), a.loai))
        return 0
    if a.lenh == "so-dong":
        ds = []
        for duong in a.files:
            with open(duong, encoding="utf-8") as f:
                ds.append(json.load(f))
        text, _lech = do_thoi_gian_bang.so_dong(ds)
        print(text)
        return 0
    return 2
