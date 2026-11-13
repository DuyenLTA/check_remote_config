"""Doc man SDK Daily Check-in (com.apero.checkin) tren may: man Check-in, man Unlocked, sheet unlock template; doi ngay.

Cay node (Compose, do AIP893 2.6.0 13/11/2026):
  - man Check-in : nut X (desc "Close"), title, banner, hang "Day 1".."Day 7", description, nut CTA ("Check-in").
  - man Unlocked : nut X (desc "Close"), title ("Unlocked Successfully!"), description - khong co hang Day.
  - popup Add Widget (SDK widget) cung co desc "Close" nhung co chu "Add Widget" -> khong nham voi hai man tren.
  - sheet unlock  : "Free Generate (N left)" (chi khi con luot), "Watch Ads (k/n)"; sheet tai xong moi hien nut.
Mau chu do bang `mau_chu.do` (dem pixel dung mau trong khung chu so voi dai doi chung) tren anh chup cung luc dump.
"""

from __future__ import annotations

import asyncio
import datetime
import re
import time

from . import mau_chu, ui_dump

DAY_RE = re.compile(r"^(?:Day|Ngày|Ngay)\s*\d+$", re.I)
WIDGET_RE = re.compile(r"\badd\s+widget\b", re.I)
FREE_RE = re.compile(r"^Free\s+Generate", re.I)
LEFT_RE = re.compile(r"\((\d+)\s+left\)", re.I)
HEX_RE = re.compile(r"#[0-9a-fA-F]{6}\b")
SU_KIEN_RE = re.compile(
    r"^\s*(\d{9,}\.\d+).*Logging event: origin=\w+,name=((?:daily_)?checkin\w*|daily_checkin\w*),params=Bundle\[\{(.*?)\}\]",
    re.M)
DAU_DOI_NGAY = "/data/local/tmp/rcr-doi-ngay"
TU_DONG_RE = re.compile(r"^(?:Automatic date and time|Set time automatically|Use network-provided time)$", re.I)


def _chu(nodes):
    return [n for n in nodes if (n.text or "").strip() and not n.bounds.empty]


def _hop(n) -> list[int]:
    b = n.bounds
    return [b.left, b.top, b.right, b.bottom]


def doc(nodes) -> dict:
    """{"widget", "checkin": {...}|None, "unlocked": {...}|None, "sheet": {...}|None} tu cay node app."""
    chu = _chu(nodes)
    widget = any(WIDGET_RE.search(n.text) for n in chu)
    dong = next((n for n in nodes if (n.content_desc or "") == "Close" and not n.bounds.empty), None)
    ra = {"widget": widget, "checkin": None, "unlocked": None, "sheet": None}
    if dong is not None and not widget:
        duoi = sorted((n for n in chu if n.bounds.top >= dong.bounds.top), key=lambda n: n.bounds.top)
        days = [n for n in duoi if DAY_RE.match(n.text.strip())]
        than = [n for n in duoi if not DAY_RE.match(n.text.strip())]
        if days and len(than) >= 2:
            cta, giua = than[-1], than[:-1]
            ra["checkin"] = {"title": giua[0].text, "banner": giua[1].text if len(giua) > 2 else "",
                             "description": giua[-1].text if len(giua) > 1 else "", "cta": cta.text, "x": True,
                             "khung": {"title": _hop(giua[0]), "banner": _hop(giua[1]) if len(giua) > 2 else None,
                                       "description": _hop(giua[-1]) if len(giua) > 1 else None, "cta": _hop(cta)}}
        elif not days and than and not any(FREE_RE.match(n.text) for n in chu):
            ra["unlocked"] = {"title": than[0].text, "description": than[-1].text if len(than) > 1 else "", "x": True,
                              "khung": {"title": _hop(than[0]),
                                        "description": _hop(than[-1]) if len(than) > 1 else None}}
    return ra


def sheet(nodes, xong_re: str) -> dict | None:
    """Sheet unlock template: None neu chua tai xong (chua co chu `xong_re`)."""
    chu = _chu(nodes)
    if not any(re.search(xong_re, n.text, re.I) for n in chu):
        return None
    free = next((n for n in chu if FREE_RE.match(n.text)), None)
    m = LEFT_RE.search(free.text) if free else None
    return {"free": free.text if free else None, "left": int(m.group(1)) if m else None,
            "enabled": bool(free and free.enabled), "khung": _hop(free) if free else None,
            "nut": [n.text for n in chu if n.clickable or re.search(xong_re, n.text, re.I) or FREE_RE.match(n.text)]}


def mau(nodes, png: bytes, cfg: dict) -> list[dict]:
    """So pixel dung tung mau #hex co trong config cua case, tai moi khung chu (mau_chu.do)."""
    hexes = sorted({h.upper() for v in (cfg or {}).values() for h in HEX_RE.findall(str(v))})
    return mau_chu.do(nodes, png, hexes) if hexes else []


def parse_su_kien(log: str) -> list[dict]:
    ra = []
    for t, ten, raw in SU_KIEN_RE.findall(log or ""):
        params = dict(kv.split("=", 1) for kv in (p.strip() for p in raw.split(",")) if "=" in kv)
        ra.append({"t": float(t), "ten": ten, "params": {k: v for k, v in params.items() if not k.startswith("ga_")}})
    return ra


async def su_kien(client, serial: str, moc: str = "") -> list[dict]:
    tu = ["-T", moc] if moc else []
    out, _, _ = await client.shell(serial, "logcat", "-d", "-v", "epoch", *tu, "-s", "FA-SVC:V")
    return parse_su_kien(out)


# ---- doi ngay may (Cai dat > Date & time): adb khong root khong dat gio duoc (`cmd alarm set-time` bi tu choi) ----

async def _nodes_all(client, serial):
    return ui_dump.parse_dump(await ui_dump.dump(client, serial))


async def _bam_chu(client, serial, mau_re, desc=False) -> bool:
    from . import device_app
    for n in await _nodes_all(client, serial):
        s = (n.content_desc if desc else n.text) or ""
        if re.search(mau_re, s, re.I) and not n.bounds.empty:
            await device_app.tap(client, serial, *n.bounds.center)
            await asyncio.sleep(1.0)
            return True
    return False


async def sang_ngay_mai(client, serial: str) -> dict:
    """Tat gio tu dong, dat lich sang ngay hom sau qua man Date & time. Ghi dau tren may de luot sau tra gio."""
    truoc, _, _ = await client.shell(serial, "date", "+%Y-%m-%d")
    await client.shell(serial, "touch", DAU_DOI_NGAY)
    await client.shell(serial, "am", "start", "-a", "android.settings.DATE_SETTINGS")
    await asyncio.sleep(2.0)
    tu_dong, _, _ = await client.shell(serial, "settings", "get", "global", "auto_time")
    if tu_dong.strip() == "1" and not await _bam_chu(client, serial, TU_DONG_RE.pattern):
        return {"ok": False, "loi": "không thấy công tắc giờ tự động"}
    if not await _bam_chu(client, serial, r"^Date$"):
        return {"ok": False, "loi": "không mở được lịch chọn ngày"}
    ngay = str((datetime.date.fromisoformat(truoc.strip()) + datetime.timedelta(days=1)).day)
    nodes = await _nodes_all(client, serial)
    if not any((n.text or "") == ngay and n.clickable for n in nodes):
        await _bam_chu(client, serial, r"^Next month$", desc=True)
    if not await _bam_chu(client, serial, rf"^{re.escape(ngay)}$") or not await _bam_chu(client, serial, r"^OK$"):
        return {"ok": False, "loi": f"không chọn được ngày {ngay}"}
    sau, _, _ = await client.shell(serial, "date", "+%Y-%m-%d")
    await client.shell(serial, "input", "keyevent", "KEYCODE_HOME")
    return {"ok": sau.strip() != truoc.strip(), "truoc": truoc.strip(), "sau": sau.strip()}


async def tra_gio(client, serial: str) -> dict | None:
    """May con dau doi ngay (case truoc doi ngay, ke ca luot chet giua chung) -> bat lai gio tu dong."""
    co, _, _ = await client.shell(serial, "ls", DAU_DOI_NGAY)
    if DAU_DOI_NGAY not in co:
        return None
    await client.shell(serial, "am", "start", "-a", "android.settings.DATE_SETTINGS")
    await asyncio.sleep(2.0)
    tu_dong, _, _ = await client.shell(serial, "settings", "get", "global", "auto_time")
    if tu_dong.strip() != "1":
        if not await _bam_chu(client, serial, TU_DONG_RE.pattern):
            await client.shell(serial, "settings", "put", "global", "auto_time", "1")
    het = time.monotonic() + 15
    tu_dong = ""
    while time.monotonic() < het:
        tu_dong, _, _ = await client.shell(serial, "settings", "get", "global", "auto_time")
        if tu_dong.strip() == "1":
            break
        await asyncio.sleep(1.0)
    await asyncio.sleep(3.0)              # cho may lay lai gio mang
    await client.shell(serial, "rm", "-f", DAU_DOI_NGAY)
    await client.shell(serial, "input", "keyevent", "KEYCODE_HOME")
    ngay, _, _ = await client.shell(serial, "date", "+%Y-%m-%d")
    return {"auto_time": tu_dong.strip(), "ngay": ngay.strip()}
