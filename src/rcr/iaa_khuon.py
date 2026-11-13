"""Duong lai IAA theo KHUON (template app), khong theo tung package.

Cac app gen anh/video cung template (AIP885, AIP893, AIP922, AIP959... - muc 3 sheet KT cung bo vi tri native_loading /
native_upload / native_i2i_i2v_prompt / result_img_vid / reward_img_vid / inter_feature / inter_style / uninstall) chi
khac CHU tren nut. `data/iaa_duong_lai.yaml`:

  khuon:
    ai_photo:
      nhan_dien: "<regex chu chi co o Home cua khuon>"
      doan: [ {ten, buoc: [...]}, ... ]        # buoc dung regex gom chu cua cac app (A|B|C)
  <package>: {khuon: ai_photo}                 # ghim khuon (tuy chon)
  <package>: [ {ten, buoc}, ... ]              # duong lai rieng (app khac han khuon)

App chua khai -> tool lai FO toi Home roi chon khuon co `nhan_dien` khop chu tren Home: app moi cung khuon chay luon,
khong phai do duong lai. Doan lech chu thi chi doan do HONG (bao ly do), cac doan khac van chay.
"""

from __future__ import annotations

import asyncio
import re
import subprocess
import tempfile
from pathlib import Path

from . import rating_cong_thuc

DATA = Path(__file__).parent / "data" / "iaa_duong_lai.yaml"


def _doc() -> dict:
    import yaml
    return yaml.safe_load(DATA.read_text(encoding="utf-8")) or {}


def cac_khuon() -> dict:
    return _doc().get("khuon") or {}


def doan_khai_san(package: str) -> tuple[str, list[dict] | None]:
    """(ten nguon, doan) da khai cho package (rieng hoac ghim khuon); chua khai -> ("", None)."""
    muc = _doc().get(package)
    if isinstance(muc, list):
        return package, muc
    if isinstance(muc, dict) and muc.get("khuon"):
        k = cac_khuon().get(muc["khuon"])
        return (f"khuôn {muc['khuon']}", k.get("doan")) if k else ("", None)
    return "", None


def khuon_khop(nodes) -> tuple[str, list[dict] | None]:
    """Khuon dau tien co chu `nhan_dien` tren man Home dang hien."""
    for ten, k in cac_khuon().items():
        if k.get("nhan_dien") and rating_cong_thuc.tim(nodes, k["nhan_dien"]):
            return f"khuôn {ten}", k.get("doan")
    return "", None


async def chon(client, serial: str, package: str, log: list[str]) -> tuple[str, list[dict] | None]:
    """Duong lai cua app: khai san, khong thi lai FO toi Home va nhan khuon theo chu."""
    # Luon lai FO toi Home truoc (ke ca app da ghim khuon): sau pm clear app dung o FO, cac doan bat dau tu Home.
    await rating_cong_thuc._mot_buoc(client, serial, package, {"ve_man": "MainActivity|HomeActivity", "toi_da": 150},
                                     log)
    await rating_cong_thuc._mot_buoc(client, serial, package, {"dong_neu_co": "^(Close|Close sheet)$"}, log)
    nguon, doan = doan_khai_san(package)
    if doan:
        return nguon, doan
    await asyncio.sleep(1.0)
    return khuon_khop(await rating_cong_thuc._nodes(client, serial, package))


def _aapt() -> str:
    """aapt moi nhat trong Android SDK (ANDROID_HOME / ~/Android/Sdk / Windows LOCALAPPDATA)."""
    import os
    goc = [os.environ.get("ANDROID_HOME", ""), os.environ.get("ANDROID_SDK_ROOT", ""), str(Path.home() / "Android/Sdk"),
           str(Path(os.environ.get("LOCALAPPDATA", "")) / "Android/Sdk")]
    for g in filter(None, goc):
        bt = sorted((Path(g) / "build-tools").glob("*/aapt*"))
        if bt:
            return str(bt[-1])
    return ""


async def nhan_icon(client, serial: str, package: str) -> str:
    """Ten app tren launcher (application-label trong APK) - de tim icon khi nhan giu mo shortcut."""
    out, _, _ = await client.shell(serial, "pm", "path", package)
    duong = next((d.split(":", 1)[1].strip() for d in (out or "").splitlines() if d.startswith("package:")), "")
    aapt = _aapt()
    if not duong or not aapt:
        return ""
    with tempfile.TemporaryDirectory() as tmp:
        apk = Path(tmp) / "base.apk"
        await client._run("-s", serial, "pull", duong, str(apk), timeout=120)
        if not apk.is_file():
            return ""
        kq = subprocess.run([aapt, "dump", "badging", str(apk)], capture_output=True, text=True, errors="replace")
    m = re.search(r"^application-label:'([^']+)'", kq.stdout or "", re.M)
    return m.group(1) if m else ""
