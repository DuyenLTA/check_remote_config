"""Theo doi man lien tuc: nhin lien tiep, ghi moc gio cua MAY moi khung.

Dung cho cac dong Expected phai NHIN THEO THOI GIAN ma truoc day day het cho
nguoi ("X hien tai ~t0+5s", "co so dem nguoc", "KHONG hien X"). Nguoi test
khong biet tool dang chay toi case nao de ma nhin kip - tool tu nhin.

Moc gio lay bang `date` tren MAY, cung dong ho voi `logcat -v epoch`: doi chieu
truc tiep voi luc ad show / luc roi trang trong log (ob3_log), khong lech gio
giua may tinh va dien thoai.

NHAN NUT X / SO DEM KHONG GAN CUNG THEO MOT APP (user chot 2026-10-07: tool
dung cho nhieu app). Mot node la "nut X" / "so dem" neu:
  - id nam trong goi y cua `data/ui_names.yaml` (them app moi thi sua file, khong
    sua code), HOAC
  - ten id mang nghia do (skip/close/dismiss/cancel - timeout/countdown/timer), HOAC
  - (chi cay uiautomator) content-desc kieu close/skip, hay chu chi la 1-2 chu so
    nam o vung tren man (so dem nguoc).
Node phai dang HIEN va NHO (nut, khong phai ca vung ad).

HAI NGUON KHUNG:
  - "nhanh": `dumpsys activity top` (~0,15s) - bat kip so dem / X song vai giay.
    Khong doc duoc chu, va khong phan biet trang ViewPager dang hien voi trang
    ben canh -> chi tin trong khoang app DANG o trang do (moc tu log).
  - "uia": `uiautomator dump` (~2,5s) chay song song - doc duoc chu so dem, chi
    thay trang dang hien -> dung de ket luan "man ke khong con X".
Truoc 2026-10-07 chi co uia: khung dau tien tre ~7s, ca cum OB3X ra FAIL oan.
"""

from __future__ import annotations

import asyncio
import re
import time

from . import device_app, fo_steps, ui_dump, ui_names, view_hierarchy_fast

# Vai tro (khong phai id): TapId mang vai tro nay thi tim theo luat chung ben duoi.
VAI_NUT_X = ("@nut_x",)
X_IDS = VAI_NUT_X                  # ten cu, giu cho noi goi cu

X_ID_RE = re.compile(r"skip|close|dismiss|cancel|exit", re.I)
DEM_ID_RE = re.compile(r"time_?out|count_?down|timer", re.I)
X_DESC_RE = re.compile(r"\b(close|skip|dismiss|đóng|bỏ qua)\b", re.I)
SO_DEM_RE = re.compile(r"^\s*\d{1,2}\s*$")
NUT_TOI_DA = 400                   # px: nut X / so dem; lon hon la vung ad, khong phai nut
VUNG_TREN = 0.35                   # so dem nguoc khong id: chi nhan o 35% tren cua man
# Moi lan uiautomator toi thieu cach nhau bay nhieu giay (no chiem CPU may).
GIUA_HAI_UIA = 1.0


def _goi_y(ten: str) -> set[str]:
    for e in ui_names.elements():
        if e.get("name") == ten:
            return set(e.get("ids") or ())
    return set()


def la_id_dem(rid: str) -> bool:
    return bool(rid) and (rid in _goi_y("số đếm ngược") or bool(DEM_ID_RE.search(rid)))


def la_id_x(rid: str) -> bool:
    return bool(rid) and not la_id_dem(rid) and (rid in _goi_y("nút X")
                                                  or bool(X_ID_RE.search(rid)))


def _id(node) -> str:
    return node.resource_id.rsplit("/", 1)[-1]


def _nho(w: int, h: int) -> bool:
    return 0 < w <= NUT_TOI_DA and 0 < h <= NUT_TOI_DA


def _hien_nho(n) -> bool:
    b = n.bounds
    return n.visible and not b.empty and _nho(b.right - b.left, b.bottom - b.top)


def tim_x(nodes) -> list:
    """Nut X tren cay uiautomator."""
    return [n for n in nodes if _hien_nho(n) and not SO_DEM_RE.match(n.text or "")
            and (la_id_x(_id(n)) or X_DESC_RE.search(n.content_desc or ""))]


def tim_dem(nodes) -> list:
    """So dem nguoc tren cay uiautomator."""
    cao = max((n.bounds.bottom for n in nodes), default=0)
    return [n for n in nodes if _hien_nho(n) and (
        la_id_dem(_id(n)) or (SO_DEM_RE.match(n.text or "") and n.bounds.top < cao * VUNG_TREN))]


def tim(nodes, ids) -> list:
    """Node dang hien theo id - hoac theo vai tro neu `ids` la VAI_NUT_X."""
    if tuple(ids) == VAI_NUT_X:
        return tim_x(nodes)
    return [n for n in nodes if n.visible and not n.bounds.empty and _id(n) in ids]


async def gio_may(client, serial: str) -> float:
    out, _, _ = await client.shell(serial, "date", "+%s.%N")
    try:
        return float(out.strip())
    except ValueError:
        return time.time()          # may khong in %N -> dong ho may tinh, lech it


async def mot_khung(client, serial: str, package: str) -> tuple[dict, list]:
    """Mot lan nhin bang uiautomator: (khung, nodes). Moc gio lay TRUOC dump."""
    t = await gio_may(client, serial)
    nodes = ui_dump.app_nodes(ui_dump.parse_dump(await ui_dump.dump(client, serial)), package)
    dem = tim_dem(nodes)
    khung = {"t": t, "x": bool(tim_x(nodes)),
             "dem": (dem[0].text or "hiện").strip() if dem else "",
             "trang": fo_steps.onboarding_page(nodes), "nguon": "uia"}
    return khung, nodes


async def khung_nhanh(client, serial: str, package: str, rong: int) -> tuple[dict, tuple | None]:
    """Mot lan nhin bang dumpsys: (khung, tam nut X tren man hoac None)."""
    t = await gio_may(client, serial)
    views = await view_hierarchy_fast.read(client, serial, package)
    xs = [v for v in views if v.visible and _nho(v.width, v.height) and la_id_x(v.rid)]
    dem = any(v.visible and _nho(v.width, v.height) and la_id_dem(v.rid) for v in views)
    tam = None
    if xs:
        v = xs[0]
        # Trang ViewPager nam canh nhau theo chieu ngang -> quy x ve mot be rong man.
        tam = (((v.left + v.right) // 2) % rong, (v.top + v.bottom) // 2)
    return {"t": t, "x": bool(xs), "dem": "hiện" if dem else "", "trang": 0, "nguon": "nhanh"}, tam


async def theo_doi(client, serial: str, package: str, giay: float, khung: list,
                   dung_khi=None) -> list | None:
    """Nhin lien tuc trong `giay` giay, them khung vao `khung`.

    Khung nhanh lien tuc; song song moi lan mot uiautomator (khung "uia").
    `dung_khi(nodes)` (nodes cua uiautomator) tra True thi dung som, tra `nodes`.
    """
    rong = (await device_app.screen_size(client, serial))[0]
    het = time.monotonic() + giay
    uia: asyncio.Task | None = None
    lan_uia = 0.0
    try:
        while time.monotonic() < het:
            if uia is None and time.monotonic() - lan_uia >= GIUA_HAI_UIA:
                uia, lan_uia = asyncio.create_task(mot_khung(client, serial, package)), time.monotonic()
            k, _ = await khung_nhanh(client, serial, package, rong)
            khung.append(k)
            if uia is not None and uia.done():
                ku, nodes = uia.result()
                uia = None
                khung.append(ku)
                if dung_khi and dung_khi(nodes):
                    return nodes
        if uia is not None:
            ku, nodes = await uia
            uia = None
            khung.append(ku)
            if dung_khi and dung_khi(nodes):
                return nodes
    finally:
        if uia is not None and not uia.done():
            uia.cancel()
        khung.sort(key=lambda k: k["t"])
    return None


async def cho_nut_x(client, serial: str, package: str, giay: float, khung: list) -> tuple | None:
    """Nhin nhanh toi khi nut X hien -> tam nut tren man (de tap ngay), hoac None."""
    rong = (await device_app.screen_size(client, serial))[0]
    het = time.monotonic() + giay
    while time.monotonic() < het:
        k, tam = await khung_nhanh(client, serial, package, rong)
        khung.append(k)
        if tam:
            return tam
    return None
