"""Thu bang chung tren may cho checklist SDK Next-Gen (muc 1, 3, 4).

Moi luot ghi ra mot file log rieng trong `out_dir`, kem `bang-chung.json`. Phan
cham (`sdk_nextgen_cham_*`) chi doc cac file nay -> cham lai bao nhieu lan cung
ra mot ket qua (`rcr-sdk-check --cham-lai <thu muc>`), va test duoc bang log that.

Luot:
  khoi_dong  10 lan pm clear + mo lanh, cho 10 s                         (1.1, 1.3, 1.5, MED-01)
  mo_lai     10 lan force-stop + am start -W                             (1.4)
  fo         user moi di het FO toi Home, roi Home -> mo lai x2          (muc 3, 1.7, EV-25, HT-04, HV-02)
             BO QUA khi 10 lan mo lanh khong co event quang cao nao (RC tat ads): moi dong dua vao
             FO deu ra Do tay, lai FO chi ton ~1,7 phut (AIP920 1.6.0, 28/10/2026)
  offline    tat wifi + data, mo app, cho 30 s; bat mang, di tiep FO     (EV-04/21/24, KT-01)
  cham       proxy lam cham moi host, do luc roi splash                  (KT-02)
Lai FO dung script `sdk-check/scripts/*.sh` (cung cach skill goc).
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path

from . import device_app, fa_log, net_ctl, rc_baseline
from .adb_parsers import AdbError
from .models import RcError
from .sdk_nextgen_cham_build import DEMO, MARK_TAG

SCRIPTS = Path(__file__).resolve().parents[2] / "sdk-check" / "scripts"
SO_LAN = 10
CHO_KHOI_DONG_S = 10.0
CHO_OFFLINE_S = 30.0       # KT-01: "doi toi da 30 giay"
CHO_CHAM_TOI_DA_S = 120.0  # KT-02: mang cham, cho roi splash toi da
# Skill goc do KT-02 bang `slow_ads_proxy.py 8899 3 8`. Cong lay cong trong moi luot, khong co
# dinh 8899: hai may chay song song thi proxy thu hai khong bind duoc (loi bi nuot vao DEVNULL),
# ca hai may di qua proxy dau, luot dau xong go proxy -> may kia mat mang giua KT-02 (do 2026-10-27).
PROXY_TRE_S, PROXY_KBPS = 3, 8


def cong_trong() -> int:
    import socket
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]
BUFFERS = "main,system,crash,events"
_TOTAL = re.compile(r"TotalTime:\s*(\d+)")
_MIN_SDK = re.compile(r"minSdk=(\d+)")
_TOP = re.compile(r"(?:topResumedActivity|mResumedActivity)=\S+ \S+ \S+/(\S+)")


def bash() -> str:
    """Git Bash tren Windows (bash.exe trong System32 la WSL, khong co adb), bash thuong noi khac.

    `git` co the nam o `Git/cmd`, `Git/bin` hay `Git/mingw64/bin` -> do len toi thu muc Git.
    """
    git = shutil.which("git")
    if git:
        for goc in list(Path(git).parents)[:3]:
            for c in (goc / "bin" / "bash.exe", goc / "usr" / "bin" / "bash.exe"):
                if c.exists():
                    return str(c)
    if sys.platform == "win32":
        raise RcError("Không thấy Git Bash (cần để chạy script lái app trong sdk-check/scripts)")
    return shutil.which("bash") or "bash"


class GhiLog:
    """`adb logcat` chay nen ghi vao file trong mot khoi `async with`."""

    def __init__(self, client, serial: str, path: Path):
        self.client, self.serial, self.path = client, serial, path

    async def __aenter__(self):
        # Xoa CA 4 buffer: buffer events con dong am_anr cua phien truoc -> cham ANR oan.
        await self.client._run("-s", self.serial, "logcat", "-b", BUFFERS, "-c")
        self.f = open(self.path, "wb")
        self.proc = subprocess.Popen([self.client.adb, "-s", self.serial, "logcat", "-v", "threadtime", "-b", BUFFERS],
                                     stdout=self.f, stderr=subprocess.DEVNULL)
        await asyncio.sleep(0.5)
        return self

    async def __aexit__(self, *exc):
        await asyncio.sleep(1.0)  # dong cuoi con trong buffer
        try:
            self.proc.terminate()
            self.proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.proc.kill()
        finally:
            self.f.close()


async def _moc(client, serial: str, text: str) -> None:
    await client.shell(serial, "log", "-t", MARK_TAG, f"'{text}'")


async def _moi(client, serial: str, package: str) -> None:
    """User moi: xoa du lieu + cap san quyen thong bao (khong de hop quyen chan luong)."""
    await device_app.force_stop(client, serial, package)
    await client.shell(serial, "pm", "clear", package)
    await client.shell(serial, "pm", "grant", package, "android.permission.POST_NOTIFICATIONS")


def _bash(serial: str, script: str, *args: str, timeout: float) -> tuple[bool, str]:
    """Chay script lai app voi ANDROID_SERIAL (nhieu may cam cung luc khong lai nham may). -> (ok, nhat ky)."""
    try:
        r = subprocess.run([bash(), str(SCRIPTS / script), *args], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=timeout, cwd=str(SCRIPTS),
                           env={**os.environ, "ANDROID_SERIAL": serial})
        return r.returncode == 0, r.stdout + r.stderr
    except subprocess.TimeoutExpired as exc:
        return False, f"{script}: quá {timeout:.0f}s ({exc})"


async def top(client, serial: str) -> str:
    out, _, _ = await client.shell(serial, "dumpsys", "activity", "activities")
    m = _TOP.search(out)
    return m.group(1) if m else ""


async def cho_roi_splash(client, serial: str, toi_da: float) -> tuple[float | None, str]:
    """Giay tu luc mo toi khi man top khong con la Splash (AdActivity cung tinh: ad da load xong)."""
    t0 = time.monotonic()
    man = ""
    while time.monotonic() - t0 < toi_da:
        man = await top(client, serial)
        if man and "splash" not in man.lower() and "permission" not in man.lower():
            return round(time.monotonic() - t0, 1), man
        await asyncio.sleep(0.5)
    return None, man


async def splash_timeout_rc(client, serial: str, package: str) -> tuple[float | None, str]:
    """Timeout splash khai trong RC (doc duoc khi app debuggable / may root). -> (giay, key)."""
    try:
        cfg = (await rc_baseline.read(client, serial, package)).configs
    except (AdbError, RcError, OSError):  # ban release: khong doc duoc RC -> dung moc mac dinh
        return None, ""
    for k, v in sorted(cfg.items()):
        if re.search(r"splash.*time_?out|time_?out.*splash", k, re.I) and str(v).strip().replace(".", "", 1).isdigit():
            x = float(v)
            return (x / 1000 if x > 1000 else x), k
    return None, ""


async def thu_apk(client, serial: str, package: str, out: Path) -> dict:
    """File trong APK (base + split), co debuggable, minSdk app demo."""
    paths, _, _ = await client.shell(serial, "pm", "path", package)
    files: set[str] = set()
    for i, remote in enumerate(x.split(":", 1)[1].strip() for x in paths.splitlines() if x.startswith("package:")):
        local = out / f"apk-{i}.apk"
        await client._run("-s", serial, "pull", remote, str(local), timeout=180)
        if local.exists():
            with zipfile.ZipFile(local) as z:
                files.update(z.namelist())
            local.unlink()  # chi can danh sach file, khong giu APK (nang, co the chua key)
    info, _, _ = await client.shell(serial, "dumpsys", "package", package)
    demo = {}
    for p in DEMO:
        d, _, _ = await client.shell(serial, "dumpsys", "package", p)
        m = _MIN_SDK.search(d)
        demo[p] = int(m.group(1)) if m else None
    return {"apk_files": sorted(files), "debuggable": "DEBUGGABLE" in info, "demo_min_sdk": demo}


async def khoi_dong(client, serial: str, package: str, out: Path, log_fn) -> None:
    async with GhiLog(client, serial, out / "log-khoi-dong.txt"):
        for i in range(1, SO_LAN + 1):
            log_fn(f"  mở lạnh user mới {i}/{SO_LAN}")
            await _moi(client, serial, package)
            await _moc(client, serial, f"lan {i}")
            await device_app.launch(client, serial, package)
            await asyncio.sleep(CHO_KHOI_DONG_S)
        await device_app.force_stop(client, serial, package)


async def mo_lai(client, serial: str, package: str, out: Path, log_fn) -> list[int]:
    ms: list[int] = []
    component = await device_app.resolve_launcher(client, serial, package)
    async with GhiLog(client, serial, out / "log-mo-lai.txt"):
        for i in range(1, SO_LAN + 1):
            await device_app.force_stop(client, serial, package)
            await _moc(client, serial, f"lan {i}")
            o, _, _ = await client.shell(serial, "am", "start", "-W", "-n", component)
            m = _TOTAL.search(o)
            if m:
                ms.append(int(m.group(1)))
            log_fn(f"  mở lại {i}/{SO_LAN}: TotalTime {m.group(1) if m else '?'} ms")
            await asyncio.sleep(4)
        await device_app.force_stop(client, serial, package)
    return ms


async def fo(client, serial: str, package: str, out: Path, log_fn) -> tuple[str, str]:
    """-> (nhat ky, loi). Loi khac rong = lai FO khong toi Home: cham Sai tren log nay khong tin duoc."""
    # Tuyet doi: _bash chay voi cwd=SCRIPTS, duong dan tuong doi (out/...) tro nham cho, script khong ghi duoc marks
    marks = (out.resolve() / "marks-fo.txt").as_posix()
    loi = ""
    async with GhiLog(client, serial, out / "log-fo.txt"):
        await _moi(client, serial, package)
        log_fn("  lái FO user mới tới Home")
        ok, nhat_ky = _bash(serial, "drive-fo-to-home.sh", package, marks, "noclear", timeout=360)
        if not ok:
            loi = "drive-fo-to-home không tới Home"
        for r in (1, 2):
            log_fn(f"  Home → mở lại app (app open) {r}/2")
            await client.shell(serial, "input", "keyevent", "HOME")
            await asyncio.sleep(6)
            await _moc(client, serial, f"resume {r}")
            await device_app.launch(client, serial, package)
            await asyncio.sleep(4)
            ok, nk = _bash(serial, "continue-fo-from-current-screen.sh", marks, "MainActivity", timeout=90)
            nhat_ky += nk
            if not ok and not loi:
                loi = f"không về Home sau lần mở lại {r}"
    return nhat_ky, loi


async def offline(client, serial: str, package: str, out: Path, log_fn) -> dict:
    """Mat mang tu luc mo app; sau toi da 30 s bat mang, di tiep FO toi man sau xem ad load lai (KT-01)."""
    log_fn(f"  mất mạng: pm clear + mở app, chờ tối đa {CHO_OFFLINE_S:.0f}s rời splash")
    ra: dict = {}
    try:
        async with GhiLog(client, serial, out / "log-offline.txt"):
            ra["offline_mang_that_tat"] = not (await net_ctl.tat(client, serial))["thong"]
            await _moi(client, serial, package)
            await device_app.launch(client, serial, package)
            roi, man = await cho_roi_splash(client, serial, CHO_OFFLINE_S)
            ra.update(offline_roi_splash_s=roi, offline_man=man)
            await asyncio.sleep(max(0.0, 8 - (roi or 0)))  # de lib kip xin / bao loi
            log_fn("  bật mạng lại, đi tiếp FO")
            await _moc(client, serial, "mang bat")
            ra["offline_bat_lai"] = await net_ctl.bat(client, serial)
            ok, _ = _bash(serial, "continue-fo-from-current-screen.sh", (out.resolve() / "marks-offline.txt").as_posix(),
                          "Onboarding|Question|MainActivity", timeout=150)
            ra["offline_di_tiep_ok"] = ok
            await asyncio.sleep(10)  # cho ad o man sau load
            await device_app.force_stop(client, serial, package)
    finally:
        await net_ctl.bat(client, serial)  # luon tra mang, ke ca khi luot hong
    return ra


async def mang_cham(client, serial: str, package: str, out: Path, log_fn) -> dict:
    """KT-02: moi host qua proxy tre 3 s + 8 KB/s; do luc roi splash so voi timeout splash."""
    timeout_s, key = await splash_timeout_rc(client, serial, package)
    log_fn(f"  mạng chậm (proxy {PROXY_TRE_S}s, {PROXY_KBPS} KB/s), timeout splash: {timeout_s or 'mặc định 60'}s {key}")
    cong = cong_trong()
    proxy = subprocess.Popen([sys.executable, "-I", str(SCRIPTS / "slow_ads_proxy.py"), str(cong), str(PROXY_TRE_S),
                              str(PROXY_KBPS)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    ra: dict = {"cham_timeout_s": timeout_s, "cham_timeout_key": key}
    try:
        await client._run("-s", serial, "reverse", f"tcp:{cong}", f"tcp:{cong}")
        await client.shell(serial, "settings", "put", "global", "http_proxy", f"127.0.0.1:{cong}")
        async with GhiLog(client, serial, out / "log-cham.txt"):
            await _moi(client, serial, package)
            await device_app.launch(client, serial, package)
            roi, man = await cho_roi_splash(client, serial, CHO_CHAM_TOI_DA_S)
            ra.update(cham_roi_splash_s=roi, cham_man=man)
            await asyncio.sleep(3)
            await device_app.force_stop(client, serial, package)
    finally:
        # Luon go proxy: de lai la may mat mang moi luot sau.
        await client.shell(serial, "settings", "put", "global", "http_proxy", ":0")
        await client._run("-s", serial, "reverse", "--remove", f"tcp:{cong}")
        proxy.terminate()
    return ra


def dem_ads(log: Path) -> int:
    """So event quang cao app ban ra trong log (do 2026-10-28: app co ads 166, AIP920 RC tat ads 0)."""
    from .sdk_nextgen_events import AD_EVENTS
    try:
        text = log.read_text("utf-8", "replace")
    except OSError:
        return -1                         # khong doc duoc -> khong ket luan "khong co ads"
    return sum(1 for e in fa_log.parse(text) if e["name"].split("(", 1)[0] in AD_EVENTS)


async def thu(client, serial: str, package: str, out: Path, muc: set[str], log_fn) -> dict:
    """Chay cac luot can cho `muc`, ghi `bang-chung.json`. Tra bang chung (khong kem noi dung log)."""
    out.mkdir(parents=True, exist_ok=True)
    await fa_log.bat(client, serial)
    await client.shell(serial, "setprop", "debug.firebase.analytics.app", package)
    await client._run("-s", serial, "logcat", "-G", "16M")
    bc: dict = {"package": package, "serial": serial, "muc": sorted(muc)}
    if muc & {"1", "4"}:
        log_fn("Đọc APK + app demo...")
        bc.update(await thu_apk(client, serial, package, out))
        log_fn("Lượt mở lạnh...")
        await khoi_dong(client, serial, package, out, log_fn)
        bc["ads_khoi_dong"] = dem_ads(out / "log-khoi-dong.txt")
    if "1" in muc:
        log_fn("Lượt mở lại...")
        bc["mo_lai_ms"] = await mo_lai(client, serial, package, out, log_fn)
    if "ads_khoi_dong" in bc and bc["ads_khoi_dong"] == 0:
        bc["fo_bo_qua"] = ("bỏ lượt FO: 10 lần mở lạnh không có event quảng cáo nào "
                           "(Remote Config đang tắt ads?)")
        bc["fo_loi"], bc["nhat_ky_fo"] = "", ""
        log_fn(f"  {bc['fo_bo_qua']}")
    else:
        log_fn("Lượt FO + quay lại app...")
        nhat_ky, bc["fo_loi"] = await fo(client, serial, package, out, log_fn)
        bc["nhat_ky_fo"] = nhat_ky[-4000:]
    if muc & {"3", "4"}:
        bc.update(await offline(client, serial, package, out, log_fn))
    if "4" in muc:
        bc.update(await mang_cham(client, serial, package, out, log_fn))
    bc["ad_click"] = {f.name: fa_log.ad_clicks(fa_log.parse(f.read_text("utf-8", "replace")))
                      for f in sorted(out.glob("log-*.txt"))}
    (out / "bang-chung.json").write_text(json.dumps(bc, ensure_ascii=False, indent=1), "utf-8")
    return bc
