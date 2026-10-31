"""Dong "... anh content OB1": anh nen trang OB co dung file `onbN.content` cua case khong.

So vung anh nen (node ImageView lon nhat cua trang) tren anh chup trang do voi file content cua MOI trang trong
khoi ngon ngu case dat: dung khi file cua trang N khop nhat va lech duoi nguong. Anh chup trong report la ban thu
nho 360px - du cho so o 54x120 (`splash_media.KICH`).
Truoc day ve nay khong ai cham, dong van ra PASS nho phan ma mau (AIP886 R01-03 31/10/2026).
"""

from __future__ import annotations

import base64
import io
import json
import re
from pathlib import Path

from . import fo_steps, ui_dump
from .splash_media import CHE_DO, _dat_len_man, _khung_media, _lech, _tai
from .verdict_levels import FAIL, NEEDS_HUMAN, PASS, out

ANH_RE = re.compile(r"[ảa]nh\s+content\s+OB\s*(\d)", re.I)
NGOAC_RE = re.compile(r"[\"“”'‘’]([^\"“”'‘’]{2,80})[\"“”'‘’]")
NGUONG_LECH = 28.0        # lech trung binh moi kenh toi da giua vung anh nen va file content (do that: dung 15,8, sai 62-78)
THU_MUC = Path(__file__).resolve().parents[2] / "out" / "media"


def _khoi(text: str, cfg: dict) -> dict:
    """Khoi ngon ngu cua onboard_config_content_new ma dong nay noi toi (theo chu trong ngoac), khong ro thi khoi dau."""
    try:
        ds = json.loads((cfg or {}).get("onboard_config_content_new") or "[]")
    except ValueError:
        return {}
    ds = [k for k in ds if isinstance(k, dict)] if isinstance(ds, list) else []
    chu = {c.strip().casefold() for c in NGOAC_RE.findall(text)}
    for k in ds:
        if any(str(v).strip().casefold() in chu for o in k.values() if isinstance(o, dict) for v in o.values()):
            return k
    return ds[0] if ds else {}


def _anh_trang(drive: dict, trang: int):
    """(anh thu nho, bounds ImageView nen, kich man) cua buoc dang o trang OB `trang`."""
    from PIL import Image

    for st in (drive or {}).get("steps") or []:
        if "Onboarding" not in (st.get("activity") or "") or not st.get("dump") or not st.get("shot"):
            continue
        try:
            nodes = ui_dump.parse_dump(st["dump"])
        except Exception:  # noqa: BLE001
            continue
        if fo_steps.onboarding_page(nodes) != trang:
            continue
        anh = [n for n in nodes if n.visible and not n.bounds.empty and n.cls.endswith("ImageView")]
        if not anh:
            continue
        nen = max(anh, key=lambda n: (n.bounds.right - n.bounds.left) * (n.bounds.bottom - n.bounds.top))
        man = max(nodes, key=lambda n: (n.bounds.right, n.bounds.bottom)).bounds
        img = Image.open(io.BytesIO(base64.b64decode(st["shot"].split(",", 1)[1]))).convert("RGB")
        return img, nen.bounds, (man.right, man.bottom), st.get("n")
    return None


def cham(text: str, drive: dict, cfg: dict | None) -> dict | None:
    m = ANH_RE.search(text)
    if not m:
        return None
    trang = int(m.group(1))
    khoi = _khoi(text, cfg or {})
    url = (khoi.get(f"onb{trang}") or {}).get("content")
    if not url:
        return out(NEEDS_HUMAN, f"case không đặt content cho OB{trang}", text)
    co = _anh_trang(drive, trang)
    if not co:
        return out(NEEDS_HUMAN, f"chưa có ảnh chụp trang OB{trang} để so ảnh content", text)
    img, b, (w, h), buoc = co
    sx, sy = img.width / w, img.height / h
    vung = img.crop((round(b.left * sx), round(b.top * sy), round(b.right * sx), round(b.bottom * sy)))
    from PIL import Image

    vung = vung.resize((54, 120), Image.BILINEAR)
    na = [True] * (54 * 120)
    sai = {}
    for n in range(1, 7):
        u = (khoi.get(f"onb{n}") or {}).get("content")
        if not u or u in sai:
            continue
        try:
            src = _khung_media(_tai(u, THU_MUC))[0][0]
        except Exception:  # noqa: BLE001
            continue
        bw, bh = b.right - b.left, b.bottom - b.top
        sai[u] = min(_lech(vung, _dat_len_man(src, bw, bh, cd), na) for cd in CHE_DO)
    if url not in sai:
        return out(NEEDS_HUMAN, f"không tải được ảnh content OB{trang}", text)
    gan_nhat = min(sai, key=sai.get)
    ly = (f"ảnh nền OB{trang} bước {buoc} lệch {sai[url]:.1f} so với content OB{trang} "
          f"({url.rsplit('/', 1)[-1]}); ảnh content khác lệch "
          f"{', '.join(f'{v:.1f}' for k, v in sai.items() if k != url) or '—'}")
    return out(PASS if gan_nhat == url and sai[url] < NGUONG_LECH else FAIL, ly, text)
