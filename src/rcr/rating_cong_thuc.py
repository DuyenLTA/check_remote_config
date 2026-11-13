"""Chay cong thuc lai app toi man result cua tab TC rating (`data/rating_gen.yaml`) - buoc "Gen anh / gen video".

Gen anh moi app mot kieu (chon style, chon anh, xem reward ad...) nen khong doan: cong thuc ghi tung buoc theo chu tren
man, them app moi la them muc vao file YAML. Dong quang cao dung lai `fo_flow.dong_ad_dang_che` cua rc-check (chi bam
dung nut dong, ad test khong co node nut thi BACK sau thoi gian toi thieu).
"""

from __future__ import annotations

import asyncio
import re
import time
from pathlib import Path

from . import device_app, fo_flow, ui_dump

DATA = Path(__file__).parent / "data" / "rating_gen.yaml"
TOI_DA_MAC_DINH = 30.0
NHIP = 1.0
DONG_TOI_DA = 4
LUONG_FO_RE = re.compile(r"Splash|AdActivity|Language|Onboarding|Question|Billing", re.I)
GOI_SUB = "weekly"      # goi test ngan nhat (chu ky test 5 phut)
# Trinh chon anh he thong: o anh co desc "Photo taken on ..." (photopicker Android 13+), nut xac nhan Done / Add.
ANH_RE = re.compile(r"^(?:Photo|Ảnh|Anh)\b.*(?:taken|chụp|chup)", re.I)
XAC_NHAN_ANH_RE = re.compile(r"^(?:Done|Add|Select|Xong|Thêm|Chọn)$", re.I)


def cong_thuc(package: str, loai: str) -> list[dict] | None:
    """Danh sach buoc cua app `package` cho `loai` ("anh" / "video"); chua co -> None."""
    import yaml
    data = yaml.safe_load(DATA.read_text(encoding="utf-8")) or {}
    return (data.get(package) or {}).get(loai)


def _khop(n, mau: str) -> bool:
    return any(re.search(mau, s or "", re.I) for s in (n.text, n.content_desc))


def tim(nodes, mau: str):
    return next((n for n in nodes if _khop(n, mau) and not n.bounds.empty), None)


def tim_duoi(nodes, mau: str, thu: int = 1):
    """Node bam duoc thu `thu` (dem tu trai) o hang dau tien nam duoi node co chu khop (the anh mau / the template
    khong co chu). The cuoi hang chi lo mot mep van tap duoc: tap vao giua phan dang hien."""
    moc = tim(nodes, mau)
    if moc is None:
        return None
    duoi = [n for n in nodes if n.clickable and not n.bounds.empty and n.bounds.top >= moc.bounds.bottom]
    if not duoi:
        return None
    hang = min(n.bounds.top for n in duoi)
    cung_hang = sorted((n for n in duoi if abs(n.bounds.top - hang) <= 8), key=lambda n: n.bounds.left)
    return cung_hang[thu - 1] if 0 < thu <= len(cung_hang) else None


async def _nodes(client, serial: str, package: str):
    return ui_dump.app_nodes(ui_dump.parse_dump(await ui_dump.dump(client, serial)), package)


async def _bam(client, serial: str, node) -> None:
    await device_app.tap(client, serial, *node.bounds.center)
    await asyncio.sleep(NHIP)


async def _chon_anh(client, serial: str, het: float, log: list[str]) -> bool:
    """Trinh chon anh he thong (photopicker / Google Photos): bam anh dau tien roi nut xac nhan neu co."""
    da_bam = False
    while time.monotonic() < het:
        nodes = ui_dump.parse_dump(await ui_dump.dump(client, serial))
        if not da_bam:
            anh = next((n for n in nodes if ANH_RE.search(n.content_desc or "") and not n.bounds.empty), None)
            if anh:
                await _bam(client, serial, anh)
                log.append("chọn ảnh đầu tiên")
                da_bam = True
                continue
        else:
            nut = next((n for n in nodes if XAC_NHAN_ANH_RE.match(n.text or "") and not n.bounds.empty), None)
            if nut:
                await _bam(client, serial, nut)
                log.append(f"bấm {nut.text}")
                return True
            pkg, _ = await device_app.focus(client, serial)
            if pkg and "photo" not in pkg and "media" not in pkg and "documentsui" not in pkg:
                return True                      # trinh chon dong ngay sau khi bam anh (chon 1 anh)
        await asyncio.sleep(NHIP)
    log.append("không chọn được ảnh trong trình chọn ảnh")
    return False


async def _mot_buoc(client, serial: str, package: str, buoc: dict, log: list[str]) -> bool:
    het = time.monotonic() + float(buoc.get("toi_da", TOI_DA_MAC_DINH))
    if "chon_anh" in buoc:
        return await _chon_anh(client, serial, het, log)
    if "cho_chu" in buoc:
        while time.monotonic() < het:
            if tim(await _nodes(client, serial, package), buoc["cho_chu"]):
                return True
            await asyncio.sleep(NHIP)
        log.append(f"không thấy chữ {buoc['cho_chu']!r}")
        return False
    if "dong_neu_co" in buoc:
        # Home co the chong nhieu popup (Add Widget, Check-in...): dong toi khi het, toi da DONG_TOI_DA lan.
        for _ in range(DONG_TOI_DA):
            node = tim(await _nodes(client, serial, package), buoc["dong_neu_co"])
            if not node:
                break
            await _bam(client, serial, node)
            log.append(f"đóng {node.text or node.content_desc}")
            await asyncio.sleep(NHIP)
        return True
    while time.monotonic() < het:
        _pkg, act = await device_app.focus(client, serial)
        if "ve_man" in buoc:
            # Case noi tiep co the dang o result / Feedback: BACK ve toi man goc (Home) truoc khi gen lai.
            if re.search(buoc["ve_man"], act or ""):
                return True
            if _pkg != package:
                await device_app.launch(client, serial, package)
                await device_app.wait_foreground(client, serial, package)
            elif LUONG_FO_RE.search(act or ""):
                # Vua mo lanh (sau mua sub / kill): dang o Splash / ad / LFO / OB -> lai qua FO bang trinh lai co san.
                walk = await fo_flow.walk_to(client, serial, package, buoc["ve_man"])
                log.append(f"lái FO tới {walk.get('activity', '').rsplit('.', 1)[-1]}")
            else:
                await client.shell(serial, "input", "keyevent", "KEYCODE_BACK")
                log.append(f"BACK từ {(act or '').rsplit('.', 1)[-1]}")
            await asyncio.sleep(1.5)
            continue
        if "cho_man" in buoc:
            if re.search(buoc["cho_man"], act or ""):
                log.append(f"tới {act.rsplit('.', 1)[-1]}")
                return True
        elif "xem_ads" in buoc:
            if re.search(buoc.get("toi", "$^"), act or ""):
                log.append(f"xem ads xong → {act.rsplit('.', 1)[-1]}")
                return True
            if "AdActivity" in (act or ""):
                log.append(await fo_flow.dong_ad_dang_che(client, serial, cho=45) or "chờ ad hết giờ")
                continue
            nodes = await _nodes(client, serial, package)
            chan = tim(nodes, buoc["dung_neu"]) if buoc.get("dung_neu") else None
            if chan:
                log.append(f"app báo '{chan.text or chan.content_desc}'")
                raise HetLuot(chan.text or chan.content_desc)
            node = tim(nodes, buoc["xem_ads"])
            if node:
                log.append(f"bấm {node.text}")
                await _bam(client, serial, node)
                await asyncio.sleep(3.0)      # cho ad mo len, tranh bam lai nut cu
                continue
        elif not ({"tap", "tap_duoi"} & set(buoc)):
            log.append(f"bước không hiểu trong data/rating_gen.yaml: {buoc}")
            return False
        else:
            nodes = await _nodes(client, serial, package)
            node = tim(nodes, buoc["tap"]) if "tap" in buoc else tim_duoi(nodes, buoc["tap_duoi"],
                                                                         int(buoc.get("thu", 1)))
            if node:
                log.append(f"bấm {node.text or node.content_desc or node.label}")
                await _bam(client, serial, node)
                return True
        await asyncio.sleep(NHIP)
    log.append(f"hết giờ ở bước {buoc}")
    return False


class HetLuot(Exception):
    """App bao het luot gen (vd "Daily Limit Reached")."""


async def _mua_sub(client, serial: str, package: str, log: list[str]) -> bool:
    """Het luot gen free -> mua sub test bang flow co san cua rc-check (`sub_thao_tac.mua`, user chot 12/11/2026:
    moi may la License Tester, mua khong hoi). Billing chi cap nhat khi kill app -> mo lanh lai sau khi mua."""
    from . import sub_thao_tac
    from .models import RcError
    await client.shell(serial, "input", "keyevent", "KEYCODE_BACK")      # dong dialog het luot
    await asyncio.sleep(NHIP)
    # `mo_paywall` di tu Home: dang o man chon anh -> BACK ve Home truoc (walk_to khong lui ve duoc).
    await _mot_buoc(client, serial, package, {"ve_man": "MainActivity", "toi_da": 20}, log)
    try:
        kq = await sub_thao_tac.mua(client, serial, package, GOI_SUB, "approves", True)
    except RcError as exc:
        log.append(f"mua sub lỗi: {exc}")
        return False
    log.append(f"mua sub {GOI_SUB}: popup {'test' if (kq.get('popup') or {}).get('la_test') else 'không thấy'}")
    await sub_thao_tac.mo_lanh(client, serial, package)
    return True


async def chay_ds(client, serial: str, package: str, ds: list[dict], log: list[str], bien: dict | None = None) -> bool:
    """Chay mot danh sach buoc cong thuc bat ky (dung chung cho tab daily checkin). `bien`: thay "{ten}" trong gia tri."""
    for b in ds:
        if bien:
            b = {k: (v.format(**bien) if isinstance(v, str) and "{" in v else v) for k, v in b.items()}
        if not await _mot_buoc(client, serial, package, b, log):
            return False
    return True


async def chay(client, serial: str, package: str, loai: str) -> dict:
    """{"co_cong_thuc", "xong", "log", "mua_sub"}: lai toi man result theo cong thuc; het luot gen thi mua sub
    roi chay lai cong thuc tu dau (mot lan)."""
    buoc = cong_thuc(package, loai)
    if not buoc:
        return {"co_cong_thuc": False, "xong": False, "log": []}
    log: list[str] = []
    da_mua = False
    while True:
        try:
            for b in buoc:
                if not await _mot_buoc(client, serial, package, b, log):
                    return {"co_cong_thuc": True, "xong": False, "log": log, "mua_sub": da_mua}
            return {"co_cong_thuc": True, "xong": True, "log": log, "mua_sub": da_mua}
        except HetLuot:
            if da_mua or not await _mua_sub(client, serial, package, log):
                return {"co_cong_thuc": True, "xong": False, "log": log, "mua_sub": da_mua}
            da_mua = True
