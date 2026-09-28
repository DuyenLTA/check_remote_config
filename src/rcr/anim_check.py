"""Do mot vung man hinh co dang chay animation khong, va co LAP khong.

Chup vai khung cach nhau mot nhip roi so vung cua node:
  - khung nao khac khung dau qua nguong -> vung do DANG doi, tuc co animation
  - mot khung sau giong lai mot khung truoc (khong ke ke nhau) -> animation
    quay ve khung cu, tuc LAP

Do tren may 2026-09-28 (`ob2Bb2SwipeLottie` cua Piclux, 380x441): khung 1 va
khung 3 lech nhau gan bang 0 trong khi khung 0 vs 1 lech trung binh ~19/kenh -
chu ky khoang 1,05 giay.

KHONG ket luan "dung figma" hay "goi y ro huong": cai do phai co ban thiet ke
de doi chieu, va la danh gia cua nguoi.
"""

from __future__ import annotations

import io
import logging

log = logging.getLogger(__name__)

# Lech trung binh moi kenh mau. Duoi nguong nay coi nhu hai khung y het nhau:
# JPEG/PNG cua may cung khung van lech vai don vi vi nhieu cam ung, thanh trang thai.
NGUONG_DOI = 3.0
NGUONG_GIONG = 1.0


def _lech(a, b) -> float:
    """Lech trung binh moi kenh giua hai anh cung kich thuoc."""
    from PIL import ImageChops

    d = ImageChops.difference(a, b)
    tong = sum(sum(h[i] * i for i in range(256)) for h in (ch.histogram() for ch in d.split()))
    return tong / max(1, a.width * a.height * len(d.split()))


def do(frames: list[bytes], bounds) -> dict:
    """{doi, lap, lech_max, lech_cuoi} tu cac khung PNG da chup.

    `lap` KHONG doi hai khung trung khit nhau. Do that tren may 2026-09-28
    (`ob2Bb2SwipeLottie`, 10 khung cach 0,30s): cap giong nhau nhat van lech
    5,5/255 - vung crop chua ca anh nen dang doi, nen khung khong bao gio lap
    y het. Dau hieu dung cua "lap" la animation KHONG DUNG LAI: chay mot lan
    roi thoi thi may khung cuoi dung yen canh nhau.
    """
    try:
        from PIL import Image
    except ImportError:                       # pragma: no cover - Pillow la phu thuoc that
        return {"doi": False, "lap": False, "loi": "khong co Pillow de so anh"}
    if len(frames) < 3:
        return {"doi": False, "lap": False, "loi": "chua du 3 khung de so"}
    hop = (bounds.left, bounds.top, bounds.right, bounds.bottom)
    anh = []
    for png in frames:
        try:
            anh.append(Image.open(io.BytesIO(png)).crop(hop).convert("RGB"))
        except Exception as exc:              # anh hong thi bo khung do
            log.debug("bo mot khung: %s", exc)
    if len(anh) < 3:
        return {"doi": False, "lap": False, "loi": "khong doc duoc anh"}

    lien_tiep = [_lech(anh[i], anh[i + 1]) for i in range(len(anh) - 1)]
    doi = max(lien_tiep) > NGUONG_DOI
    # Hai nhip cuoi deu dung yen -> animation da chay xong va dung.
    dung_lai = all(x < NGUONG_DOI for x in lien_tiep[-2:])
    return {"doi": doi, "lap": doi and not dung_lai,
            "lech_max": round(max(lien_tiep), 1),
            "lech_cuoi": round(lien_tiep[-1], 1),
            "so_khung": len(anh)}
