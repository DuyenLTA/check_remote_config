"""Do mau chu tren anh chup GOC (PNG), luc vua dump - report chi giu anh thu nho JPEG.

Chu nam tren anh nen (splash la anh chup that) nen khong lay "mau nhieu nhat" trong
khung chu duoc: nen chiem phan lon. Dem so pixel GAN mau dich trong khung chu, roi dem
o mot dai DOI CHUNG cung kich thuoc sat tren/duoi khung (cung nen, khong co chu). Chu
dung mau thi trong khung nhieu hon han dai doi chung; nen tinh co trung mau thi hai ben
ngang nhau. Cung y voi rc-check.md 5b: "mau chu = pixel khong doi giua hai nen".
"""

from __future__ import annotations

import io
import re

HEX_RE = re.compile(r"#([0-9a-f]{6})\b", re.I)
# Lech toi da moi kenh RGB coi la "dung mau". Vien chu bi khu rang cua nhung LOI net chu
# trung mau tuyet doi; nen anh chuyen mau thi hiem khi trung. Do 24/10/2026 tren Piclux
# 2.4.0: subtitle #E0E0E0 tren nen sang - lech <=4: 13.754 px trong khung, 0 o doi chung;
# lech <=28 (Euclid): 58.398 vs 76.232, nen nuot mat chu.
GAN = 4


def _rgb(hex_: str) -> tuple[int, int, int]:
    h = hex_.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _dem(img, box, dich) -> int:
    if box[3] <= box[1] or box[2] <= box[0]:
        return 0
    r0, g0, b0 = dich
    vung = img.crop(box)
    diem = getattr(vung, "get_flattened_data", vung.getdata)()
    return sum(1 for r, g, b in diem
               if abs(r - r0) <= GAN and abs(g - g0) <= GAN and abs(b - b0) <= GAN)


def _dai_doi_chung(b, cao_anh: int, chu_khac: list) -> tuple:
    """Dai cung kich thuoc sat tren hoac duoi khung chu, chon ben it de len chu khac."""
    h = b.bottom - b.top
    tren = (b.left, max(0, b.top - h), b.right, b.top)
    duoi = (b.left, b.bottom, b.right, min(cao_anh, b.bottom + h))

    def de(box):
        return sum(1 for o in chu_khac if o.left < box[2] and box[0] < o.right
                   and o.top < box[3] and box[1] < o.bottom)
    return min((tren, duoi), key=lambda box: (de(box), -(box[3] - box[1])))


# Chup lai toi da bay nhieu khung: chu splash hien dan (log app "alpha=0.0" luc vua nap),
# va inter co the de len giua luc dump va luc chup (24/10/2026, UI-003: dump thay splash,
# anh chup sau 2,5s ra 0 pixel mau title -> FAIL gia).
SO_KHUNG = 5
NHIP = 0.6


def theo_vi_tri_moi(nodes, views) -> list:
    """Node chu lay bounds MOI theo id tu `view_hierarchy_fast`. Cum chu splash nhay len
    khi native ve (24/10/2026: title y=1665 luc chua co ad, y=885 luc co) - do bang bounds
    cua dump cu la do vao nen anh, ra 0 pixel."""
    from dataclasses import replace

    from .ui_dump import Bounds

    moi = {v.rid: v for v in views if v.visible and v.rid}
    return [replace(n, bounds=Bounds(moi[n.resource_id].left, moi[n.resource_id].top,
                                     moi[n.resource_id].right, moi[n.resource_id].bottom))
            if n.resource_id in moi else n for n in nodes]


async def do_nhieu_khung(client, serial: str, package: str, activity: str, nodes, dich: list[str],
                         png_dau: bytes = b"") -> list[dict]:
    """Do tren vai khung CUNG activity voi dump, giu khung chu hien ro nhat (nhieu pixel
    trung mau nhat). Khong khung nao hop le -> [] (dong mau ra NEEDS_HUMAN, khong FAIL)."""
    import asyncio

    from . import device_app, screencap, view_hierarchy_fast

    tot, diem_tot = [], -1
    for i in range(SO_KHUNG):
        png = png_dau if i == 0 and png_dau else await screencap.raw(client, serial)
        _, dang_hien = await device_app.focus(client, serial)
        if png and activity and dang_hien and activity.rsplit(".", 1)[-1] == dang_hien.rsplit(".", 1)[-1]:
            try:
                views = await view_hierarchy_fast.read(client, serial, package, timeout=5)
            except Exception:  # noqa: BLE001 - khong doc duoc thi dung bounds cua dump
                views = []
            m = do(theo_vi_tri_moi(nodes, views), png, dich)
            diem = sum(c[0] for x in m for c in x["dem"].values())
            if diem > diem_tot:
                tot, diem_tot = m, diem
        await asyncio.sleep(NHIP)
    return tot + await _chu_moi(client, serial, package, activity, {x["text"] for x in tot}, dich)


async def _chu_moi(client, serial: str, package: str, activity: str, da_co: set, dich: list[str]) -> list[dict]:
    """Dump lai MOT lan: chu tren man doi sau dump dau (splash ban release ve UI mac dinh truoc, ~1-2s sau moi
    ap splash_ui_config) -> do them cac chu moi. `view_hierarchy_fast` khong co chu nen cac khung tren van mang
    chu cu, dong "'My Super App' mau #FFFFFF" khong khop node nao (AIP886 31/10/2026)."""
    from . import device_app, screencap, ui_dump

    try:
        _, dang_hien = await device_app.focus(client, serial)
        if not activity or activity.rsplit(".", 1)[-1] != (dang_hien or "").rsplit(".", 1)[-1]:
            return []
        nodes = ui_dump.app_nodes(ui_dump.parse_dump(await ui_dump.dump(client, serial)), package)
        if not {n.text for n in nodes if (n.text or "").strip()} - da_co:
            return []
        png = await screencap.raw(client, serial)
        # Dump mat ~2,5s: chup xong man da sang inter thi anh khong phai man cua dump -> bo (0 pixel = FAIL gia).
        _, sau = await device_app.focus(client, serial)
        if activity.rsplit(".", 1)[-1] != (sau or "").rsplit(".", 1)[-1]:
            return []
    except Exception:  # noqa: BLE001 - do them hong thi giu so do cu
        return []
    return [m for m in do(nodes, png, dich) if m["text"] not in da_co]


def do(nodes, png: bytes, dich: list[str]) -> list[dict]:
    """-> [{text, bounds, dem: {hex: [trong_khung, doi_chung]}}] cho moi node co chu."""
    if not png or not dich:
        return []
    try:
        from PIL import Image

        img = Image.open(io.BytesIO(png)).convert("RGB")
    except Exception:  # noqa: BLE001 - anh hong thi khong do, khong lam hong ca buoc
        return []
    co_chu = [n for n in nodes if n.visible and not n.bounds.empty and (n.text or "").strip()]
    ra = []
    for n in co_chu:
        b = n.bounds
        khung = (max(0, b.left), max(0, b.top), min(img.width, b.right), min(img.height, b.bottom))
        doi = _dai_doi_chung(b, img.height, [o.bounds for o in co_chu if o is not n])
        ra.append({"text": n.text, "id": n.resource_id, "bounds": list(khung),
                   "dem": {h.upper(): [_dem(img, khung, _rgb(h)), _dem(img, doi, _rgb(h))] for h in dich}})
    return ra + _cham_active(nodes, img, dich) + _nen_chu(nodes, img, dich)


# Id gia cho so do cham chi trang dang active: dong "slider mau #1565C0" / "indicator mau ..." khop vao day.
ID_CHAM_ACTIVE = "indicator_active"


def _cham_active(nodes, img, dich: list[str]) -> list[dict]:
    """Do mau cham chi trang dang active (cham rong nhat), doi chung = cac cham con lai (cung nen, mau khac)."""
    from . import fo_steps

    cham = [n for n in nodes if n.resource_id == fo_steps.DOT_ID and n.visible] or fo_steps._cham_khong_id(nodes)
    if len(cham) < 2:
        return []
    active = max(cham, key=lambda n: n.bounds.right - n.bounds.left)
    khac = [n for n in cham if n is not active]
    b = active.bounds
    khung = (max(0, b.left), max(0, b.top), min(img.width, b.right), min(img.height, b.bottom))
    dem = {}
    for h in dich:
        doi = sum(_dem(img, (o.bounds.left, o.bounds.top, o.bounds.right, o.bounds.bottom), _rgb(h)) for o in khac)
        dem[h.upper()] = [_dem(img, khung, _rgb(h)), doi]
    return [{"text": "", "id": ID_CHAM_ACTIVE, "bounds": list(khung), "dem": dem}]


# Id gia cho so do mau NEN khung chu ("Nen text #F5F5F5" - background_text_color cua OB).
ID_NEN_CHU = "nen_chu"
GAN_NEN = 6               # nen la mang mau phang, khong khu rang nhu net chu: cho lech nhieu hon chut
LE_NEN = 12               # bo mep khung (bo goc tron lo anh phia sau)
AD_ID_RE = re.compile(r"native|adview|ad_?container|bottomad|flfake|shimmer", re.I)


def _nen_chu(nodes, img, dich: list[str]) -> list[dict]:
    """Mau nen cua khung chua chu (node nho nhat bao >= 2 node chu, vd `ctlContent` chua title + subtitle + nut):
    dem pixel phan NEN (bo cac node chu / nut ben trong) gan tung mau dich, kem mau pho bien nhat do duoc.

    Truoc day dong nay ra NOT_VERIFIABLE "nen co the ban trong suot" (AIP886 R01-03 31/10/2026) - do duoc: nen
    phang mot mau thi phan lon pixel trung mau; ban trong suot chong len anh thi mau pho bien lech, bao FAIL kem
    mau that."""
    from collections import Counter

    W, H = img.size
    # Chu trong vung ad (native: "Ad" + headline trong `linearLayoutTitle`) khong phai khung chu cua app - lay nham
    # thi do nen cua native (AIP886 R01-03 31/10/2026).
    ad = [n.bounds for n in nodes if AD_ID_RE.search(n.resource_id or "")]
    chu = [n for n in nodes if n.visible and not n.bounds.empty and (n.text or "").strip()
           and not any(o.left <= n.bounds.left and o.top <= n.bounds.top and o.right >= n.bounds.right
                       and o.bottom >= n.bounds.bottom for o in ad)]
    if len(chu) < 2:
        return []

    def chua(o, n):
        a, b = o.bounds, n.bounds
        return a.left <= b.left and a.top <= b.top and a.right >= b.right and a.bottom >= b.bottom and o is not n

    khung = [o for o in nodes if o.visible and not o.bounds.empty and not (o.text or "").strip()
             and (o.bounds.right - o.bounds.left) * (o.bounds.bottom - o.bounds.top) < 0.5 * W * H
             and sum(chua(o, n) for n in chu) >= 2]
    if not khung:
        return []
    o = min(khung, key=lambda k: (k.bounds.right - k.bounds.left) * (k.bounds.bottom - k.bounds.top))
    b = o.bounds
    hop = (max(0, b.left + LE_NEN), max(0, b.top + LE_NEN), min(W, b.right - LE_NEN), min(H, b.bottom - LE_NEN))
    if hop[2] <= hop[0] or hop[3] <= hop[1]:
        return []
    trong = [n.bounds for n in nodes if chua(o, n) and n.visible and not n.bounds.empty
             and ((n.text or "").strip() or n.clickable)]
    vung = img.crop(hop)
    diem = []
    for i, p in enumerate(getattr(vung, "get_flattened_data", vung.getdata)()):
        x, y = hop[0] + i % vung.width, hop[1] + i // vung.width
        if not any(t.left <= x < t.right and t.top <= y < t.bottom for t in trong):
            diem.append(p)
    if not diem:
        return []
    pho_bien = Counter(diem).most_common(1)[0][0]
    dem = {}
    for h in dich:
        r0, g0, b0 = _rgb(h)
        dem[h.upper()] = [sum(1 for r, g, bb in diem
                              if abs(r - r0) <= GAN_NEN and abs(g - g0) <= GAN_NEN and abs(bb - b0) <= GAN_NEN),
                          len(diem)]
    return [{"text": "", "id": ID_NEN_CHU, "khung_id": o.resource_id.rsplit("/", 1)[-1], "bounds": list(hop),
             "nen": dem, "pho_bien": "#%02X%02X%02X" % pho_bien, "dem": {}}]
