"""Test Data "key=JSON dang chay tren Firebase, sua: a.b="x", c=#FF0000": lay JSON dang chay cua `key` roi sua field.

Tab TC SDK daily checkin (sua 13/11/2026) khong dan JSON day du ma ghi "JSON dang chay tren Firebase, sua: ...". Truoc
day rc_pairs tach thanh `checkin_sdk_config = "JSON dang chay tren Firebase"` + key rac `title_text_color` -> rc_extract
dung case (NEEDS_HUMAN). Gia tri dang chay lay tu baseline (ban release: template Firebase; ban debug: file activate tren
may), nen JSON dat len chi khac dung cac field TC ghi.

Field viet theo duong cham (`checkin.title`) phai co san trong JSON. Field khong cham (`title_text_color`) duoc tim o moi
tang va phai co DUNG MOT cho. Sai mot dieu kien -> giu nguyen dong, rc_extract dung case kem ly do (khong doan).

Key app CO doc (DEX) nhung server CHUA khai (AIP893 2.6.0 13/11/2026: ca 5 key checkin): app chay bang mac dinh trong
code, khong co JSON nao tren Firebase. Khi do JSON dat len chi gom cac field TC ghi (`{}` + field, tao nhanh khi thieu),
field khac de app tu lay mac dinh.
"""

from __future__ import annotations

import dataclasses
import json
import re

DONG_RE = re.compile(
    r"^\s*(?P<key>[A-Za-z][A-Za-z0-9_]*)\s*[=:]\s*JSON\s+(?:đang|dang)\s+ch(?:ạ|a)y\b[^,:]*,?\s*"
    r"s(?:ử|u)a\s*:\s*(?P<sua>.+?)\s*$", re.I)
FIELD_RE = re.compile(r'(?P<path>[A-Za-z_][\w.]*)\s*=\s*(?:"(?P<q>[^"]*)"|(?P<v>[^,]+))')


def cac_sua(text: str) -> list[tuple[str, str, bool]]:
    """'a.b="x", c=#F00' -> [("a.b", "x", True), ("c", "#F00", False)] (co ngoac kep = chac chan la chuoi)."""
    return [(m["path"], m["q"] if m["q"] is not None else m["v"].strip(), m["q"] is not None)
            for m in FIELD_RE.finditer(text)]


def _cho_cua(goc, ten: str) -> list:
    """Moi (dict cha) co khoa `ten` o bat ky tang nao."""
    ra = []
    if isinstance(goc, dict):
        if ten in goc:
            ra.append(goc)
        for v in goc.values():
            ra += _cho_cua(v, ten)
    elif isinstance(goc, list):
        for v in goc:
            ra += _cho_cua(v, ten)
    return ra


def _ep_kieu(cu, gia_tri: str, chuoi: bool):
    if chuoi or isinstance(cu, str):
        return gia_tri
    try:
        return json.loads(gia_tri)
    except ValueError:
        return gia_tri


def ap_dung(json_goc: str, sua: list[tuple[str, str, bool]], tao_moi: bool = False) -> tuple[str | None, str]:
    """-> (JSON moi, "") hoac (None, ly do khong sua duoc). `tao_moi`: JSON goc rong, field thieu thi tao."""
    try:
        goc = json.loads(json_goc)
    except (TypeError, ValueError):
        return None, "giá trị đang chạy không phải JSON"
    if not sua:
        return None, "không đọc được field cần sửa"
    for path, gia_tri, chuoi in sua:
        phan = path.split(".")
        if len(phan) > 1:
            cha = goc
            for p in phan[:-1]:
                if tao_moi and isinstance(cha, dict):
                    cha = cha.setdefault(p, {})
                else:
                    cha = cha.get(p) if isinstance(cha, dict) else None
            if not isinstance(cha, dict) or (phan[-1] not in cha and not tao_moi):
                return None, f"JSON đang chạy không có field {path}"
        else:
            cho = _cho_cua(goc, path) or ([goc] if tao_moi else [])
            if len(cho) != 1:
                return None, f"field {path} có {len(cho)} chỗ trong JSON đang chạy (cần đúng 1)"
            cha = cho[0]
        cha[phan[-1]] = _ep_kieu(cha.get(phan[-1], ""), gia_tri, chuoi)
    return json.dumps(goc, ensure_ascii=False, separators=(",", ":")), ""


def thay(pairs: list, dang_chay: dict[str, str], app_doc: frozenset[str] = frozenset()) -> list:
    """[(tab, Case)] -> cung danh sach, dong "key=JSON dang chay..., sua: ..." da thay bang JSON da sua."""
    ra = []
    for tab, c in pairs:
        td = c.test_data or ""
        if not any(DONG_RE.match(l) for l in td.split("\n")):
            ra.append((tab, c))
            continue
        dong = []
        for line in td.split("\n"):
            m = DONG_RE.match(line)
            moi = None
            if m and m["key"] in dang_chay:
                moi, _ = ap_dung(dang_chay[m["key"]], cac_sua(m["sua"]))
            elif m and m["key"] in app_doc:
                moi, _ = ap_dung("{}", cac_sua(m["sua"]), tao_moi=True)
            dong.append(f"{m['key']}={moi}" if moi else line)
        ra.append((tab, dataclasses.replace(c, test_data="\n".join(dong))))
    return ra


def key_chua_ro(case, dang_chay, app_doc) -> list[str]:
    """Key ghi "JSON dang chay, sua: ..." ma chua biet app co doc khong (server chua khai, DEX chua tra) -> can tra DEX."""
    return sorted({m["key"] for line in (case.test_data or "").splitlines() if (m := DONG_RE.match(line))
                   and m["key"] not in dang_chay and m["key"] not in app_doc})
