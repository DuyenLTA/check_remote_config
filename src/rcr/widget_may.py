"""Doc trang thai WIDGET cua app tren may: widget nao dang gan tren launcher, toast vua hien, nut xac nhan cua
dialog ghim widget, widget nam o dau tren home screen.

Tach rieng de `act_widget` (thao tac) va `assert_widget` (cham) dung chung bo doc, va de test duoc bang
chuoi output that ma khong can may (AIP893 widget 12/11/2026: ca 4 buoc nay truoc day Claude lam tay).
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET

from . import ui_dump

# `dumpsys appwidget`: muc "Widgets:" liet ke widget DANG GAN vao host (launcher). Muc "Providers:" chi la widget
# app khai bao - co ngay ca khi chua add, nen chi doc muc Widgets.
#   Widgets:
#     [0] id=3
#       host=HostId{user:0, app:10154, hostId:1024, pkg:com.google.android.apps.nexuslauncher}
#       provider=ProviderId{user:0, app:10321, cmp:ComponentInfo{<pkg>/<pkg>.widget.VslWidgetReceiver}}
WIDGETS_RE = re.compile(r"^Widgets:\s*$(.*?)(?=^\S[^\n]*:\s*$|\Z)", re.M | re.S)
KHOI_RE = re.compile(r"^\s*\[\d+\]\s+id=(\d+)", re.M)
PROVIDER_RE = re.compile(r"provider=.*?ComponentInfo\{([\w.]+)/([\w.$]+)\}")
HOST_PKG_RE = re.compile(r"host=.*?pkg:([\w.]+)")

# `uiautomator events`: toast phat TYPE_NOTIFICATION_STATE_CHANGED, ClassName la android.widget.Toast(...),
# chu cua toast nam trong "Text: [...]". Notification cua app cung phat event nay nhung ClassName khac.
TOAST_TEXT_RE = re.compile(r"Text:\s*\[([^\]]*)\]")

# Nut xac nhan cua dialog ghim widget (launcher / ROM). Thu tu = uu tien: cau dai, ro nghia truoc; "Add"/"Them"
# tran tru cuoi. So bang ca chu (khong phan biet hoa thuong), khong so chuoi con.
NUT_XAC_NHAN = ("add to home screen", "thêm vào màn hình chính", "add automatically", "thêm tự động",
                "add widget", "add", "thêm")


def parse_appwidget(out: str, package: str) -> list[dict]:
    """Widget cua `package` dang gan tren host -> [{id, provider, host}]."""
    m = WIDGETS_RE.search(out or "")
    if not m:
        return []
    phan = m.group(1)
    moc = [(k.start(), k.group(1)) for k in KHOI_RE.finditer(phan)]
    ra = []
    for i, (bat_dau, wid) in enumerate(moc):
        khoi = phan[bat_dau: moc[i + 1][0] if i + 1 < len(moc) else len(phan)]
        p = PROVIDER_RE.search(khoi)
        if not p or p.group(1) != package:
            continue
        h = HOST_PKG_RE.search(khoi)
        ra.append({"id": wid, "provider": f"{p.group(1)}/{p.group(2)}", "host": h.group(1) if h else ""})
    return ra


async def doc_appwidget(client, serial: str, package: str) -> list[dict]:
    out, _, _ = await client.shell(serial, "dumpsys", "appwidget")
    return parse_appwidget(out, package)


def parse_toast(out: str) -> list[str]:
    """Chu cua cac toast trong output `uiautomator events`."""
    ra = []
    for dong in (out or "").splitlines():
        if "TYPE_NOTIFICATION_STATE_CHANGED" not in dong or "Toast" not in dong:
            continue
        m = TOAST_TEXT_RE.search(dong)
        if m and m.group(1).strip() and m.group(1).strip() not in ra:
            ra.append(m.group(1).strip())
    return ra


async def nghe_toast(client, serial: str, giay: float) -> tuple[str, list[str]]:
    """Nghe accessibility event `giay` giay (lenh `timeout` cua may tu dung). -> (output tho, chu toast).

    KHONG chay song song voi `uiautomator dump`: hai lenh cung xin UiAutomation, lenh sau hong.
    """
    out, _, _ = await client.shell(serial, "timeout", f"{giay:g}", "uiautomator", "events",
                                   timeout=giay + 8)
    return out or "", parse_toast(out)


def nut_xac_nhan(xml: str, package: str):
    """Nut xac nhan cua dialog ghim widget -> (chu, node). Khong co -> (None, None). Mot chu khop NHIEU node
    -> ("", None): khong doan (bam nham "Add" cua mot dialog khac la hong luot)."""
    nodes = [n for n in ui_dump.parse_dump(xml) if n.visible and n.package != package]
    for chu in NUT_XAC_NHAN:
        khop = [n for n in nodes if (n.text or n.content_desc).strip().casefold() == chu]
        if len(khop) == 1:
            return chu, khop[0]
        if len(khop) > 1:
            return "", None
    return None, None


def vung_widget(xml: str, package: str) -> tuple[int, int, int, int] | None:
    """Khung cua widget app tren launcher: RemoteViews duoc ve trong tien trinh launcher (package cua node la
    launcher) nhung resource-id van mang prefix package app ("<pkg>:id/rootView"). Lay node lon nhat."""
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        return None
    best, dt = None, 0
    for el in root.iter("node"):
        if not el.get("resource-id", "").startswith(f"{package}:id/"):
            continue
        try:
            b = ui_dump.parse_bounds(el.get("bounds", ""))
        except ValueError:
            continue
        s = (b.right - b.left) * (b.bottom - b.top)
        if s > dt:
            best, dt = (b.left, b.top, b.right, b.bottom), s
    return best


DISPLAYED_RE = re.compile(r"Displayed\s+([\w.]+)/([\w.$]+)[^+\n]*\+?([\dms]*)")


def parse_displayed(log: str, package: str) -> list[dict]:
    """Dong "Displayed <pkg>/<activity>: +369ms" cua ActivityTaskManager -> [{activity, ms}] theo thu tu."""
    return [{"activity": m.group(2), "ms": m.group(3)} for m in DISPLAYED_RE.finditer(log or "")
            if m.group(1) == package]
