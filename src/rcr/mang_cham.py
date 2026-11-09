"""Lam cham rieng duong toi ad server de tao precondition "ad VE MUON" - khong can root.

VI SAO: bo TC co cac case doi ad chua ve luc user roi man ("Di qua LFO2 ngay khi vao man de 202 chua
kip show", "Roi OB3 truoc khi 303 ve", "throttle mang"). Ad duoc preload tu Splash/LFO1 nen tren mang
that no ve truoc khi user toi man -> truoc day tool ghi "may khong root, khong co proxy" va de BLOCKED
(AIP872 1.9.0, 05/11/2026: S03-01, S04-01). Repo da co `sdk-check/scripts/slow_ads_proxy.py` (nhanh
Next-Gen dung): proxy HTTP CONNECT tren may tinh, may Android tro toi qua `adb reverse` + `http_proxy`.
Chi domain quang cao bi lam cham, Firebase / app di thang.

Tao dieu kien la CHUA DU: ket qua case chi duoc nhan khi log cho thay ad that su chua show o man do
(`assert_ad_screen.ad_man_nha_da_show`) - run_batch kiem va ha BLOCKED neu chua dat.
"""
from __future__ import annotations

import asyncio
import re
import socket
import subprocess
import sys
import zlib
from pathlib import Path

from . import assert_ad_screen
from .app_sandbox import guard

PYTHON_GOC = getattr(sys, "_base_executable", None) or sys.executable
PROXY_SCRIPT = Path(__file__).resolve().parents[2] / "sdk-check" / "scripts" / "slow_ads_proxy.py"
# Domain quang cao (giong ghi chu trong slow_ads_proxy.py). Firebase khong nam trong day.
AD_HOSTS = ("doubleclick|googlesyndication|googleads|admob|googleadservices|facebook|fbcdn|applovin"
            "|mtgglobals|rayjump|pangle|vungle|byteoversea")
# GMA cat socket sau ~10s: tre >= 10s thi ad FAIL chu khong ve muon (doc trong slow_ads_proxy.py).
TRE_KET_NOI_S = 6.0
# KB/s moi chieu: anh native / inter vai tram KB -> tai them vai giay sau khi ket noi.
TOC_DO_KBPS = 20.0

# Ma man trong cau precondition: LFO2, OB3...
_MAN = r"(LFO\s*\d|OB\s*\d)"
_CHUA_SHOW_O = re.compile(r"ch[ưu]a\s+(?:k[ịi]p\s+)?show\s+(?:ở|o|tại|tai)\s+" + _MAN, re.I)
# "Di qua LFO2 ngay khi vao man de 202 chua kip show" (TC 3.5.4 S03-01): man nam truoc cum "chua kip show".
_QUA_MAN_CHUA_SHOW = re.compile(r"qua\s+" + _MAN + r"\b.{0,60}?ch[ưu]a\s+(?:k[ịi]p\s+)?show", re.I)
_ROI_TRUOC_KHI_VE = re.compile(r"r[ờo]i\s+" + _MAN + r"\s+tr[ưu][ớo]c\s+khi\s+.{0,60}?\bv[ềe]\b", re.I)
_THROTTLE = re.compile(r"throttle|m[ạa]ng\s+ch[ậa]m|\d+\s*kbps|m[ạa]ng\s+v[ừu]a\s+ph[ảa]i|show\s+mu[ộo]n"
                       r"|show\s+sau\s+~?\s*\d", re.I)


def _ma_man(s: str) -> str:
    return re.sub(r"\s+", "", s).lower()


def can_lam_cham(precondition: str) -> tuple[bool, str]:
    """(precondition can ad ve muon?, man ma ad KHONG duoc show tai do - '' neu cau khong noi man)."""
    text = precondition or ""
    for mau in (_CHUA_SHOW_O, _QUA_MAN_CHUA_SHOW, _ROI_TRUOC_KHI_VE):
        m = mau.search(text)
        if m:
            return True, _ma_man(m.group(1))
    if _THROTTLE.search(text):
        return True, ""
    return False, ""


def cong_cua(serial: str) -> int:
    """Moi may mot cong: bot chay song song nhieu may tren cung may tinh."""
    return 18000 + zlib.crc32(serial.encode()) % 1000


async def _cho_cong_mo(cong: int, han_s: float = 5.0) -> bool:
    buoc = 0.1
    for _ in range(int(han_s / buoc)):
        with socket.socket() as s:
            s.settimeout(buoc)
            if s.connect_ex(("127.0.0.1", cong)) == 0:
                return True
        await asyncio.sleep(buoc)
    return False


async def bat(client, serial: str) -> dict:
    """Chay proxy cham + tro may vao no. Tra trang thai de `tat` go dung nhu cu."""
    guard(serial)
    cong = cong_cua(serial)
    # Python goc, khong qua launcher cua venv: tren Windows `.venv/Scripts/python.exe` la trinh chuyen tiep,
    # terminate no co the de lai tien trinh con van giu cong (proxy song sau khi tat).
    proc = subprocess.Popen(
        [PYTHON_GOC, "-I", str(PROXY_SCRIPT), str(cong), str(TRE_KET_NOI_S), str(TOC_DO_KBPS), AD_HOSTS],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    trang_thai = {"proc": proc, "cong": cong}
    try:
        if not await _cho_cong_mo(cong):
            raise RuntimeError(f"proxy cham khong mo duoc cong {cong}")
        _, err, rc = await client._run("-s", serial, "reverse", f"tcp:{cong}", f"tcp:{cong}")
        if rc:
            raise RuntimeError(f"adb reverse loi: {err.strip()}")
        await client.shell(serial, "settings", "put", "global", "http_proxy", f"127.0.0.1:{cong}")
    except BaseException:
        await tat(client, serial, trang_thai)
        raise
    return trang_thai


async def tat(client, serial: str, trang_thai: dict) -> None:
    """Go proxy: may con tro vao proxy da tat la mat mang cho moi luot sau. Luon chay, ke ca khi case hong."""
    guard(serial)
    cong = trang_thai.get("cong")
    try:
        await client.shell(serial, "settings", "put", "global", "http_proxy", ":0")
        if cong:
            await client._run("-s", serial, "reverse", "--remove", f"tcp:{cong}")
    finally:
        proc = trang_thai.get("proc")
        if proc is not None and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()


def _unit_cua_man(units, man: str) -> list[dict]:
    return [u for u in units
            if any((v := assert_ad_screen._man_cua_key(k)) and v[1] == man for k in (u.get("rc_keys") or ()))]


def kiem_dieu_kien(runs: list[dict], man: str, da_bat: bool, loi: str = "") -> tuple[list[str], str]:
    """(ly do chua tao duoc precondition, ghi chu cach da tao) sau khi case chay voi mang cham.

    Dat = ad cua man `man` CO ve (load) nhung KHONG show ngay tai `man`. Ad khong ve lan nao la
    nhanh no-fill / timeout chu khong phai "ve muon" -> chua dat (FAIL "OB5 khong hien 303" luc do la FAIL gia).
    """
    if not da_bat:
        return [loi or "không bật được proxy làm chậm ad"], ""
    if not man:
        return [], (mo_ta() + " — precondition không nêu màn nên chưa kiểm được bằng log ad có về muộn "
                    "đúng như TC; đối chiếu log trước khi nhận kết quả")
    ten = man.upper()
    show_som, co_ve = [], False
    for run in runs or ():
        units = list(((run.get("ads") or {}).get("units") or {}).values())
        show_som += assert_ad_screen.ad_man_nha_da_show(run.get("events"), units, man)
        co_ve = co_ve or any(u.get("loaded") or u.get("shown") for u in _unit_cua_man(units, man))
    if show_som:
        return [f"đã làm chậm ad nhưng ad {ten} ({', '.join(sorted(set(show_som)))}) vẫn show ngay ở {ten} "
                f"— chưa tạo được điều kiện ad về muộn"], ""
    if not co_ve:
        return [f"đã làm chậm ad nhưng ad {ten} không về lần nào (fail / no-fill), không phải về muộn"], ""
    return [], f"{mo_ta()}; log xác nhận ad {ten} có về nhưng không show ngay ở {ten}"


def mo_ta() -> str:
    return (f"làm chậm domain quảng cáo qua proxy (trễ kết nối {TRE_KET_NOI_S:.0f}s, "
            f"{TOC_DO_KBPS:.0f} KB/s; Firebase/app đi thẳng)")
