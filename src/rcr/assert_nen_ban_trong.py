"""Mau nen BAN TRONG SUOT cua khung chu OB ("Nen text #F5F5F5"): suy nguoc mau lop phu tu anh nen goc.

Khung chu OB cua AIP886 la lop phu ban trong suot tren anh content (nhin xuyen thay anh): dem pixel trung #F5F5F5
chi ra 1% du app to dung mau (AIP886 R01-03 31/10/2026). Biet anh goc phia duoi (`onbN.content`) thi moi pixel man
la pha tron P = a*C + (1-a)*I: hoi quy tuyen tinh P theo I tren tung kenh -> do doc = 1-a, chan = a*C -> C, a.
Dung khi C lech mau dich toi da LECH_MAU moi kenh.
"""

from __future__ import annotations

import base64
import io

from . import fo_steps, ui_dump
from .assert_anh_content import THU_MUC, _khoi
from .splash_media import CHE_DO, _dat_len_man, _khung_media, _lech, _tai

LECH_MAU = 12
A_TOI_THIEU = 0.05        # lop phu gan nhu trong suot hoan toan thi khong suy duoc mau


def _hoi_quy(xs: list[float], ys: list[float]) -> tuple[float, float]:
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    if sxx <= 0:
        return 0.0, my
    k = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx
    return k, my - k * mx


def suy_mau(drive: dict, cfg: dict, m: dict, text: str) -> dict | None:
    """-> {mau, a, so_diem} cua lop phu khung `m` (so do `mau_chu._nen_chu`), None neu khong du du lieu."""
    from PIL import Image

    st = next((s for s in (drive or {}).get("steps") or [] if m in (s.get("mau") or [])), None)
    if not st or not st.get("shot") or not st.get("dump"):
        return None
    nodes = ui_dump.parse_dump(st["dump"])
    url = (_khoi(text, cfg).get(f"onb{fo_steps.onboarding_page(nodes)}") or {}).get("content")
    if not url:
        return None
    anh = [n for n in nodes if n.visible and not n.bounds.empty and n.cls.endswith("ImageView")]
    if not anh:
        return None
    nen = max(anh, key=lambda n: (n.bounds.right - n.bounds.left) * (n.bounds.bottom - n.bounds.top)).bounds
    man = max(nodes, key=lambda n: (n.bounds.right, n.bounds.bottom)).bounds
    shot = Image.open(io.BytesIO(base64.b64decode(st["shot"].split(",", 1)[1]))).convert("RGB")
    s = shot.width / man.right
    bw, bh = round((nen.right - nen.left) * s), round((nen.bottom - nen.top) * s)
    vung = shot.crop((round(nen.left * s), round(nen.top * s), round(nen.left * s) + bw, round(nen.top * s) + bh))
    src = _khung_media(_tai(url, THU_MUC))[0][0]
    # Kieu scale cua anh nen: kieu khop nhat tren phan anh KHONG bi lop phu (ngoai khung chu).
    l, t, r, b = (round(v * s) for v in m["bounds"])
    ox, oy = round(nen.left * s), round(nen.top * s)
    ngoai = [not (l - ox <= x < r - ox and t - oy <= y < b - oy) for y in range(bh) for x in range(bw)]
    goc = min((_dat_len_man(src, bw, bh, cd).resize((bw, bh)) for cd in CHE_DO),
              key=lambda g: _lech(vung, g, ngoai))
    chu = [n.bounds for n in nodes if n.visible and not n.bounds.empty and ((n.text or "").strip() or n.clickable)]
    px, ig = [], []
    for y in range(max(t, oy), min(b, oy + bh)):
        for x in range(max(l, ox), min(r, ox + bw)):
            X, Y = x / s, y / s
            if any(c.left <= X < c.right and c.top <= Y < c.bottom for c in chu):
                continue
            px.append(vung.getpixel((x - ox, y - oy)))
            ig.append(goc.getpixel((x - ox, y - oy)))
    if len(px) < 200:
        return None
    mau, a_kenh = [], []
    for k in range(3):
        doc, chan = _hoi_quy([p[k] for p in ig], [p[k] for p in px])
        a = 1 - doc
        a_kenh.append(a)
        mau.append(chan / a if a > A_TOI_THIEU else -1)
    a = sum(a_kenh) / 3
    if a <= A_TOI_THIEU or min(mau) < 0:
        return {"a": round(a, 2), "mau": "", "so_diem": len(px)}
    hex_ = "#%02X%02X%02X" % tuple(max(0, min(255, round(v))) for v in mau)
    return {"a": round(a, 2), "mau": hex_, "so_diem": len(px)}


def khop(hex_do: str, hex_dich: str) -> bool:
    if not hex_do:
        return False
    a = [int(hex_do[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(hex_dich[i:i + 2], 16) for i in (1, 3, 5)]
    return all(abs(x - y) <= LECH_MAU for x, y in zip(a, b))
