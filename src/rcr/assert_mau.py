"""Cham dong "Title dung mau #4957FF; Subtitle dung mau #E0E0E0" bang so do cua `mau_chu`.

Node nao la "Title": tra truong JSON ma case dat (`title_color` = #4957FF -> chu cua
truong `title`), khong co thi node co id chua ten do. Doan theo vi tri la cham nham chu.
"""

from __future__ import annotations

import json
import re

from .mau_chu import HEX_RE
from .verdict_levels import FAIL, NEEDS_HUMAN, PASS, out, worst

# "Title dung mau #4957FF", "Subtitle: #E0E0E0", "mau chu subtitle #E0E0E0"
CAP_RE = re.compile(r"([A-Za-z_]+)\s*(?:đúng\s+)?(?:màu\s*)?:?\s*#([0-9a-f]{6})\b", re.I)
# Chu dung mau phai co it nhat chung nay pixel trung mau, va gap 3 lan dai doi chung.
TOI_THIEU = 40
GAP = 3


def routes(text: str) -> bool:
    return bool(HEX_RE.search(text) and re.search(r"màu|color", text, re.I))


def _chu_cua(ten: str, hex_: str, cfg: dict) -> str:
    """Chu ma case dat cho phan tu `ten` (title -> truong `title` khi `title_color` = hex)."""
    khoa = re.sub(r"[^a-z]", "", ten.lower())
    for value in (cfg or {}).values():
        try:
            obj = json.loads(value) if isinstance(value, str) else None
        except ValueError:
            continue
        if not isinstance(obj, dict):
            continue
        for k, v in obj.items():
            if (k.lower().endswith("color") and str(v).lower() == f"#{hex_}".lower()
                    and re.sub(r"[^a-z]", "", k.lower()[:-5]) == khoa):
                chu = obj.get(k[:-6]) or obj.get(k[:-5].rstrip("_"))
                if isinstance(chu, str) and chu:
                    return chu
    return ""


def _do_cua(drive: dict, ten: str, chu: str, hex_: str):
    for step in reversed((drive or {}).get("steps") or []):
        for m in step.get("mau") or []:
            if hex_.upper() not in m["dem"]:
                continue
            if (chu and m["text"].strip() == chu.strip()) or (
                    not chu and ten.lower() in (m.get("id") or "").lower()):
                return step.get("n"), m
    return None, None


def cham(text: str, drive: dict, cfg: dict | None) -> dict | None:
    if not routes(text):
        return None
    ket = []
    for ten, h in CAP_RE.findall(text):
        hex_ = f"#{h.upper()}"
        chu = _chu_cua(ten, h, cfg or {})
        buoc, m = _do_cua(drive, ten, chu, hex_)
        ten_hien = f"{ten} ({chu!r})" if chu else ten
        if not m:
            ket.append(out(NEEDS_HUMAN, f"chưa có ảnh gốc của {ten_hien} để đo màu — chưa lái tới màn "
                                        "hoặc bị ad che", text))
            continue
        trong, doi = m["dem"][hex_]
        dat = trong >= TOI_THIEU and trong >= GAP * doi
        # Nen tu no da mang mau dich: dem khong tach duoc chu khoi nen -> khong ket luan FAIL.
        v = PASS if dat else NEEDS_HUMAN if doi >= TOI_THIEU else FAIL
        ket.append(out(v, f"{ten_hien} bước {buoc}: {trong} pixel trùng {hex_} trong khung chữ, {doi} ở dải "
                          f"đối chứng cùng nền (đạt khi ≥{TOI_THIEU} và ≥{GAP}× đối chứng)"
                          + (" — nền trùng màu chữ, không tách được" if v == NEEDS_HUMAN else ""), text))
    if not ket:
        return None
    return ket[0] if len(ket) == 1 else out(worst(k["verdict"] for k in ket),
                                             "; ".join(k["reason"] for k in ket), text)
