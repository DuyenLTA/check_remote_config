"""Cham dong "Title dung mau #4957FF; Subtitle dung mau #E0E0E0" bang so do cua `mau_chu`.

Node nao la "Title": tra truong JSON ma case dat (`title_color` = #4957FF -> chu cua
truong `title`), khong co thi node co id chua ten do. Doan theo vi tri la cham nham chu.
"""

from __future__ import annotations

import json
import re

from . import assert_nen_ban_trong
from .mau_chu import HEX_RE, ID_CHAM_ACTIVE, ID_NEN_CHU
from .verdict_levels import FAIL, NEEDS_HUMAN, PASS, out, worst

# "Title dung mau #4957FF", "Subtitle: #E0E0E0", "mau chu subtitle #E0E0E0": ten phan tu dung NGAY truoc ma mau.
# Ten >= 2 chu: truoc day `[A-Za-z_]+` an "u" cua chu "màu" -> do nham node co id chua "u", ra 0-2 pixel
# (AIP886 31/10/2026: "'Preparing your data...' màu #888888" FAIL gia).
TEN_RE = re.compile(r"([A-Za-z_]{2,})\s*(?:đúng\s+)?(?:màu\s*)?:?\s*$", re.I)
# Chu trong ngoac dung truoc "mau #HEX" chinh la chu can do: "Title 'My Super App' màu #FFFFFF".
NGOAC_RE = re.compile(r"[\"“”'‘’]([^\"“”'‘’]{2,80})[\"“”'‘’]")
NEN_RE = re.compile(r"\bn[ềe]n\b|background|\bbg\b", re.I)
NEN = "nền"
# Ten chung chung: khop id kieu "co chua chu nay" la khop bua (AIP886 R01-03: "Nen text" -> node id chua "text"
# o splash, 0 pixel -> FAIL gia).
TEN_CHUNG = {"text", "txt", "label", "button", "btn", "view", "item", "chu"}
# "slider mau #1565C0", "indicator mau ...": mau cham chi trang dang active (mau_chu do rieng).
TEN_CHAM = {"slider", "indicator", "dot", "dots"}
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
    """So do ro nhat (nhieu pixel trung mau nhat) cua chu nay trong moi buoc - mot khung chup luc inter de len
    (0 pixel) khong duoc thang khung splash dung (AIP886 R01-02 31/10/2026)."""
    tot = (None, None)
    for step in (drive or {}).get("steps") or []:
        for m in step.get("mau") or []:
            if hex_.upper() not in m["dem"]:
                continue
            cham_trang = not chu and ten.lower() in TEN_CHAM and m.get("id") == ID_CHAM_ACTIVE
            if cham_trang or (chu and m["text"].strip().casefold() == chu.strip().casefold()) or (
                    not chu and ten.lower() not in TEN_CHUNG and ten.lower() in (m.get("id") or "").lower()):
                if tot[1] is None or m["dem"][hex_.upper()][0] > tot[1]["dem"][hex_.upper()][0]:
                    tot = (step.get("n"), m)
    return tot


def _cap(text: str, cfg: dict) -> list[tuple[str, str, str, int]]:
    """Moi ma mau -> [(ten, chu can do, hex, so chu cung nhom)]. Chu trong ngoac truoc ma mau (sau ma mau
    truoc do) thang; khong co thi lay ten phan tu (title/subtitle) tra theo truong JSON cua case."""
    ra, dau = [], 0
    for m in HEX_RE.finditer(text):
        doan, dau = text[dau:m.start()], m.end()
        # Chi chu CUNG VE voi "mau #HEX": "button 'FR - Next', slider màu #1565C0" la mau cua slider, khong
        # phai cua nut. Ve chi con chu "mau" ("('EN - OB1 title', 'EN - OB2 title', màu #2E7D32)") -> ca nhom.
        ve = re.split(r"[,;]", doan)[-1]
        if NEN_RE.search(ve):
            # "Nen text #F5F5F5": mau NEN (thuong ban trong suot chong len anh) - dem pixel chu khong do duoc.
            ra.append((NEN, "", m.group(1), 1))
            continue
        chu = [c.strip() for c in NGOAC_RE.findall(ve)]
        if not chu and re.fullmatch(r"\s*(?:màu|color)?\s*:?\s*", ve, re.I):
            chu = [c.strip() for c in NGOAC_RE.findall(doan)]
        if chu:
            ra += [(c, c, m.group(1), len(chu)) for c in chu]
            continue
        ten = TEN_RE.search(ve)
        if ten:
            ra.append((ten.group(1), _chu_cua(ten.group(1), m.group(1), cfg), m.group(1), 1))
    return ra


# Nen phang dung mau: phan lon pixel phan nen (bo chu / nut) trung mau dich.
NEN_DAT = 0.6


def _cham_nen(drive: dict, hex_: str, text: str, cfg: dict | None = None) -> dict:
    """"Nen text #F5F5F5": lay lan do khung nen chu co ti le trung mau cao nhat trong moi buoc (`mau_chu._nen_chu`)."""
    tot = None
    for step in (drive or {}).get("steps") or []:
        for m in step.get("mau") or []:
            if m.get("id") == ID_NEN_CHU and hex_ in (m.get("nen") or {}):
                trung, tong = m["nen"][hex_]
                if tot is None or trung / tong > tot[1]:
                    tot = (step.get("n"), trung / tong, m)
    if not tot:
        return out(NEEDS_HUMAN, f"màu nền {hex_}: chưa có ảnh gốc của khung chữ để đo — chưa lái tới màn", text)
    buoc, ti_le, m = tot
    ly = (f"nền khung chữ `{m['khung_id']}` bước {buoc}: {ti_le:.0%} pixel phần nền trùng {hex_} "
          f"(màu phổ biến nhất {m['pho_bien']}; đạt khi ≥{NEN_DAT:.0%})")
    if ti_le >= NEN_DAT:
        return out(PASS, ly, text)
    # Nen ban trong suot chong len anh content: suy nguoc mau lop phu tu anh goc (assert_nen_ban_trong).
    try:
        suy = assert_nen_ban_trong.suy_mau(drive, cfg or {}, m, text)
    except Exception as exc:  # noqa: BLE001 - suy hong thi giu ket qua dem pixel
        suy = None
        ly += f"; không suy được màu lớp phủ: {exc}"
    if suy and suy.get("mau"):
        ly = (f"nền khung chữ `{m['khung_id']}` bước {buoc} là lớp phủ bán trong suốt trên ảnh content (chỉ "
              f"{ti_le:.0%} pixel trùng thẳng {hex_}); suy ngược từ ảnh gốc trên {suy['so_diem']} điểm: màu lớp phủ "
              f"{suy['mau']}, độ phủ {suy['a']:.0%} (đạt khi lệch {hex_} ≤{assert_nen_ban_trong.LECH_MAU}/kênh)")
        return out(PASS if assert_nen_ban_trong.khop(suy["mau"], hex_) else FAIL, ly, text)
    return out(FAIL, ly, text)


def cham(text: str, drive: dict, cfg: dict | None) -> dict | None:
    if not routes(text):
        return None
    ket = []
    for ten, chu, h, nhom in _cap(text, cfg or {}):
        hex_ = f"#{h.upper()}"
        if ten == NEN:
            ket.append(_cham_nen(drive, hex_, text, cfg))
            continue
        buoc, m = _do_cua(drive, ten, chu, hex_)
        ten_hien = repr(chu) if chu == ten else f"{ten} ({chu!r})" if chu else ten
        if not m:
            if nhom > 1:
                continue        # "khoi 'EN-us' ('EN - OB1 title', ...)": chu khong phai node thi bo, do cac chu con lai
            ly_do = (f"không có node chữ nào ứng với {ten!r} để đo màu" if not chu
                     else f"chưa có ảnh gốc của {ten_hien} để đo màu — chưa lái tới màn hoặc bị ad che")
            ket.append(out(NEEDS_HUMAN, ly_do, text))
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
