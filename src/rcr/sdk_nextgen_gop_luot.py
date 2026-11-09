"""Gop luot cham checklist Next-Gen cung build thay vi ghi de.

Chay lai cung build (bot giao lai, may loi giua chung...) truoc day ra mot report moi tu dau: dong do tay luot sau
do lai theo cach khac, Sai luot truoc mat luon (ADA895 3.3.0, 09/11/2026: HV-01 Sai luc 19:13, luot 22:05 ra Khop
vi chi bam inter). Luat gop:
  - Dong code ra DO_TAY o luot moi: luot truoc co Sai do tay -> lay Sai do (Sai dinh, xem `sai_truoc`); khong thi
    lay ket qua do tay moi nhat da DU BUOC (`sdk_nextgen_buoc_do_tay.du_buoc`). Dong do tay cu khong khai buoc
    (truoc khi co luat buoc) chi dung lai khi la Sai.
  - Dong code cham: giu ket qua luot moi (cung quy trinh tu dong da chay lai), khac luot truoc thi vao muc lech.
  - Moi dong luu `luot_truoc` (ket qua tung luot cu) -> report hien muc "Lech giua cac luot" de nguoi xem.
"""

from __future__ import annotations

import json
from pathlib import Path

from .models import RcError
from .sdk_nextgen_buoc_do_tay import du_buoc
from .sdk_nextgen_ket import DO_TAY, SAI

KET_QUA = "ket-qua.json"


def _la_tay(r: dict) -> bool:
    return r.get("cham_boi", "code") != "code" and r.get("ket") != DO_TAY


def doc_luot(d: Path, package: str) -> dict:
    f = Path(d) / KET_QUA
    if not f.is_file():
        raise RcError(f"--gop-luot: không thấy {f}")
    data = json.loads(f.read_text("utf-8"))
    if (data.get("meta") or {}).get("package") != package:
        raise RcError(f"--gop-luot: {d} là lượt của {(data.get('meta') or {}).get('package')}, không phải {package}")
    return {"thu_muc": str(d), "data": data}


def khoa_build(meta: dict) -> str:
    """Khoa "cung build": phien ban + sha256 APK. Dev day lai cung version van la build khac (verify phai cai ban moi
    nhat) -> khong co sha thi khong tu gop, chi gop khi ghi ro --gop-luot."""
    pb, sha = (meta or {}).get("phien_ban") or "", (meta or {}).get("apk_sha256") or ""
    return f"{pb}|{sha}" if pb and sha else ""


def thu_tu(thu_muc: str) -> str:
    """Thu tu luot = gio trong ten thu muc sdk-<pkg>-YYMMDD-HHMMSS (khong doi khi --cham-lai, khac `cham_luc`)."""
    ten = Path(thu_muc).name
    return ten[-13:] if len(ten) >= 13 else ten


def cung_thu_muc(a: str, b: str) -> bool:
    try:
        return Path(a).resolve() == Path(b).resolve()
    except OSError:
        return a == b


def tim(out_dir: Path, package: str, khoa: str, tru: Path | None = None) -> list[dict]:
    """Luot cu cung package + cung `khoa_build` trong `out_dir`, cu truoc moi sau."""
    if not khoa:
        return []
    ra = []
    for d in sorted(Path(out_dir).glob(f"sdk-{package}-*"), key=lambda x: thu_tu(str(x))):
        if tru is not None and cung_thu_muc(str(d), str(tru)):
            continue
        try:
            luot = doc_luot(d, package)
        except (RcError, OSError, ValueError):
            continue
        if khoa_build(luot["data"].get("meta") or {}) == khoa:
            ra.append(luot)
    return ra


_GIU = ("ket", "cham_boi", "ly_do", "buoc", "khong_tai_hien")


def _tom(luot: dict) -> dict:
    m = luot["data"].get("meta") or {}
    return {"thu_muc": luot["thu_muc"], "cham_luc": m.get("cham_luc", ""), "serial": m.get("serial", ""),
            "ket": {r["ma"]: {k: r[k] for k in _GIU if k in r} for r in luot["data"].get("ket_qua", [])}}


def _chon(tay: list[tuple[str, dict]]) -> tuple[str, dict] | None:
    """Ket qua do tay de dung lai, `tay` cu truoc moi sau. Moi nhat truoc: Sai, hoac lan da chay lai buoc tai hien
    (`khong_tai_hien` = da go Sai cu co bang chung) thi lay luon; khong thi Khop/ngoai pham vi moi nhat du buoc,
    nhung chi khi khong co Sai nao cu hon (Sai dinh)."""
    for t in reversed(tay):
        if t[1]["ket"] == SAI or t[1].get("khong_tai_hien"):
            return t
    return next((t for t in reversed(tay) if du_buoc(t[1])), None)


def gop(moi: dict, cu: list[dict]) -> tuple[dict, list[str]]:
    """-> (data da gop, ma dong lay tu luot cu). `cu`: [{thu_muc, data}]."""
    if not cu:
        return moi, []
    cu = sorted(cu, key=lambda l: thu_tu(l["thu_muc"]))
    truoc = list(moi.get("luot_truoc") or [])
    for l in cu:
        if not any(cung_thu_muc(t["thu_muc"], l["thu_muc"]) for t in truoc):
            truoc.append(_tom(l))
    moi["luot_truoc"] = sorted(truoc, key=lambda t: thu_tu(t["thu_muc"]))
    lay: list[str] = []
    ra = []
    for r in moi["ket_qua"]:
        tay = [(l["thu_muc"], x) for l in cu for x in l["data"].get("ket_qua", []) if x["ma"] == r["ma"] and _la_tay(x)]
        chon = _chon(tay) if r["ket"] == DO_TAY else None
        if chon is None:
            ra.append(r)
            continue
        tu, x = chon
        ra.append({**x, "ket_code": r.get("ket_code", r["ket"]), "bang_chung": x.get("bang_chung") or r["bang_chung"],
                   "tu_luot": tu})
        lay.append(r["ma"])
    moi["ket_qua"] = ra
    return moi, lay


def sai_truoc(data: dict, ma: str) -> dict | None:
    """Sai do tay con hieu luc cua dong `ma` -> {thu_muc, ly_do}. Moi nhat truoc: dong hien tai roi luot cu; gap
    Sai thi tra, gap lan chay lai khong tai hien (`khong_tai_hien`) thi Sai cu da go -> None. Sai do code khong dinh
    (luot moi tu chay lai dung quy trinh)."""
    hien = next((r for r in data["ket_qua"] if r["ma"] == ma), None)
    ds = [(t["thu_muc"], t["ket"][ma]) for t in data.get("luot_truoc") or [] if ma in t["ket"]]
    if hien:
        ds.append((hien.get("tu_luot") or "lượt này", hien))
    for tu, x in reversed(ds):
        if x.get("khong_tai_hien") and x.get("ket") != SAI:
            return None
        if x.get("ket") == SAI and _la_tay(x):
            return {"thu_muc": tu, "ly_do": x.get("ly_do", "")}
    return None


def lech(data: dict) -> list[dict]:
    """Dong ma ket qua hien tai khac ket qua mot luot cu (bo qua luot cu con DO_TAY)."""
    ra = []
    for r in data["ket_qua"]:
        khac = [{"thu_muc": t["thu_muc"], "cham_luc": t.get("cham_luc", ""), **t["ket"][r["ma"]]}
                for t in data.get("luot_truoc") or []
                if r["ma"] in t["ket"] and t["ket"][r["ma"]]["ket"] not in (DO_TAY, r["ket"])]
        if khac:
            ra.append({"ma": r["ma"], "ten": r["ten"], "ket": r["ket"], "luot_khac": khac})
    return ra
