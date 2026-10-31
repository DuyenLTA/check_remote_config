"""Buoc "Xem logcat tag VslTemplate4FirstOpenSDK va FOR_TESTER_CONFIG": bat tester mode (neu can) roi doc dung tag.

Truoc day buoc nay la "quan sat" va dong "Version Lib Ads = 1.2.10" ra NOT_VERIFIABLE - Claude phai do tay moi
luot (AIP886 / AIP936 R01-01). Tag FOR_TESTER_CONFIG chi in khi bat tester mode: cap quyen thong bao (hop xin
quyen che icon thi bam khong an) -> mo app -> ~1,5s sau bam icon splash 25 lan -> toast "Change to tester ad mode"
(user chot 29/10/2026, tab "cac tag check" cua sheet TC).
"""

from __future__ import annotations

import asyncio
import re

from . import device_app, ui_names

TESTER_TAG = "FOR_TESTER_CONFIG"
TAG_RE = re.compile(r"\b([A-Za-z][A-Za-z0-9_]{5,})\b")
XEM_TAG_RE = re.compile(r"^\s*(?:xem|check|ki[ểe]m\s*tra)\s+(?:log\s*cat|logcat)\s+tag\s+(.+)$", re.I)
CHO_LOG = 10.0            # FOR_TESTER_CONFIG in sau khi app vao luong (~10s do that)
_DONG_RE = re.compile(r"^\s*[\d.]+\s+(\d+)\s+\d+\s+[VDIWEF]\s+([^:]+?)\s*:\s?(.*)$")


def tags_cua(step: str) -> list[str]:
    """"Xem logcat tag A va B." -> ["A", "B"]; khong phai cau xem tag -> []."""
    m = XEM_TAG_RE.match(step or "")
    if not m:
        return []
    bo = {"va", "và", "and", "tag", "logcat"}
    return [t for t in TAG_RE.findall(m.group(1)) if t.casefold() not in bo]


def _tester_cfg() -> dict:
    import yaml

    return (yaml.safe_load(ui_names.DATA.read_text(encoding="utf-8")) or {}).get("tester_mode") or {}


async def bat_tester(client, serial: str, package: str) -> str:
    """Mo lai app, bam icon splash N lan. -> mo ta da lam / ly do khong lam duoc."""
    cfg = _tester_cfg()
    ids, lan = tuple(cfg.get("ids") or ()), int(cfg.get("so_lan") or 25)
    # Icon chi HIEN o UI mac dinh cua lan mo dau sau `pm clear` (~1,5-4s, truoc khi ap splash_ui_config); lan mo
    # lai config co san trong cache, icon o trang thai GONE (do that AIP886 31/10/2026). Precondition TC cung ghi
    # "1. Clear data. 2. Spam icon app o Splash". Ban release: RC cua case van dang publish o testvsl -> fetch lai dung.
    await client.shell(serial, "am", "force-stop", package)
    await client.shell(serial, "pm", "clear", package)
    await client.shell(serial, "pm", "grant", package, "android.permission.POST_NOTIFICATIONS")
    await device_app.launch(client, serial, package)
    # Doc nhanh (dumpsys activity top ~0,1-0,6s) lien tuc tu luc mo: uiautomator dump ~2,5s, cho xong thi splash
    # da sang inter (AIP886 31/10/2026: cho 1,5s + dump -> khong con icon).
    tam = await _cho_icon(client, serial, package, ids)
    if not tam:
        return f"không thấy đúng một icon splash ({'/'.join(ids)}) để bật tester mode"
    x, y = tam
    # Mot dong shell tren may (bam lien ~1,2s cho 25 lan); x, y, lan deu la so nguyen.
    await client.shell_line(serial, f"for i in $(seq 1 {int(lan)}); do input tap {int(x)} {int(y)}; done")
    return f"bật tester mode: bấm icon splash {lan} lần"


CHO_ICON_TOI_DA = 8.0
LAN_BAT_TESTER = 3
NHIP_ICON = 0.2


async def _cho_icon(client, serial: str, package: str, ids: tuple[str, ...]) -> tuple[int, int] | None:
    """Tam icon splash ngay khi no hien (dung mot node mang id trong `ids`), None neu het gio.

    Doc bang uiautomator (accessibility), KHONG bang `dumpsys activity top`: lan mo dau sau pm clear luong chinh
    cua app ban khoi tao, `dumpsys activity top` treo ~65s (do that AIP886 31/10/2026). Dump ngay sau khi mo,
    khong cho truoc - icon chi hien ~1,5-4s."""
    from . import ui_dump

    het = asyncio.get_running_loop().time() + CHO_ICON_TOI_DA
    while asyncio.get_running_loop().time() < het:
        try:
            nodes = ui_dump.app_nodes(ui_dump.parse_dump(await ui_dump.dump(client, serial)), package)
        except Exception:  # noqa: BLE001 - dump hong mot nhip thi dump lai
            nodes = []
        icon = [n for n in nodes if n.resource_id in ids and n.visible and not n.bounds.empty]
        if len(icon) == 1:
            return icon[0].bounds.center
        await asyncio.sleep(NHIP_ICON)
    return None


async def doc(client, serial: str, package: str, tags: list[str]) -> dict[str, list[str]]:
    """{tag: [noi dung dong]} cua PID app trong buffer logcat hien tai."""
    out, _, _ = await client.shell(serial, "logcat", "-d", "-v", "epoch", *[f"{t}:*" for t in tags], "*:S")
    pid_app, _, _ = await client.shell(serial, "pidof", package)
    pids = set(pid_app.split())
    ra: dict[str, list[str]] = {t: [] for t in tags}
    for dong in out.splitlines():
        m = _DONG_RE.match(dong)
        if not m or (pids and m.group(1) not in pids):
            continue
        tag = m.group(2).strip()
        if tag in ra and m.group(3).strip() not in ra[tag]:
            ra[tag].append(m.group(3).strip())
    return ra


async def xem(client, serial: str, package: str, tags: list[str]) -> dict:
    """Lam ca buoc: bat tester mode khi co tag FOR_TESTER_CONFIG, cho log, doc tag."""
    lam = ""
    if TESTER_TAG in tags:
        # Icon chi hien vai giay luc mo dau: dump dau tien co the roi vao luc app chua ve xong, lan sau icon da an
        # (AIP886 R01-01: lan 1 hut, lan 2 trung) -> lam lai ca chu trinh clear -> mo -> do mot lan nua.
        for _ in range(LAN_BAT_TESTER):
            lam = await bat_tester(client, serial, package)
            if lam.startswith("bật"):
                break
        await asyncio.sleep(CHO_LOG)
    return {"tags": await doc(client, serial, package, tags), "lam": lam}
