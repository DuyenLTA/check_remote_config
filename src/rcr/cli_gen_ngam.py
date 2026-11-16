"""`rcr-gen-ngam`: tu lai + tu cham tab TC "gen ngam" (tao anh / video chay ngam) theo NHOM config.

  rcr-gen-ngam chay --package P --serial S [--luot out/run-...luot.json] [--nhom r01,chung,r06,r07]
                # khong --luot: tu dung khung tu sheet TC (vai giay, khong mo app) - gen_ngam_khung
  rcr-gen-ngam cham --package P --luot out/run-...luot.json      # cham lai tu so do da luu (khong can may)

Moi nhom: dat config Test Data cua nhom (rcr-check --keep --fresh) -> clear data, mo lan dau, mua sub test neu
chua Premium -> lai kich ban, ghi so do (`out/gen-ngam-<P>-so.json`) -> tra config. Cuoi cung cham tung dong Expected.
Chu tren man theo app: src/rcr/data/gen_ngam_cong_thuc.yaml. Cach do tung case: docs/rc-check/gen-ngam-tu-lai.md.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
import sys
import time
from pathlib import Path

from . import bot_hang_doi
from . import luot_file
from .gen_ngam_cham import So, ghi_luot
from .models import RcError

OUT_MAC_DINH = Path(__file__).resolve().parents[2] / "out"
ANDROID_TOI_THIEU = 33          # Android 13: POST_NOTIFICATIONS la quyen runtime
# nhom -> (case dai dien lay config Test Data, key ep them)
NHOM = {
    "r01": ("GEN-R01-01", {"generating_wait_image_seconds": "45"}),
    "chung": ("GEN-R02-01", {}),         # gom ca S01 (cung Test Data, chay dau nhom)
    "r06": ("GEN-R06-01", {}),
    "r07": ("GEN-R07-01", {}),
    "s01": ("GEN-S01-01", {}),
    "dem_r01": ("GEN-R02-01", {}),       # chi dem luot anh R01-06 (Test Data R01 = Test Data chung)
}
MAC_DINH = "r01,chung,r06,r07"
# Case thuoc nhom: chay lai nhom thi bo so do cu cua cac case nay (`ghi_luot` lay so do khop DAU TIEN).
CASE_NHOM = {"r01": r"^GEN-R01-0[1-5]$", "chung": r"^GEN-(?:S01|R0[2-5]|R08)-|^GEN-R01-06$", "r06": r"^GEN-R06-",
             "r07": r"^GEN-R07-", "s01": r"^GEN-S01-", "dem_r01": r"^GEN-R01-06$"}


def _rcr_check() -> str:
    return str(Path(sys.executable).with_name("rcr-check"))


def config_nhom(records: list[dict], nhom: str) -> dict[str, str]:
    key, them = NHOM[nhom]
    r = next((x for x in records if x.get("key") == key), None)
    if r is None:
        raise RcError(f"file lượt không có case {key} (nhóm {nhom})")
    return {**(r.get("overrides") or {}), **them}


def dat(package: str, serial: str, gt: dict[str, str], log) -> None:
    lenh = [_rcr_check(), "--package", package, "--serial", serial, "--keep", "--fresh", "--no-walk"]
    for k, v in gt.items():
        lenh += ["--set", f"{k}={v}"]
    log(f"  đặt config ({len(gt)} key): " + ", ".join(f"{k}={v}" for k, v in gt.items() if k not in
                                                     ("enable_all_ads", "enable_all_ads_tutorial")))
    subprocess.run(lenh, check=True, stdout=subprocess.DEVNULL, stderr=sys.stderr)


def tra(package: str, serial: str) -> None:
    subprocess.run([_rcr_check(), "--package", package, "--serial", serial, "--restore"], check=False,
                   stdout=subprocess.DEVNULL, stderr=sys.stderr)


def _file_so(out_dir: Path, package: str) -> Path:
    return Path(out_dir) / f"gen-ngam-{package}-so.json"


def luu_so(f: Path, so: So) -> None:
    luot_file.ghi_nguyen_tu(f, json.dumps({"dong": so.dong, "dieu_kien": so.dieu_kien, "nho": so.nho}, ensure_ascii=False, indent=1))


def doc_so(f: Path) -> So:
    so = So()
    if f.is_file():
        d = json.loads(f.read_text(encoding="utf-8"))
        so.dong = {k: [tuple(x) for x in v] for k, v in d.get("dong", {}).items()}
        so.dieu_kien = d.get("dieu_kien", {})
        so.nho = d.get("nho", {})
    return so


def chay(a) -> dict:
    from . import gen_ngam_may, gen_ngam_nhom_dau as dau, gen_ngam_nhom_sau as sau
    from .adb_client import AdbClient
    bat_dau = time.monotonic()

    def _log(m: str) -> None:
        t = int(time.monotonic() - bat_dau)
        print(f"[+{t // 60:02d}:{t % 60:02d}] {m}", file=sys.stderr, flush=True)

    ct = gen_ngam_may.cong_thuc(a.package)
    if not ct:
        raise RcError(f"{a.package}: chưa khai chữ trên màn trong src/rcr/data/gen_ngam_cong_thuc.yaml")
    if ct.get("_khuon_chung"):
        _log("App chưa có mục riêng trong gen_ngam_cong_thuc.yaml -> dùng khuôn chung; chữ nào không khớp (lái hụt) "
             "thì thêm chữ của app vào regex khuôn chung (A|B)")
    from . import gen_ngam_khung
    if not a.luot:
        a.luot = str(gen_ngam_khung.dung(a.package, a.serial, a.out_dir, a.app_label))
        _log(f"Khung lượt dựng từ sheet TC (không mở app): {a.luot}")
    else:
        gen_ngam_khung.lam_moi(a.luot, a.package, a.out_dir, _log)     # luon tai lai sheet truoc khi chay
    records = luot_file.doc(a.luot, a.package)["records"]
    f_so = _file_so(a.out_dir, a.package)
    so = doc_so(f_so) if a.tiep else So()
    so.log = _log
    so.luu = lambda: luu_so(f_so, so)
    client = AdbClient(None)
    sdk, _, _ = asyncio.run(client.shell(a.serial, "getprop", "ro.build.version.sdk"))
    if int((sdk or "0").strip() or 0) < ANDROID_TOI_THIEU:
        # Bo TC xin quyen thong bao (R01-01, S01) chi co tren Android 13+: may Android 12 khong co hop thoai -> nhom
        # chung dung o S01, ~22 case khong do (Pixel 4 16/11/2026). Dung ngay, bao chon may khac.
        raise RcError(f"máy {a.serial} là API {sdk.strip()} (< {ANDROID_TOI_THIEU}, Android 13): bộ gen ngầm cần hộp "
                      "thoại xin quyền thông báo POST_NOTIFICATIONS — chạy trên máy Android 13+ (vd Pixel 6)")
    gen_ngam_may.MAU_TOAST[:] = [ct["toast_xong"]]
    asyncio.run(client.shell(a.serial, "logcat", "-G", "16M"))
    ctx = dau.Ctx(client, a.serial, a.package, ct, so, Path(a.out_dir) / "gen-ngam-video", _log)
    chay_nhom = {"r01": dau.nhom_r01, "chung": dau.nhom_chung, "r06": sau.nhom_r06, "r07": sau.nhom_r07,
                 "s01": sau.nhom_s01, "dem_r01": dau.nhom_dem_r01}     # s01 / dem_r01: chi khi chay lai rieng
    hut = {}
    ctx.nho["giu_video"] = a.giu_video
    try:
        _chay_cac_nhom(a, records, so, f_so, ctx, chay_nhom, hut, dau.LaiHut, _log)
    finally:
        tra(a.package, a.serial)       # luot hong giua chung van tra config testvsl (dung chung giua cac may)
    kq = ghi_luot(a.luot, a.package, so, ct.get("bo_dong") or [], _log)
    return {"lai_hut": hut, "so_do": str(f_so), "thoi_gian_s": round(time.monotonic() - bat_dau), **kq}


def _chay_cac_nhom(a, records, so, f_so, ctx, chay_nhom, hut, LaiHut, _log) -> None:
    import re
    from .adb_parsers import AdbError
    for nhom in [x.strip() for x in a.nhom.split(",") if x.strip()]:
        _log(f"Nhóm {nhom}")
        so.dong = {k: [x for x in v if a.giu_video and k == "GEN-R06-03" and x[0] == "còn 4/5"]
                   if re.search(CASE_NHOM[nhom], k) else v for k, v in so.dong.items()}
        ctx.nho["config"] = config_nhom(records, nhom)
        dat(a.package, a.serial, ctx.nho["config"], _log)
        try:
            asyncio.run(chay_nhom[nhom](ctx))
        except LaiHut as exc:
            hut[nhom] = str(exc)
            _log(f"  LÁI HỤT nhóm {nhom}: {exc}")
        except (AdbError, OSError, ValueError, KeyError, IndexError, TypeError, AttributeError) as exc:
            hut[nhom] = f"lỗi tool {type(exc).__name__}: {exc}"
            _log(f"  LỖI TOOL nhóm {nhom}: {type(exc).__name__}: {exc}")
        finally:
            luu_so(f_so, so)
        _log(f"  xong nhóm {nhom}: {sum(len(v) for v in so.dong.values())} số đo")


def cham(a) -> dict:
    from . import gen_ngam_khung, gen_ngam_may
    ct = gen_ngam_may.cong_thuc(a.package) or {}
    gen_ngam_khung.lam_moi(a.luot, a.package, a.out_dir, lambda m: print(m, file=sys.stderr))
    return ghi_luot(a.luot, a.package, doc_so(_file_so(a.out_dir, a.package)), ct.get("bo_dong") or [],
                    lambda m: print(m, file=sys.stderr))


# Thu muc file khoa may: chung voi rcr-check (cli_check.DEFAULT_OUT) va bot.
KHOA_DIR = Path(__file__).resolve().parents[2] / "out"


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="rcr-gen-ngam", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("lenh", choices=("chay", "cham"))
    p.add_argument("--package", required=True)
    p.add_argument("--serial", default="")
    p.add_argument("--luot", default="", help="file lượt; bỏ trống thì tự dựng khung từ sheet TC (chay)")
    p.add_argument("--app-label", default="")
    p.add_argument("--nhom", default=MAC_DINH, help="các nhóm chạy lần lượt (s01 đã gộp vào chung)")
    p.add_argument("--tiep", action="store_true", help="giữ số đo đã lưu của lượt trước (chạy lại vài nhóm)")
    p.add_argument("--giu-video", action="store_true",
                   help="r06: dùng lại số video/ngày đã đếm ở lượt trước (đếm hết lượt video ~8 phút)")
    p.add_argument("--out-dir", type=Path, default=OUT_MAC_DINH)
    a = p.parse_args(argv)
    try:
        if a.lenh == "chay" and not a.serial:
            raise RcError("chay cần --serial (lái máy thật)")
        if a.lenh == "cham" and not a.luot:
            raise RcError("cham cần --luot")
        with bot_hang_doi.giu_may_ca_job(KHOA_DIR, a.serial if a.lenh == "chay" else ""):
            ra = chay(a) if a.lenh == "chay" else cham(a)
    except BlockingIOError:
        print(f"LOI: máy {a.serial} đang có lượt khác (bot hoặc rc-check khác) - chờ lượt đó xong rồi chạy lại",
              file=sys.stderr)
        return 1
    except (RcError, subprocess.CalledProcessError) as exc:
        print(f"LOI: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(ra, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
