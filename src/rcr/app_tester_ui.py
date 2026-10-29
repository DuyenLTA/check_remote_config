"""Lai App Tester tren may that: tim app theo bundle_id, tim release theo version, tai + cai.

Luong do that (Pixel 6, 27/10/2026, AIP882 4.2.0 -> 4.3.0):
  Download (~2s/43MB) -> hop "Update this app?" cua packageinstaller -> Update ->
  Play Protect "App scan recommended" -> Scan app (~20s) -> "This app looks safe" -> Install.
User chot 27/10/2026: bot duoc bam "Scan app" (gui APK len Google quet) va tu tick
consent cua App Tester cho app chua test tren may.

Chi bam node da khop id/chu trong dump vua chup. Man la -> dung, luu dump + anh, bao.
"""

from __future__ import annotations

import asyncio
import re
import time
from datetime import datetime
from pathlib import Path

from . import app_tester_screens as s
from . import device_app, screencap, ui_dump
from .adb_parsers import AdbError, parse_debuggable

MAX_CUON_DS = 30          # danh sach ~50 app, moi lan cuon ~5 dong
MAX_CUON_BAN = 8          # build moi luon o dau danh sach release
TIMEOUT_CAI = 600.0
NHIP = 2.0
LAN_CHUP_LAI = 8
LAN_DOI_TRANG = 5         # doi trang chi tiet app load: toi da 5 nhip x NHIP
LAN_BACK_VE_DS = 2        # bam "All apps" khong ve duoc danh sach -> phim Back toi da 2 lan
VERSION_RE = re.compile(r"^(?P<name>\S+) \((?P<code>\d+)\)$")


class LoiCai(Exception):
    """Dung luot cai, kem ly do cho nguoi doc."""


async def _nodes(client, serial):
    # Vong xoay "Downloading…" chay lien tuc -> uiautomator bao "could not get idle
    # state" (do 27/10/2026, AIP882 4.3.0). Cho nhip roi chup lai, khong dung luot.
    for lan in range(LAN_CHUP_LAI):
        try:
            return ui_dump.parse_dump(await ui_dump.dump(client, serial))
        except AdbError as exc:
            if "idle state" not in str(exc) or lan == LAN_CHUP_LAI - 1:
                raise
            await asyncio.sleep(1.0)


async def _bam(client, serial, node, nghi: float = NHIP) -> None:
    x, y = node.bounds.center
    await device_app.tap(client, serial, x, y)
    await asyncio.sleep(nghi)


async def _cuon(client, serial, huong: str, lan: int = 1) -> None:
    for _ in range(lan):
        await device_app.swipe(client, serial, huong, ms=350)
    await asyncio.sleep(1.2)


async def _luu_man_la(client, serial, out_dir: Path, ly_do: str) -> LoiCai:
    out_dir.mkdir(parents=True, exist_ok=True)
    goc = out_dir / f"app-tester-loi-{time.strftime('%Y%m%d-%H%M%S')}"
    try:
        goc.with_suffix(".xml").write_text(await ui_dump.dump(client, serial), encoding="utf-8")
        goc.with_suffix(".png").write_bytes(await screencap.raw(client, serial))
    except AdbError:
        pass
    return LoiCai(f"{ly_do} (màn lưu ở {goc}.png)")


async def ban_dang_cai(client, serial, package) -> dict:
    """{version: "4.3.0 (40)", debuggable, cai_luc} hoac {} neu chua cai. `cai_luc` = lastUpdateTime
    (gio may) hoac None: dev day lai CUNG version thi chi moc cai moi phan biet ban cu / ban moi."""
    out, _, _ = await client.shell(serial, "dumpsys", "package", package)
    name = re.search(r"versionName=(\S+)", out)
    code = re.search(r"versionCode=(\d+)", out)
    if not (name and code):
        return {}
    luc = re.search(r"lastUpdateTime=(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d)", out)
    return {"version": f"{name.group(1)} ({code.group(1)})", "debuggable": parse_debuggable(out),
            "cai_luc": datetime.strptime(luc.group(1), "%Y-%m-%d %H:%M:%S") if luc else None}


async def mo_chi_tiet(client, serial, package, out_dir: Path):
    """Mo App Tester toi man chi tiet cua `package`. Tra node man chi tiet."""
    await device_app.launch(client, serial, s.APP_TESTER)
    await asyncio.sleep(3)
    nodes = await _nodes(client, serial)
    if s.man(nodes) in ("chi_tiet", "consent"):           # App Tester nho man cu
        await _bam(client, serial, s._co(nodes, "backToAppListButton"))
        nodes = await _nodes(client, serial)
        # Thong bao day (heads-up) cua app vua test che dung nut "All apps" o mep tren -> cu bam trung
        # thong bao (29/10/2026, Linguza "Your daily lesson awaits"). Phim Back khong bi che.
        for _ in range(LAN_BACK_VE_DS):
            if s.man(nodes) == "danh_sach":
                break
            await client.shell(serial, "input", "keyevent", "KEYCODE_BACK")
            await asyncio.sleep(NHIP)
            nodes = await _nodes(client, serial)
    if s.man(nodes) != "danh_sach":
        raise await _luu_man_la(client, serial, out_dir, "mở App Tester không ra danh sách app")
    # App dang hien san tren man -> bam luon. Chi khi chua thay moi len dau (keo lam moi) roi do tung
    # trang: truoc day luon vuot 8 lan du app nam ngay truoc mat (QA phan nan 28/10/2026).
    dong = s.dong_app(nodes, package)
    if dong is None:
        await _cuon(client, serial, "down", 8)
    for _ in range(MAX_CUON_DS):
        dong = dong or s.dong_app(await _nodes(client, serial), package)
        if dong:
            await _bam(client, serial, dong, 3)
            break
        await _cuon(client, serial, "up")
    else:
        raise LoiCai(f"App Tester không có app {package} (tài khoản tester chưa được mời?)")
    nodes = await _nodes(client, serial)
    if s.man(nodes) == "consent":
        await _bam(client, serial, s._co(nodes, "consent_checkbox"), 1)
        nut = s._co(await _nodes(client, serial), "consent_button")
        if nut is None or not nut.enabled:
            raise await _luu_man_la(client, serial, out_dir, "tick consent xong nút Start vẫn tắt")
        await _bam(client, serial, nut, 3)
        nodes = await _nodes(client, serial)
    # Trang chi tiet load cham hon nhip bam (AIP805 29/10/2026: dump luc bam chua co trang, anh chup
    # vai giay sau da du) -> doc lai vai nhip truoc khi ket luan. Mang chap chon thi App Tester hien
    # "Error fetching the app details" + nut Retry (do 29/10/2026) -> bam Retry roi doi tiep.
    for _ in range(LAN_DOI_TRANG):
        if s.man(nodes) == "chi_tiet" and s._co(nodes, "bundle_id", text=package) is not None:
            break
        thu_lai = s.nut_chu(nodes, "Retry", s.APP_TESTER)
        if thu_lai is not None:
            await _bam(client, serial, thu_lai, 3)
        else:
            await asyncio.sleep(NHIP)
        nodes = await _nodes(client, serial)
    if s.man(nodes) != "chi_tiet" or s._co(nodes, "bundle_id", text=package) is None:
        raise await _luu_man_la(client, serial, out_dir, f"không vào được trang của {package}")
    return nodes


async def doc_cac_ban(client, serial, nodes, version: str) -> list[dict]:
    """Cuon danh sach release, gom moi release (khong trung). Dung khi da qua het `version`."""
    gom: dict = {}
    for _ in range(MAX_CUON_BAN):
        moi = s.cac_ban(nodes)
        truoc = len(gom)
        for b in moi:
            gom.setdefault(s.khoa_ban(b), b)
        da_qua = any(b["version"] == version for b in gom.values()) and moi and moi[-1]["version"] != version
        # Cuon ma khong ra release moi = het danh sach -> dung, khong cuon tiep cho du MAX_CUON_BAN.
        het = truoc and len(gom) == truoc
        if da_qua or not moi or het:
            break
        await _cuon(client, serial, "up")
        nodes = await _nodes(client, serial)
    return list(gom.values())


async def kiem(client, serial, package, version, out_dir: Path) -> dict:
    """--chi-kiem: release nao cua `version` dang co. Khong tai, khong cai."""
    try:
        cac = await doc_cac_ban(client, serial, await mo_chi_tiet(client, serial, package, out_dir), version)
    finally:
        await client.shell(serial, "input", "keyevent", "KEYCODE_HOME")
    khop = [{"loai": b["loai"], "ngay": b["ngay"], "note": b["note"][:120]} for b in cac if b["version"] == version]
    return {"package": package, "version": version, "co_ban": bool(khop), "cac_ban": khop}


async def _toi_ban(client, serial, dich: dict):
    """Tim release `dich` (man hien tai truoc, khong thay moi cuon ve dau roi do xuong), mo rong no.
    Tra release (co node_nut) tren man hien tai."""
    ve_dau = False
    for _ in range(MAX_CUON_BAN + 1):
        b = next((x for x in s.cac_ban(await _nodes(client, serial)) if s.khoa_ban(x) == s.khoa_ban(dich)), None)
        if b and not b["mo_rong"]:
            await _bam(client, serial, b["node_mo"])
            continue
        if b and b["node_nut"] is not None:
            return b
        if not ve_dau:
            await _cuon(client, serial, "down", 4)
            ve_dau = True
        else:
            await _cuon(client, serial, "up")
    return None


async def cai(client, serial, package, version, loai, out_dir: Path) -> dict:
    """Cai dung release `version` + `loai`. Tra {package, version, debuggable, da_cai, go_ban_cu}."""
    m = VERSION_RE.match(version)
    if not m:
        raise LoiCai(f"version phải dạng '4.3.0 (40)': {version!r}")
    nodes = await mo_chi_tiet(client, serial, package, out_dir)
    dich, ly_do = s.chon_ban(await doc_cac_ban(client, serial, nodes, version), version, loai)
    if dich is None:
        raise LoiCai(ly_do)
    b = await _toi_ban(client, serial, dich)
    if b is None:
        raise await _luu_man_la(client, serial, out_dir, f"không mở được release {version} ({loai})")
    if b["loai"] not in (loai, s.CHUA_RO):   # note day du khac note rut gon
        raise LoiCai(f"release {version} mở ra là bản {b['loai']}, không phải {loai}")
    # Da cai hay chua: hoi dumpsys, khong suy tu nut (open_button "Install" = tai roi chua cai).
    truoc = await ban_dang_cai(client, serial, package)
    dung_loai = bool(truoc) and truoc["debuggable"] == (loai == "debug")
    # Cung version co the la lan day cu (dev day lai cung version): dumpsys khong phan biet duoc.
    # Nut Open cung KHONG tin duoc: AIP922 3.7.0 (30) day lai 29/10 14:35 ("thay ban 28/10") van hien
    # Open vi App Tester so versionCode, bot bo qua cai va verify tren ban 28/10. -> release day SAU luc
    # cai tren may thi la ban moi: go ban cu roi cai lai.
    cu_hon = bool(dung_loai and truoc.get("cai_luc") and s._luc_day(b) > truoc["cai_luc"])
    if dung_loai and truoc["version"] == version and b["nut"] not in ("tai", "da_tai") and not cu_hon:
        await client.shell(serial, "input", "keyevent", "KEYCODE_HOME")
        return {"package": package, "version": version, "debuggable": truoc["debuggable"],
                "da_cai": False, "go_ban_cu": False}
    go = bool(truoc) and (not dung_loai or (cu_hon and b["nut"] not in ("tai", "da_tai")))
    if b["nut"] == "ha_cap" and not go:
        raise LoiCai(f"máy đang cài {truoc.get('version')} mới hơn {version} — gỡ tay nếu muốn hạ cấp")
    if go:
        # debug <-> release khac chu ky -> Android tu choi cai de; go truoc (mat data app).
        await client.shell(serial, "pm", "uninstall", package)
        b = await _toi_ban(client, serial, dich)
    if b is None or b["nut"] not in ("tai", "da_tai"):
        raise await _luu_man_la(client, serial, out_dir, f"release {version} không có nút Download/Install")
    await _bam(client, serial, b["node_nut"])
    return await _cho_cai_xong(client, serial, package, version, loai, go, out_dir)


async def _cho_cai_xong(client, serial, package, version, loai, go, out_dir) -> dict:
    het = time.monotonic() + TIMEOUT_CAI
    la = 0
    while time.monotonic() < het:
        hien = await ban_dang_cai(client, serial, package)
        if hien.get("version") == version and hien["debuggable"] == (loai == "debug"):
            await client.shell(serial, "input", "keyevent", "KEYCODE_HOME")
            return {"package": package, "version": version, "debuggable": hien["debuggable"],
                    "da_cai": True, "go_ban_cu": go}
        if hien.get("version") == version:
            # Ban cu cung version sai loai da bi go truoc khi bam cai (`go`) -> day chinh la ban vua cai.
            # Note khong ghi loai ma co debuggable noi khac -> bao ngay, khong cho het TIMEOUT_CAI.
            thuc = "debug" if hien["debuggable"] else "release"
            await client.shell(serial, "input", "keyevent", "KEYCODE_HOME")
            raise LoiCai(f"{version} cài xong kiểm cờ debuggable bằng adb: là bản {thuc}, không phải {loai} "
                         f"(release note không ghi loại)")
        nodes = await _nodes(client, serial)
        man = s.man(nodes)
        nut = {"hop_cai": s._co(nodes, "button1", package=s.INSTALLER),
               "pp_quet": s.nut_chu(nodes, "Scan app", s.PLAY_STORE),
               "pp_an_toan": s.nut_chu(nodes, "Install", s.PLAY_STORE)}.get(man)
        la = la + 1 if man in ("khac", "danh_sach", "consent") else 0
        if nut is not None:
            await _bam(client, serial, nut)
        elif la >= 5:                     # hop cai "Installing…" thoang qua thi khong tinh
            raise await _luu_man_la(client, serial, out_dir, "màn lạ khi đang cài")
        else:
            await asyncio.sleep(NHIP)
    raise await _luu_man_la(client, serial, out_dir, f"quá {TIMEOUT_CAI:.0f}s chưa cài xong {version}")
