"""Buoc Action cua tab TC "widget": xac nhan dialog ghim widget cua launcher, ra home screen dien thoai, tap widget.

AIP893 widget 12/11/2026: ba cau nay tool tra NEEDS_HUMAN ("khong dich duoc buoc"), Claude lam tay. Cach lam tay
duoc user duyet nen dong goi lai o day:
  "Xac nhan them widget tren dialog cua launcher (neu co)" -> bam "Add to Home screen" (Pixel) / "Add" / "Them"...;
      khong co dialog thi thoi. Nghe toast trong luc bam, doc `dumpsys appwidget` sau khi bam.
  "Ra home screen dien thoai, quan sat widget"            -> nhan Home, lat trang launcher toi khi thay widget app.
  "Tap vao widget"                                          -> tap widget, doc dong "Displayed" xem app mo tu man nao.

Ket qua ghi vao record cua buoc (`widget_xac_nhan` / `widget_launcher` / `mo_tu_widget`) cho `assert_widget` cham.
Man hinh luc nay la launcher (khong phai app) nen KHONG di qua luat Tap cua `case_drive` (man bi "che" -> dung).
"""

from __future__ import annotations

import asyncio
import re
import time
from dataclasses import dataclass

from . import device_app, device_motion, log_moc, ui_dump, widget_may
from .adb_parsers import AdbError

XAC_NHAN_RE = re.compile(r"(?:x[áa]c\s*nh[ậa]n|confirm|đồng\s*ý|dong\s*y).{0,40}widget|dialog\s+(?:c[ủu]a\s+)?launcher", re.I)
RA_LAUNCHER_RE = re.compile(
    r"^\s*(?:ra|v[ềe]|quay\s+v[ềe]|v[àa]o|m[ởo]|đi\s+t[ớo]i)\s+(?:home\s*screen|m[àa]n\s+h[ìi]nh\s+ch[íi]nh|launcher"
    r"|home\s+(?:c[ủu]a\s+)?(?:đi[ệe]n\s+tho[ạa]i|dien\s+thoai|m[áa]y))", re.I)
TAP_WIDGET_RE = re.compile(r"^\s*(?:tap|b[ấa]m|nh[ấa]n|click|ch[ạa]m)\s+(?:v[àa]o\s+)?(?:icon\s+)?widget\b", re.I)

CHO_DIALOG = 6.0          # dialog ghim widget hien sau ~1s ke tu luc bam CTA; khong co sau 6s = launcher tu them
NGHE_TOAST = 5.0          # toast Android hien ~2s (LENGTH_SHORT) - nghe du ca luc launcher dong dialog
CHO_APPWIDGET = 5.0
TRANG_TOI_DA = 5          # so lan lat trang launcher tim widget
CHO_SAU_THAO_TAC = 1.5
CHO_QUA_SPLASH = 40.0


@dataclass(frozen=True, slots=True)
class XacNhanWidget:
    reason: str

    @property
    def summary(self) -> dict:
        return {"kind": "xac_nhan_widget", "reason": self.reason}


@dataclass(frozen=True, slots=True)
class RaLauncher:
    reason: str

    @property
    def summary(self) -> dict:
        return {"kind": "ra_launcher", "reason": self.reason}


@dataclass(frozen=True, slots=True)
class TapWidget:
    reason: str

    @property
    def summary(self) -> dict:
        return {"kind": "tap_widget", "reason": self.reason}


LOAI = (XacNhanWidget, RaLauncher, TapWidget)


def resolve(text: str):
    """Cau buoc cua tab widget -> thao tac; cau khac -> None."""
    if XAC_NHAN_RE.search(text):
        return XacNhanWidget("bấm nút xác nhận trên dialog ghim widget của launcher (không có dialog thì thôi)")
    if RA_LAUNCHER_RE.match(text):
        return RaLauncher("nhấn Home ra launcher, lật trang tới khi thấy widget của app")
    if TAP_WIDGET_RE.match(text):
        return TapWidget("tap widget của app trên launcher, đọc màn app mở ra đầu tiên")
    return None


async def lam(client, serial: str, action, record: dict, ctx: dict) -> None:
    package = ctx["package"]
    if isinstance(action, XacNhanWidget):
        record["widget_xac_nhan"] = await _xac_nhan(client, serial, package)
    elif isinstance(action, RaLauncher):
        await device_motion.home(client, serial)
        await asyncio.sleep(CHO_SAU_THAO_TAC)
        record["widget_launcher"] = await _tim_tren_launcher(client, serial, package, ve_home=False)
        record["widget_launcher"]["appwidget"] = await widget_may.doc_appwidget(client, serial, package)
    elif isinstance(action, TapWidget):
        record["mo_tu_widget"] = await _tap_widget(client, serial, package, ctx)


async def _xac_nhan(client, serial: str, package: str) -> dict:
    ket = {"dialog": "", "toast": None, "appwidget": []}
    het = time.monotonic() + CHO_DIALOG
    chu, nut = None, None
    while True:
        chu, nut = widget_may.nut_xac_nhan(await ui_dump.dump(client, serial), package)
        if chu is not None or time.monotonic() >= het:
            break
        await asyncio.sleep(0.5)
    if chu == "":
        ket["loi"] = "dialog có nhiều nút cùng chữ — không đoán, không bấm"
    elif nut is not None:
        # Nghe toast SONG SONG voi cu bam: toast "Widget added!" hien ngay khi launcher bao da ghim.
        nghe = asyncio.create_task(widget_may.nghe_toast(client, serial, NGHE_TOAST))
        await asyncio.sleep(0.8)          # cho `uiautomator events` dang ky xong roi moi bam
        await device_app.tap(client, serial, *nut.bounds.center)
        ket["dialog"] = nut.text or nut.content_desc
        ket["appwidget"] = await _cho_appwidget(client, serial, package)
        try:
            _, ket["toast"] = await nghe
        except AdbError as exc:
            ket["toast_loi"] = str(exc)
    if not ket["appwidget"]:
        ket["appwidget"] = await _cho_appwidget(client, serial, package)
    await asyncio.sleep(CHO_SAU_THAO_TAC)
    return ket


async def _cho_appwidget(client, serial: str, package: str) -> list[dict]:
    het = time.monotonic() + CHO_APPWIDGET
    while True:
        ds = await widget_may.doc_appwidget(client, serial, package)
        if ds or time.monotonic() >= het:
            return ds
        await asyncio.sleep(1.0)


async def _tim_tren_launcher(client, serial: str, package: str, ve_home: bool = True) -> dict:
    """Lat trang launcher (vuot trai) toi khi thay widget app. Man khong doi nua = het trang -> dung."""
    if ve_home:
        await device_motion.home(client, serial)
        await asyncio.sleep(CHO_SAU_THAO_TAC)
    truoc = ""
    for trang in range(1, TRANG_TOI_DA + 1):
        xml = await ui_dump.dump(client, serial)
        khung = widget_may.vung_widget(xml, package)
        if khung:
            return {"thay": True, "trang": trang, "khung": list(khung)}
        if xml == truoc:
            break
        truoc = xml
        await device_app.swipe(client, serial, "left")
        await asyncio.sleep(CHO_SAU_THAO_TAC)
    return {"thay": False, "trang": 0, "khung": []}


async def _tap_widget(client, serial: str, package: str, ctx: dict) -> dict:
    xml = await ui_dump.dump(client, serial)
    khung = widget_may.vung_widget(xml, package)
    tim = {"thay": True, "khung": list(khung)} if khung else await _tim_tren_launcher(client, serial, package)
    if not tim["thay"]:
        return {"tap": False, "loi": "không thấy widget của app trên launcher", "displayed": []}
    l, t, r, b = tim["khung"]
    moc = await log_moc.bay_gio(client, serial)
    await device_app.tap(client, serial, (l + r) // 2, (t + b) // 2)
    ket = {"tap": True, "khung": tim["khung"], "moc": moc, "displayed": []}
    try:
        await device_app.wait_foreground(client, serial, package)
    except AdbError as exc:
        ket["loi"] = f"tap widget xong app không lên foreground: {exc}"
    ctx["o_nen"] = False
    await asyncio.sleep(2.0)              # de ActivityTaskManager ghi xong dong "Displayed" cua man dau
    tu = ["-T", moc] if moc else []
    log, _, _ = await client.shell(serial, "logcat", "-d", *tu, "-s", "ActivityTaskManager:I", "ActivityManager:I")
    ket["displayed"] = widget_may.parse_displayed(log, package)
    # Cho qua Splash nhu khi mo bang icon, de anh cuoi chup man that su sau Splash.
    het = time.monotonic() + CHO_QUA_SPLASH
    while time.monotonic() < het:
        _, act = await device_app.focus(client, serial)
        if act and "Splash" not in act:
            break
        await asyncio.sleep(1.0)
    return ket
