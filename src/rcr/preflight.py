"""Kiem dieu kien TRUOC khi chay mot luot (`rcr-check --preflight`).

Moi dieu kien duoi day truoc day chi lo ra GIUA luot: cai nham ban release thi
toi buoc doc baseline moi biet (23/10/2026 cai nham 3 lan), RAM may tinh can
thi Claude Code tat lenh nen o case thu 14 (mat het ket qua), sheet ID khong
co tab cua app thi luot van chay nhung dong ads quy nham vi tri. Gom het lai
mot lenh vai giay, chay truoc khi cam may di lam viec khac.

Ket qua moi muc: `ok` | `loi` (chay la hong, phai xu truoc) | `canh_bao`
(chay duoc nhung de hong giua chung).
"""

from __future__ import annotations

import asyncio
import ctypes
import sys
from pathlib import Path

from . import ad_units_sheet, app_sandbox, device_app, fa_log, sdk_probe, tc_source
from .adb_parsers import AdbError
from .models import RcError

OK, LOI, CANH_BAO = "ok", "loi", "canh_bao"
# Duoi muc nay Claude Code tat lenh nen khi RAM can (do 23/10/2026: con 1,7 GB
# thi luot 19 case bi tat; dong Chrome con 5,5 GB thi chay het).
RAM_TOI_THIEU_GB = 4.0
# Publisher cua cac ad unit test Google cong bo (banner …6300978111, native …2247696110).
GOOGLE_TEST_PUB = "ca-app-pub-3940256099942544/"
# Cho toi da bao lau sau khi mo app de thay request ads dau tien (splash ~2s, do 24/10/2026).
ADS_CHO_S = 15.0


def _muc(ten: str, trang_thai: str, chi_tiet: str, viec: str = "") -> dict:
    return {"ten": ten, "trang_thai": trang_thai, "chi_tiet": chi_tiet, "viec_can_lam": viec}


def ram_trong_gb() -> float | None:
    """RAM con trong cua MAY TINH (khong phai dien thoai). Khong do duoc -> None."""
    try:
        if sys.platform == "win32":
            class _Mem(ctypes.Structure):
                _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                            ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                            ("ullTotalPageFile", ctypes.c_ulonglong),
                            ("ullAvailPageFile", ctypes.c_ulonglong),
                            ("ullTotalVirtual", ctypes.c_ulonglong),
                            ("ullAvailVirtual", ctypes.c_ulonglong),
                            ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
            m = _Mem()
            m.dwLength = ctypes.sizeof(_Mem)
            if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m)):
                return None
            return m.ullAvailPhys / 1024 ** 3
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) / 1024 ** 2
    except (OSError, ValueError, AttributeError):
        pass
    return None


def man_hinh(window: str, power: str) -> tuple[str, str]:
    """(trang_thai, chi_tiet) tu `dumpsys window` + `dumpsys power`.

    May khoa thi PMS khong resolve activity -> tool bao "khong mo duoc app",
    nhin y het app hong (rc-check.md muc 3).
    """
    if "mWakefulness=Awake" not in power:
        return LOI, "màn hình đang tắt"
    if "isKeyguardShowing=true" in window or "mDreamingLockscreen=true" in window:
        return LOI, "máy đang khoá màn hình"
    return OK, "màn hình đang mở, không khoá"


async def _app(client, serial: str, package: str) -> list[dict]:
    out, _, _ = await client.shell(serial, "pm", "path", package)
    if "package:" not in out:
        return [_muc("App đã cài", LOI, f"máy chưa cài {package}", "Cài bản build debuggable của app")]
    info, _, _ = await client.shell(serial, "dumpsys", "package", package)
    ver = next((ln.split("versionName=")[1].strip() for ln in info.splitlines()
                if "versionName=" in ln), "?")
    ra = [_muc("App đã cài", OK, f"{package} {ver}")]
    try:
        mode = await app_sandbox.detect_mode(client, serial, package)
        cach = {app_sandbox.RUN_AS: "bản debuggable (run-as)", app_sandbox.ROOT: "adb root",
                app_sandbox.SU: "máy root (su)"}[mode]
        ra.append(_muc("Vào được dữ liệu app", OK, cach))
    except AdbError as exc:
        dong = str(exc).splitlines() or ["?"]
        # Dong 2 la ly do run-as; loi mot dong (package sai, mat may) thi lay dong dau.
        ra.append(_muc("Vào được dữ liệu app", LOI, (dong[1:] or dong)[0].strip(),
                       "Xin dev bản build bật debuggable (kiểm bằng aapt trước khi cài), "
                       "hoặc dùng máy root"))
    return ra


def _sheets(package: str, tc: str, out_dir) -> list[dict]:
    ra = []
    try:
        path = tc_source.tai_ve(tc, out_dir)
        if not Path(path).exists():
            raise RcError(f"không thấy file {path}")
        ra.append(_muc("Sheet testcase", OK, "tải được bản mới nhất" if tc_source.la_link(tc) else path))
    except RcError as exc:
        ra.append(_muc("Sheet testcase", LOI, str(exc), "Chia sẻ sheet TC hoặc gửi file .xlsx"))
    bang, ghi_chu = ad_units_sheet.tai(package, out_dir)
    if bang:
        ra.append(_muc("Sheet ID ads", OK, ghi_chu))
    else:
        ra.append(_muc("Sheet ID ads", LOI, ghi_chu,
                       "Bổ sung tab của app vào sheet Check thông số KT (dòng Package name)"))
    return ra


def unit_ads(events: list[dict]) -> list[str]:
    """Ad unit ID trong cac event request/load/show cua app (key `adunitid` hoac `ad_unit_id`)."""
    ra = []
    for e in events:
        if e["name"].startswith(("track_ad_request", "ad_load", "ad_show")):
            unit = e["params"].get("adunitid") or e["params"].get("ad_unit_id") or ""
            if unit.startswith("ca-app-pub-"):
                ra.append(unit)
    return ra


def muc_ads_test(units: list[str]) -> dict:
    """Build dung unit test cua Google -> moi vi tri chung mot ID, khong quy duoc
    ad ve vi tri nao: dong ads ra NEEDS_HUMAN hang loat hoac PASS gia (do 24/10/2026,
    Piclux 2.4.0: native/banner la ID test, chay 50 phut moi biet)."""
    if not units:
        return _muc("Ads dùng ID thật", CANH_BAO,
                    f"mở app {ADS_CHO_S:.0f}s chưa thấy request ads nào trong log",
                    "Kiểm mạng / enable_all_ads; ads chưa chạy thì dòng ads sẽ không chấm được")
    test = sorted({u for u in units if u.startswith(GOOGLE_TEST_PUB)})
    if test:
        return _muc("Ads dùng ID thật", LOI,
                    f"{len(test)} unit là ID test của Google ({', '.join(u.rsplit('/', 1)[-1] for u in test)})"
                    f" trên {len(set(units))} unit đã request",
                    "Xin dev bản debuggable dùng ID ads thật; build ID test không quy được ad về vị trí")
    return _muc("Ads dùng ID thật", OK, f"{len(set(units))} unit đã request đều là ID thật")


async def _mo_app_mot_lan(client, serial: str, package: str) -> tuple[dict, str]:
    """Mo app mot lan: doc log FA-SVC xem ads request bang ID nao, va dong
    `VslTemplate4FirstOpenSDK: Using version` cua CHINH pid app (truoc khi
    force-stop: mat pid la khong loc duoc log theo app). -> (muc ads, ban SDK)."""
    await fa_log.bat(client, serial)
    await client.shell(serial, "logcat", "-c")
    try:
        await device_app.restart(client, serial, package)
        units: list[str] = []
        sdk = ""
        for _ in range(int(ADS_CHO_S / 1.5)):
            await asyncio.sleep(1.5)
            units = unit_ads(await fa_log.doc(client, serial))
            if not sdk:
                pid = await sdk_probe.pid_of(client, serial, package)
                sdk = sdk_probe.last_version(await sdk_probe.read_log(client, serial, pid)) if pid else ""
            if sdk and units and any(u.startswith(GOOGLE_TEST_PUB) for u in units):
                break
        return muc_ads_test(units), sdk
    finally:
        await device_app.force_stop(client, serial, package)


def muc_sdk(sdk: str) -> dict:
    """Ban SDK FO quyet dinh nhanh chay: Next-Gen -> checklist, con lai -> bo TC."""
    if not sdk:
        return _muc("Bản SDK FO", CANH_BAO, "không thấy dòng `VslTemplate4FirstOpenSDK: Using version` trong log",
                    "Hỏi bản SDK rồi truyền --sdk X.Y.Z")
    if sdk_probe.la_nextgen(sdk):
        return _muc("Bản SDK FO", OK, f"{sdk} → Next-Gen: chấm checklist sdk-check/ (không chạy bộ TC)")
    return _muc("Bản SDK FO", OK, f"{sdk} → chạy bộ TC")


def noi_long_nextgen(muc: list[dict]) -> list[dict]:
    """Nhanh checklist Next-Gen khong patch RC va khong quy ad ve vi tri theo sheet:
    ban release / ID test chi han che vai case (ghi o report), khong chan ca luot."""
    nhe = {"Vào được dữ liệu app", "Ads dùng ID thật"}
    return [{**m, "trang_thai": CANH_BAO, "viec_can_lam": "Checklist vẫn chạy; case cần đổi RC / ad thật ghi rõ trên report"}
            if m["ten"] in nhe and m["trang_thai"] == LOI else m for m in muc]


def _ram() -> dict:
    gb = ram_trong_gb()
    if gb is None:
        return _muc("RAM máy tính", CANH_BAO, "không đo được")
    if gb < RAM_TOI_THIEU_GB:
        return _muc("RAM máy tính", CANH_BAO, f"còn trống {gb:.1f} GB (< {RAM_TOI_THIEU_GB:.0f} GB)",
                    "Đóng bớt Chrome / Android Studio, kẻo lượt dài bị tắt giữa chừng")
    return _muc("RAM máy tính", OK, f"còn trống {gb:.1f} GB")


async def chay(client, serial: str, package: str, tc: str, out_dir, sdk: str = "") -> dict:
    """Kiem het, KHONG dung o muc dau tien hong: nguoi dung can thay moi viec phai lam.

    `sdk` (tham so --sdk) de trong thi doc tu log lan mo app. Ban Next-Gen ->
    `nhanh = "nextgen"`: bo qua sheet TC / sheet ID ads, khong bat buoc debuggable.
    """
    window, _, _ = await client.shell(serial, "dumpsys", "window")
    power, _, _ = await client.shell(serial, "dumpsys", "power")
    tt, ct = man_hinh(window, power)
    muc = [_muc("Máy", OK, serial),
           _muc("Màn hình", tt, ct, "Mở khoá máy, tắt khoá màn hình tự động" if tt == LOI else "")]
    app = await _app(client, serial, package)
    muc += app
    if tt == OK and app[0]["trang_thai"] == OK:
        try:
            ads, sdk_log = await _mo_app_mot_lan(client, serial, package)
            muc.append(ads)
            sdk = sdk or sdk_log
        except (AdbError, RcError) as exc:
            muc.append(_muc("Ads dùng ID thật", CANH_BAO, f"không mở được app để kiểm: {exc}"))
    muc.append(muc_sdk(sdk))
    nhanh = "nextgen" if sdk_probe.la_nextgen(sdk) else "tc"
    if nhanh == "nextgen":
        muc = noi_long_nextgen(muc)
    else:
        muc += _sheets(package, tc, out_dir)
    muc.append(_ram())
    return {"ok": all(m["trang_thai"] != LOI for m in muc), "muc": muc, "sdk": sdk, "nhanh": nhanh}


def in_bang(kq: dict, log_fn) -> None:
    dau = {OK: "OK  ", LOI: "LOI ", CANH_BAO: "CHU Y"}
    for m in kq["muc"]:
        log_fn(f"  [{dau[m['trang_thai']]}] {m['ten']}: {m['chi_tiet']}")
        if m["viec_can_lam"]:
            log_fn(f"         -> {m['viec_can_lam']}")
    if kq.get("nhanh") == "nextgen":
        log_fn(f"Nhanh: checklist Next-Gen (SDK {kq['sdk']}) - lam theo sdk-check/WORKFLOW.md")
    log_fn("San sang chay." if kq["ok"] else "CHUA chay duoc - xu cac dong LOI truoc.")
