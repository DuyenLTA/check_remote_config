"""Ban release (khong run-as): baseline + verify doc Remote Config THAT tu Firebase theo version cua APK.

Di cung `rc_firebase` (doi RC tren server qua dieu kien `testvsl`). Khong doc duoc file config trong data app,
nen "gia tri dang song" = gia tri Firebase tra cho dung app + version nay (REST fetch cua client, nhu SDK goi luc
mo app). App vua `pm clear` roi mo len fetch dung cac gia tri nay (do 30/10/2026, AIP886 2.7.0).
"""

from __future__ import annotations

import asyncio
import base64
import json
import os
import re
import subprocess
import tempfile
import time
import urllib.request
from pathlib import Path

from .adb_parsers import AdbError
from .models import RcBaseline, RcError

WRITE_MODE = "firebase"


def _aapt2() -> str:
    roots = [os.environ.get("ANDROID_HOME"), os.environ.get("ANDROID_SDK_ROOT"), "~/Android/Sdk",
             "~/Library/Android/sdk", "~/AppData/Local/Android/Sdk"]
    for root in filter(None, roots):
        bt = Path(os.path.expanduser(root)) / "build-tools"
        for ver in sorted((p.name for p in bt.iterdir()) if bt.is_dir() else (),
                          key=lambda v: [int(x) if x.isdigit() else 0 for x in v.split(".")], reverse=True):
            for ten in ("aapt2", "aapt2.exe"):
                if (bt / ver / ten).is_file():
                    return str(bt / ver / ten)
    raise RcError("không thấy aapt2 (Android SDK build-tools) để đọc Firebase project trong APK")


def thong_tin_apk(apk: Path) -> dict:
    """{project, app_id, api_key, package, version} doc tu resource cua APK."""
    a = _aapt2()
    res = subprocess.run([a, "dump", "resources", str(apk)], capture_output=True, encoding="utf-8",
                         errors="replace").stdout
    badge = subprocess.run([a, "dump", "badging", str(apk)], capture_output=True, encoding="utf-8",
                           errors="replace").stdout

    def chuoi(ten: str) -> str:
        m = re.search(r"string/" + ten + r"\b.*?\n\s*\(\)\s*\"([^\"]+)\"", res, re.S)
        if not m:
            raise RcError(f"APK không có string/{ten} - app không dùng Firebase?")
        return m.group(1)

    return {"project": chuoi("project_id"), "app_id": chuoi("google_app_id"), "api_key": chuoi("google_api_key"),
            "package": re.search(r"package: name='([^']+)'", badge).group(1),
            "version": re.search(r"versionName='([^']+)'", badge).group(1)}


def _post(url: str, body: dict, headers: dict) -> dict:
    from .rc_firebase import _mang

    req = urllib.request.Request(url, json.dumps(body).encode(), {"Content-Type": "application/json", **headers})

    def goi():
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.load(r)
    return _mang(goi)


# Installation Firebase gia lap (fid + auth token, song 7 ngay) nho theo app trong tien trinh: moi case doi chieu
# 2 lan (verify sau patch + verify cuoi) - tao installation moi moi lan la them 1 lan goi (~0,8s). Dieu kien testvsl
# theo app.id + version, khong theo fid, nen dung lai mot installation van ra dung gia tri cua may vua pm clear.
INST_SONG = 3600.0
_INST: dict[tuple[str, str], tuple[str, str, float]] = {}


def _installation(info: dict) -> tuple[str, str]:
    khoa = (info["project"], info["app_id"])
    co = _INST.get(khoa)
    if co and co[2] > time.monotonic():
        return co[0], co[1]
    fid = base64.urlsafe_b64encode(bytes([0x70 | (os.urandom(1)[0] & 0x0F)]) + os.urandom(16)).decode()[:22]
    inst = _post(f"https://firebaseinstallations.googleapis.com/v1/projects/{info['project']}/installations",
                 {"fid": fid, "appId": info["app_id"], "authVersion": "FIS_v2", "sdkVersion": "a:17.0.0"},
                 {"x-goog-api-key": info["api_key"], "X-Android-Package": info["package"]})
    _INST[khoa] = (inst["fid"], inst["authToken"]["token"], time.monotonic() + INST_SONG)
    return _INST[khoa][0], _INST[khoa][1]


def _fetch(info: dict, fid: str, tok: str, country: str) -> dict:
    return _post(f"https://firebaseremoteconfig.googleapis.com/v1/projects/{info['app_id'].split(':')[1]}"
                 f"/namespaces/firebase:fetch?key={info['api_key']}",
                 {"appInstanceId": fid, "appInstanceIdToken": tok, "appId": info["app_id"],
                  "countryCode": country, "languageCode": "en-US", "platformVersion": "36",
                  "timeZone": "Asia/Bangkok", "appVersion": info["version"], "packageName": info["package"],
                  "sdkVersion": "22.0.0", "analyticsUserProperties": {}},
                 {"X-Android-Package": info["package"], "X-Goog-Firebase-Installations-Auth": tok})


def gia_tri_that(info: dict, country: str = "VN") -> dict[str, str]:
    """Gia tri RC Firebase tra cho app + version nay (installation moi, nhu may vua pm clear)."""
    try:
        try:
            rc = _fetch(info, *_installation(info), country)
        except OSError:
            # Installation da nho bi tu choi (het han / bi xoa) -> tao moi, thu mot lan nua.
            _INST.pop((info["project"], info["app_id"]), None)
            rc = _fetch(info, *_installation(info), country)
    except OSError as exc:
        raise RcError(f"không đọc được Remote Config thật của {info['package']}: {exc}") from None
    return {str(k): str(v) for k, v in (rc.get("entries") or {}).items()}


def kiem_dieu_kien_test(info: dict) -> str:
    """Dieu kien `testvsl` co, dung thu 1, va bieu thuc nhac dung version dang test -> bieu thuc; khong -> RcError."""
    from . import rc_firebase

    t, _ = rc_firebase.doc(info["project"], rc_firebase.token())
    bt = rc_firebase.kiem_dieu_kien(t)
    if info["version"] not in bt:
        raise RcError(f"điều kiện `{rc_firebase.DIEU_KIEN}` không nhắc version {info['version']} đang test: {bt}")
    return bt


# Loi tren CHINH may bot (o dia, adb) - khong phai do dieu kien testvsl: bot_kiem_testvsl khong nho QA sua condition.
MAY_BOT = "[máy bot]"
HET_CHO_RE = re.compile(r"quota exceeded|no space left|ENOSPC", re.I)
APK_CU_GIAY = 30 * 60


def _don_apk_cu() -> None:
    """Xoa APK tam `rcr_fb_*.apk` con sot (luot chet giua chung khong toi `finally`): tich lai lam day /tmp - Ubuntu
    13/11/2026 bao `Disk quota exceeded` khi keo APK AIP892, bot bao nham la thieu dieu kien testvsl."""
    han = time.time() - APK_CU_GIAY
    for f in Path(tempfile.gettempdir()).glob("rcr_fb_*.apk"):
        try:
            if f.stat().st_mtime < han:
                f.unlink()
        except OSError:
            pass


async def thong_tin_tren_may(client, serial: str, package: str) -> dict:
    """Keo APK dang cai tren may -> `thong_tin_apk` (Firebase project, app id, version)."""
    from .dex_check import PUSH_TIMEOUT, apk_paths

    duong = await apk_paths(client, serial, package)
    if not duong:
        raise RcError(f"máy chưa cài {package}")
    _don_apk_cu()
    fd, ten = tempfile.mkstemp(prefix="rcr_fb_", suffix=".apk")
    os.close(fd)
    local = Path(ten)
    try:
        out, err, code = await client._run("-s", serial, "pull", duong[0], str(local), timeout=PUSH_TIMEOUT * 4)
        if code != 0:
            loi = (err or out).strip()
            if HET_CHO_RE.search(loi):
                raise AdbError(f"{MAY_BOT} ổ tạm `{local.parent}` hết chỗ / vượt quota khi kéo APK ({loi[:160]})")
            raise AdbError(f"Khong keo duoc {duong[0]}: {loi}")
        info = thong_tin_apk(local)
        # Nho app id cho App Tester: lan cai build sau mo thang trang app bang deep link, khong cuon tim.
        from . import app_tester_link
        app_tester_link.ghi(package, info.get("app_id", ""))
        return info
    finally:
        local.unlink(missing_ok=True)


async def don_testvsl(client, serial: str, package: str) -> str:
    """Go moi gia tri dieu kien `testvsl` cua Firebase project cua app (luot bi dung giua chung). Tra project."""
    from . import rc_firebase
    info = await thong_tin_tren_may(client, serial, package)
    await asyncio.to_thread(rc_firebase.tra_het, info["project"])
    return info["project"]


async def doc_baseline(client, serial: str, package: str) -> RcBaseline:
    """Baseline ban release: keo APK tu may -> Firebase project + version -> gia tri RC that."""
    info = await thong_tin_tren_may(client, serial, package)
    # Luot truoc chet giua chung (mat mang luc go) co the de lai gia tri tren testvsl -> don truoc khi doc baseline.
    from . import rc_firebase
    await asyncio.to_thread(rc_firebase.tra_het, info["project"])
    configs = gia_tri_that(info)
    return RcBaseline(package=package, serial=serial, app_id=info["app_id"], activate_name="", settings_name="",
                      activate_raw="", settings_raw="", configs=configs, write_mode=WRITE_MODE, firebase=info)
