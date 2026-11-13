"""Buoc Action cua tab TC "daily checkin" (SDK com.apero.checkin): dong Add Widget roi doi man Check-in, bam Check-in,
dong Unlocked, vao sheet unlock template, gen free, ve Home / kill mo lai, doi ngay may.

AIP893 2.6.0 daily checkin 12-13/11/2026: tool tra NEEDS_HUMAN o moi buoc nay (hoac te hon: "Mo app vao Home, bam
Check-in, dong Unlocked" bi dich thanh CHI lai vao Home, ve sau bo im), Claude do tay. Cach do tay da duoc user chap
nhan nen dong goi o day; bang chung ghi vao `record["checkin"]` cho `assert_checkin` cham:
  - moi lan nhin man: chu title/banner/description/CTA + so pixel tung mau #hex cua config (do mau chu), nut X.
  - sheet unlock: co / khong "Free Generate (N left)", enabled, chi ket luan khi sheet da tai xong.
  - gen free: bam Free Generate, cho ve Home, mo History xem co ban vua tao.
Duong vao sheet unlock + History moi app mot kieu: `data/checkin_cong_thuc.yaml` (chua co -> dung case, khong doan).

Cau chung ("Kill app, mo lai, vao Home", "Quay ve Home", "Bam X") chi doi cach lam khi case dat key checkin (CFG):
o tab khac chung giu nguyen thao tac cu.
"""

from __future__ import annotations

import asyncio
import contextvars
import re
import time
from dataclasses import dataclass
from pathlib import Path

from . import checkin_may, device_app, fo_flow, log_moc, rating_cong_thuc, ui_dump
from .adb_parsers import AdbError

DATA = Path(__file__).parent / "data" / "checkin_cong_thuc.yaml"
# Config RC cua case dang chay (case_run dat): co key checkin -> dang o tab daily checkin.
CFG: contextvars.ContextVar[dict | None] = contextvars.ContextVar("checkin_cfg", default=None)
KEY_RE = re.compile(r"^(?:show_checkin|checkin_)", re.I)

DONG_WIDGET_RE = re.compile(r"^\s*đ[óo]ng\s+(?:m[àa]n|popup)\s+add\s*widget", re.I)
CHO_CHECKIN_RE = re.compile(r"^\s*m[ởo]\s+app\s+v[àa]o\s+home\s*,\s*ch[ờo]\s+(?:m[àa]n\s+)?daily\s*check", re.I)
FULL_RE = re.compile(r"^\s*m[ởo]\s+app\s+v[àa]o\s+home\s*,\s*b[ấa]m\s+check-?in\s*,\s*đ[óo]ng\s+unlocked", re.I)
CHECKIN_RE = re.compile(r"^\s*b[ấa]m\s+(?:button\s+|n[úu]t\s+)?check-?in\s*\.?\s*$", re.I)
DONG_UNLOCKED_RE = re.compile(r"^\s*(?:b[ấa]m\s+x\s+tr[êe]n\s+m[àa]n\s+unlocked|đ[óo]ng\s+(?:m[àa]n\s+)?unlocked)", re.I)
X_RE = re.compile(r"^\s*b[ấa]m\s+x\s*\.?\s*$", re.I)
UNLOCK_RE = re.compile(r"(?:ch[ọo]n\s+1\s+template\s*,\s*)?v[àa]o\s+m[àa]n\s+unlock\s+template(?:\s+c[ủu]a\s+template\s+"
                       r"(?P<t>[A-Z]))?", re.I)
QUAY_UNLOCK_RE = re.compile(r"^\s*quay\s+l[ạa]i\s+m[àa]n\s+unlock\s+template", re.I)
GEN_FREE_RE = re.compile(r"^\s*b[ấa]m\s+free\s+generate", re.I)
GEN_TPL_RE = re.compile(r"^\s*gen\s+free\s+v[ớo]i\s+template\s+(?P<t>[A-Z])\b", re.I)
VE_HOME_RE = re.compile(r"^\s*quay\s+v[ềe]\s+home\s*\.?\s*$", re.I)
KILL_RE = re.compile(r"^\s*(?:quay\s+v[ềe]\s+home\s*,\s*)?kill\s+app\s*,\s*m[ởo]\s+l[ạa]i\s*,?\s*(?:v[àa]o\s+home)?", re.I)
DOI_NGAY_RE = re.compile(r"ch[ỉi]nh\s+gi[ờo]\s+(?:thi[ếe]t\s+b[ịi]|m[áa]y)\s+sang\s+ng[àa]y\s+h[ôo]m\s+sau", re.I)

CHO_POPUP = 20.0          # Add Widget hien ~8s sau khi vao Home (do AIP893)
CHO_CHECKIN = 8.0         # man Check-in hien ngay sau khi dong Add Widget
CHO_SHEET = 30.0
CHO_GEN = 180.0
NHIP = 0.5
CHO_DUNG_YEN = 4.0        # toi da doi sheet truot xong (nut X dung yen)


@dataclass(frozen=True, slots=True)
class Checkin:
    viec: str
    reason: str
    thu: int = 0

    @property
    def summary(self) -> dict:
        return {"kind": f"checkin_{self.viec}", "reason": self.reason}


def dang_checkin() -> bool:
    return any(KEY_RE.match(k) for k in (CFG.get() or {}))


def _thu(chu: str | None) -> int:
    return ord(chu.upper()) - ord("A") + 1 if chu else 0


def resolve(text: str, nodes):
    """Cau buoc cua tab daily checkin -> thao tac; cau khac -> None."""
    if CHO_CHECKIN_RE.match(text):
        return Checkin("vao_home", "lái tới Home, đóng Add Widget, chờ màn Daily Check-in")
    if FULL_RE.match(text):
        return Checkin("full", "lái tới Home, đóng Add Widget, bấm Check-in, đóng Unlocked")
    if CHECKIN_RE.match(text):
        return Checkin("checkin", "bấm CTA của màn Daily Check-in, nhìn màn Unlocked")
    if DONG_UNLOCKED_RE.match(text):
        return Checkin("dong_unlocked", "bấm X của màn Unlocked")
    m = GEN_TPL_RE.match(text)
    if m:
        return Checkin("gen_tpl", f"vào sheet unlock của template {m.group('t')}, gen free, chờ xong",
                       thu=_thu(m.group("t")))
    if QUAY_UNLOCK_RE.match(text):
        return Checkin("vao_unlock", "vào lại sheet unlock của template trước")
    m = UNLOCK_RE.search(text)
    if m and not re.search(r"\bgen\b", text, re.I):
        return Checkin("vao_unlock", "vào sheet unlock template theo công thức của app", thu=_thu(m.group("t")))
    if GEN_FREE_RE.match(text):
        return Checkin("gen_free", "bấm Free Generate, chờ gen xong, xem History")
    if DOI_NGAY_RE.search(text):
        return Checkin("doi_ngay", "tắt giờ tự động, đặt ngày máy sang hôm sau (Cài đặt > Date & time)")
    if not dang_checkin():
        return None
    if DONG_WIDGET_RE.match(text):
        return Checkin("quan_sat", "đóng popup Add Widget, nhìn màn Daily Check-in hiện sau đó")
    if KILL_RE.match(text):
        return Checkin("kill", "kill app, mở lại vào Home, đóng Add Widget, nhìn có màn Check-in không"
                       + (" (nhìn cả lúc về Home)" if text.lower().lstrip().startswith("quay") else ""))
    if VE_HOME_RE.match(text):
        return Checkin("ve_home", "BACK về Home, nhìn có màn Check-in không")
    if X_RE.match(text) and checkin_may.doc(nodes)["checkin"]:
        return Checkin("x", "bấm X của màn Daily Check-in")
    return None


def cong_thuc(package: str) -> dict | None:
    import yaml
    return (yaml.safe_load(DATA.read_text(encoding="utf-8")) or {}).get(package)


async def lam(client, serial: str, action: Checkin, record: dict, ctx: dict) -> None:
    package = ctx["package"]
    moc = await log_moc.bay_gio(client, serial)
    try:
        ket = await _lam(client, serial, package, action, ctx)
    except (AdbError, OSError, ValueError, TypeError, KeyError, IndexError) as exc:
        ket = {"dung": f"lỗi khi làm bước daily checkin {action.viec}: {type(exc).__name__}: {exc}"}
    record["checkin"] = {"viec": action.viec, **ket, "su_kien": await checkin_may.su_kien(client, serial, moc)}
    if ket.get("dung"):
        record["dung_lai"] = ket["dung"]


async def _lam(client, serial, package, action: Checkin, ctx) -> dict:
    ct = cong_thuc(package) or {}
    v = action.viec
    if v == "quan_sat":
        return await _quan_sat(client, serial, package)
    if v == "vao_home":
        await _ve_home_fo(client, serial, package)
        return await _quan_sat(client, serial, package)
    if v == "full":
        await _ve_home_fo(client, serial, package)
        ket = await _quan_sat(client, serial, package)
        if not ket.get("checkin"):
            return ket | {"dung": "không thấy màn Daily Check-in để bấm Check-in"}
        ket |= await _checkin(client, serial, package)
        return ket | {"sau_dong": await _dong_unlocked(client, serial, package)}
    if v == "checkin":
        return await _checkin(client, serial, package)
    if v == "dong_unlocked":
        return await _dong_unlocked(client, serial, package)
    if v == "x":
        return await _x(client, serial, package)
    if v in ("vao_unlock", "gen_tpl", "gen_free") and not ct.get("vao_unlock"):
        return {"dung": "app chưa có công thức vào sheet unlock template trong data/checkin_cong_thuc.yaml"}
    if v == "vao_unlock":
        thu = action.thu or ctx.get("checkin_thu") or 1
        ctx["checkin_thu"] = thu
        return await _vao_unlock(client, serial, package, ct, thu)
    if v == "gen_free":
        return await _gen(client, serial, package, ct)
    if v == "gen_tpl":
        ctx["checkin_thu"] = action.thu
        ket = await _vao_unlock(client, serial, package, ct, action.thu)
        if ket.get("dung") or not (ket.get("sheet") or {}).get("free"):
            return ket
        return ket | await _gen(client, serial, package, ct)
    if v == "ve_home":
        return {"lan": [await _ve_home_back(client, serial, package, ct)]}
    if v == "kill":
        lan = [await _ve_home_back(client, serial, package, ct)] if "nhìn cả lúc về Home" in action.reason else []
        await client.shell(serial, "am", "force-stop", package)
        await asyncio.sleep(1.0)
        await _ve_home_fo(client, serial, package)
        return {"lan": lan + [await _quan_sat(client, serial, package)]}
    if v == "doi_ngay":
        ket = await checkin_may.sang_ngay_mai(client, serial)
        return ket if ket.get("ok") else ket | {"dung": f"không đổi được ngày máy: {ket.get('loi') or ket}"}
    return {}


# ---- nhin man ----

async def _nhin(client, serial: str, package: str) -> dict:
    xml = await ui_dump.dump(client, serial)
    png, _, _ = await client.run_binary("-s", serial, "exec-out", "screencap -p")
    nodes = ui_dump.app_nodes(ui_dump.parse_dump(xml), package)
    man = checkin_may.doc(nodes)
    _, act = await device_app.focus(client, serial)
    man["man"] = (act or "").rsplit(".", 1)[-1]
    if man["checkin"] or man["unlocked"]:
        man["mau"] = checkin_may.mau(nodes, png, CFG.get() or {})
    man["_nodes"] = nodes
    return man


def _bo_nodes(man: dict) -> dict:
    return {k: v for k, v in man.items() if k != "_nodes"}


def _vi_tri_x(man: dict):
    x = next((n for n in man.get("_nodes") or [] if (n.content_desc or "") == "Close" and not n.bounds.empty), None)
    return None if x is None else (x.bounds.left, x.bounds.top)


async def _cho(client, serial, package, dk, giay: float) -> dict:
    """Doi toi khi `dk` dung, roi doi sheet dung yen (nut X 2 lan nhin cung cho): sheet Check-in / Unlocked truot tu
    duoi len, chup giua chung thi chu bi cat o mep man, dem mau sai (Pixel 4 13/11/2026: Unlocked FAIL gia)."""
    het = time.monotonic() + giay
    man = await _nhin(client, serial, package)
    while not dk(man) and time.monotonic() < het:
        await asyncio.sleep(NHIP)
        man = await _nhin(client, serial, package)
    het_dung = time.monotonic() + CHO_DUNG_YEN
    while dk(man) and _vi_tri_x(man) is not None and time.monotonic() < het_dung:
        await asyncio.sleep(NHIP)
        sau = await _nhin(client, serial, package)
        if not dk(sau):
            break
        on_dinh = _vi_tri_x(sau) == _vi_tri_x(man)
        man = sau
        if on_dinh:
            break
    return man


async def _bam_close(client, serial, nodes) -> bool:
    x = next((n for n in nodes if (n.content_desc or "") == "Close" and not n.bounds.empty), None)
    if x is None:
        return False
    await device_app.tap(client, serial, *x.bounds.center)
    await asyncio.sleep(1.0)
    return True


async def _quan_sat(client, serial: str, package: str) -> dict:
    """Doi popup Add Widget (hoac man Check-in neu app khong co widget), dong widget, doi man Check-in."""
    man = await _cho(client, serial, package, lambda m: m["widget"] or m["checkin"], CHO_POPUP)
    widget = man["widget"]
    if widget:
        await _bam_close(client, serial, man["_nodes"])
        man = await _cho(client, serial, package, lambda m: m["checkin"], CHO_CHECKIN)
    return {"widget": widget, "checkin": man["checkin"], "mau": man.get("mau") or [], "man": man["man"]}


async def _ve_home_fo(client, serial, package) -> None:
    """"Mo app vao Home": app khong o foreground (vua doi ngay, vua kill) -> mo lanh nhu bam icon, roi lai qua FO."""
    pkg, act = await device_app.focus(client, serial)
    if pkg != package:
        await client.shell(serial, "am", "force-stop", package)
        await device_app.launch(client, serial, package)
        await device_app.wait_foreground(client, serial, package)
    await fo_flow.walk_to(client, serial, package, "MainActivity")


async def _checkin(client, serial, package) -> dict:
    man = await _cho(client, serial, package, lambda m: m["checkin"], CHO_CHECKIN)
    if not man["checkin"]:
        return {"dung": "không thấy màn Daily Check-in để bấm Check-in"}
    cta = next(n for n in man["_nodes"] if (n.text or "") == man["checkin"]["cta"])
    await device_app.tap(client, serial, *cta.bounds.center)
    man = await _cho(client, serial, package, lambda m: m["unlocked"], CHO_CHECKIN)
    return {"bam_checkin": True, "unlocked": man["unlocked"], "mau_unlocked": man.get("mau") or [], "man": man["man"]}


async def _dong_unlocked(client, serial, package) -> dict:
    man = await _cho(client, serial, package, lambda m: m["unlocked"], CHO_CHECKIN)
    if not man["unlocked"]:
        return {"dung": "không thấy màn Unlocked để bấm X"}
    await _bam_close(client, serial, man["_nodes"])
    sau = await _nhin(client, serial, package)
    return {"bam_x": True, "man": sau["man"], "con_popup": bool(sau["unlocked"] or sau["checkin"])}


async def _x(client, serial, package) -> dict:
    man = await _nhin(client, serial, package)
    if not man["checkin"] or not await _bam_close(client, serial, man["_nodes"]):
        return {"dung": "không thấy nút X của màn Daily Check-in"}
    sau = await _nhin(client, serial, package)
    return {"bam_x": True, "man": sau["man"], "con_popup": bool(sau["unlocked"] or sau["checkin"])}


async def _vao_unlock(client, serial, package, ct, thu: int) -> dict:
    log: list[str] = []
    if not await rating_cong_thuc.chay_ds(client, serial, package, ct["vao_unlock"], log, {"thu": thu}):
        return {"thu": thu, "log": log, "dung": f"không vào được sheet unlock template: {'; '.join(log[-2:])}"}
    het = time.monotonic() + CHO_SHEET
    sh = None
    while time.monotonic() < het:
        nodes = ui_dump.app_nodes(ui_dump.parse_dump(await ui_dump.dump(client, serial)), package)
        sh = checkin_may.sheet(nodes, ct.get("sheet_xong") or "^Watch Ads")
        if sh:
            break
        await asyncio.sleep(NHIP)
    if not sh:
        return {"thu": thu, "log": log, "dung": "sheet unlock template không tải xong"}
    return {"thu": thu, "log": log, "sheet": sh}


async def _gen(client, serial, package, ct) -> dict:
    nodes = ui_dump.app_nodes(ui_dump.parse_dump(await ui_dump.dump(client, serial)), package)
    free = next((n for n in nodes if checkin_may.FREE_RE.match(n.text or "") and not n.bounds.empty), None)
    if free is None:
        return {"gen": {"bam": False}, "dung": "không có nút Free Generate để bấm"}
    await device_app.tap(client, serial, *free.bounds.center)
    het, ve = time.monotonic() + CHO_GEN, False
    while time.monotonic() < het:
        await asyncio.sleep(3.0)
        nodes = ui_dump.app_nodes(ui_dump.parse_dump(await ui_dump.dump(client, serial)), package)
        if rating_cong_thuc.tim(nodes, ct.get("home_chu") or "$^"):
            ve = True
            break
    gen = {"bam": True, "ve_home": ve, "moi_nhat": ""}
    log: list[str] = []
    if ve and ct.get("lich_su") and await rating_cong_thuc.chay_ds(client, serial, package, ct["lich_su"], log):
        nodes = ui_dump.app_nodes(ui_dump.parse_dump(await ui_dump.dump(client, serial)), package)
        moi = rating_cong_thuc.tim(nodes, ct.get("moi_tao") or "$^")
        gen["moi_nhat"] = moi.text if moi else ""
        await client.shell(serial, "input", "keyevent", "KEYCODE_BACK")
        await asyncio.sleep(1.0)
    gen["xong"] = bool(gen["moi_nhat"])
    gen["log"] = log
    return {"gen": gen}


async def _ve_home_back(client, serial, package, ct) -> dict:
    for _ in range(4):
        nodes = ui_dump.app_nodes(ui_dump.parse_dump(await ui_dump.dump(client, serial)), package)
        if rating_cong_thuc.tim(nodes, ct.get("home_chu") or "$^") and not any(
                (n.content_desc or "") == "Close sheet" for n in nodes):
            break
        await client.shell(serial, "input", "keyevent", "KEYCODE_BACK")
        await asyncio.sleep(1.2)
    man = await _cho(client, serial, package, lambda m: m["checkin"], CHO_CHECKIN)
    return {"widget": man["widget"], "checkin": man["checkin"], "man": man["man"]}
