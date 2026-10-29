"""Cai build tu link Google Drive (ban debug QA gui kem), thay cho App Tester.

QA tra loi tin hoi cua bot kem link Drive (user chot 29/10/2026); file de "Ai co link deu xem duoc" -> tai thang
bang link, khong dang nhap Google. Tai xong kiem dung la APK roi `adb install`; cai xong doi chieu version + moc cai
tren may: APK sai package / sai version thi dung, khong de luot chay test nham ban (bai hoc AIP922 29/10/2026).
"""

from __future__ import annotations

import asyncio
import re
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

from .app_tester_ui import LoiCai, ban_dang_cai

ID_RE = re.compile(r"(?:/file/d/|/d/|[?&]id=)([A-Za-z0-9_-]{20,})")
LINK_RE = re.compile(r"https://(?:drive|docs)\.google\.com/\S+")
TAI_URL = "https://drive.usercontent.google.com/download?id={id}&export=download&confirm=t"
TIMEOUT_TAI = 900
CO_TOI_THIEU = 1_000_000          # APK that > 1 MB; nho hon thuong la trang loi HTML


class LoiDrive(RuntimeError):
    pass


def tim_link(chu: str) -> str:
    """Link Drive dau tien trong tin (bo dau <> / ngoac Discord hay boc quanh link). "" neu khong co."""
    m = LINK_RE.search(chu or "")
    return m.group(0).rstrip(">)].,") if m and ID_RE.search(m.group(0)) else ""


def file_id(link: str) -> str:
    m = ID_RE.search(link or "")
    if not m:
        raise LoiDrive(f"không đọc được ID file trong link Drive: {link!r}")
    return m.group(1)


def tai(link: str, thu_muc: Path) -> Path:
    """Tai file ve `thu_muc/drive-<id>.apk`, kiem la APK (zip co AndroidManifest.xml)."""
    fid = file_id(link)
    thu_muc.mkdir(parents=True, exist_ok=True)
    dich = thu_muc / f"drive-{fid}.apk"
    req = urllib.request.Request(TAI_URL.format(id=fid), headers={"User-Agent": "rcr-bot/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_TAI) as r, dich.open("wb") as f:
            loai = r.headers.get("Content-Type", "")
            if "text/html" in loai:
                raise LoiDrive("Drive trả về trang web, không phải file — mở quyền 'Ai có link đều xem được' "
                               "hoặc kiểm lại link")
            while chunk := r.read(1 << 20):
                f.write(chunk)
    except urllib.error.HTTPError as e:
        raise LoiDrive(f"Drive trả HTTP {e.code} — link sai hoặc file chưa chia sẻ công khai") from None
    except urllib.error.URLError as e:
        raise LoiDrive(f"không tải được từ Drive: {e.reason}") from None
    if dich.stat().st_size < CO_TOI_THIEU or not zipfile.is_zipfile(dich):
        raise LoiDrive("file tải về không phải APK (quá nhỏ / không phải zip) — link có trỏ đúng file .apk?")
    with zipfile.ZipFile(dich) as z:
        if "AndroidManifest.xml" not in z.namelist():
            raise LoiDrive("file tải về không có AndroidManifest.xml — không phải APK (.aab không cài thẳng được)")
    return dich


async def cai(client, serial: str, package: str, version: str, link: str, out_dir: Path) -> dict:
    """Tai APK tu `link` roi cai len may. Tra {package, version, debuggable, da_cai, go_ban_cu, nguon}."""
    try:
        apk = await asyncio.to_thread(tai, link, Path(out_dir) / "apk")
    except LoiDrive as e:
        raise LoiCai(str(e)) from None
    truoc = await ban_dang_cai(client, serial, package)
    go = False
    out, err, _ = await client._run("-s", serial, "install", "-r", "-d", str(apk), timeout=TIMEOUT_TAI)
    kq = (out + err).strip()
    if "INSTALL_FAILED_UPDATE_INCOMPATIBLE" in kq or "signatures do not match" in kq.lower():
        # debug <-> release khac chu ky: go ban dang cai (mat data app) roi cai lai.
        await client.shell(serial, "pm", "uninstall", package)
        go = True
        out, err, _ = await client._run("-s", serial, "install", "-r", "-d", str(apk), timeout=TIMEOUT_TAI)
        kq = (out + err).strip()
    if "Success" not in kq:
        raise LoiCai(f"adb install APK từ Drive lỗi: {kq[-300:]}")
    sau = await ban_dang_cai(client, serial, package)
    moi = sau and (go or not truoc or sau.get("cai_luc") != truoc.get("cai_luc"))
    if not moi:
        raise LoiCai(f"APK trên Drive không phải package {package} (cài xong máy vẫn là bản cũ)")
    if sau["version"] != version:
        raise LoiCai(f"APK trên Drive là {sau['version']}, tin build là {version} — gửi đúng link bản {version}")
    return {"package": package, "version": version, "debuggable": sau["debuggable"], "da_cai": True,
            "go_ban_cu": go, "nguon": "drive"}

