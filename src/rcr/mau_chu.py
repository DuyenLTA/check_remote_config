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
    return tot


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
    return ra
