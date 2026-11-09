"""Cham checklist SDK Next-Gen tu mot thu muc bang chung da thu (khong can may).

Cung thu muc -> cung ket qua: luat la code, khong phu thuoc nguoi/Claude cham.
Phan code khong cham chac duoc ra DO_TAY; Claude do tay roi ghi bang `cham_tay()`
(giu dau vet ai cham, cham bang gi) - giong `cham_tay.py` cua nhanh bo TC.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from . import (sdk_nextgen_buoc_do_tay, sdk_nextgen_cham_build, sdk_nextgen_cham_ev_3a, sdk_nextgen_cham_ev_3b,
               sdk_nextgen_cham_muc4, sdk_nextgen_gop_luot)
from .models import RcError
from .sdk_nextgen_cham_build import MARK_TAG
from .sdk_nextgen_events import _TT, chan_khi_offline, crash, doc_events, loc, tach_moc
from .sdk_nextgen_ket import DO_TAY, KHONG_AP_DUNG, KHOP, SAI

KET_QUA = "ket-qua.json"
KET_TAY = (KHOP, SAI)
# Do tay con duoc dua dong vao muc "Ngoai pham vi / khong ap dung" (checklist ghi N/A, luat 2/4 WORKFLOW).
KET_GHI_TAY = KET_TAY + (KHONG_AP_DUNG,)


def _doc(d: Path, ten: str) -> str | None:
    f = d / ten
    return f.read_text("utf-8", "replace") if f.exists() else None


def cham_thu_muc(d: Path) -> dict:
    """-> {meta, ket_qua: [...]} tu `bang-chung.json` + cac file log-*.txt trong `d`."""
    d = Path(d)
    bc_file = d / "bang-chung.json"
    if not bc_file.exists():
        raise RcError(f"Không thấy {bc_file} — thư mục này chưa thu bằng chứng (chạy rcr-sdk-check --package ...)")
    bc = json.loads(bc_file.read_text("utf-8"))
    pkg = bc["package"]
    fo, off = _doc(d, "log-fo.txt") or "", _doc(d, "log-offline.txt")
    bc.update(log_khoi_dong=_doc(d, "log-khoi-dong.txt") or "", log_mo_lai=_doc(d, "log-mo-lai.txt") or "", log_fo=fo)
    # Luot offline: doan truoc moc "mang bat" la luc mat mang (EV-04/21/24); doan sau cho KT-01.
    off_mat, off_sau = tach_moc(off, MARK_TAG, "mang bat") if off is not None else (None, "")
    bc.update(log_offline_sau=off_sau, log_offline_mat=off_mat or "")
    ev, ev_off = doc_events(fo), doc_events(off_mat or "")
    off = off_mat
    ket: list[dict] = []
    if "1" in bc["muc"]:
        ket += sdk_nextgen_cham_build.tat_ca(bc, pkg, ev)
    if "3" in bc["muc"]:
        mang_tat = bc.get("offline_mang_that_tat", True)
        crash_off = crash(off or "", pkg)
        failed = loc(ev, "ad_load", thanh_cong=False) + (loc(ev_off, "ad_load", thanh_cong=False) if mang_tat else [])
        a = sdk_nextgen_cham_ev_3a.tat_ca(ev, failed)
        if crash_off:  # EV-04 doi ca "khong crash" luc mat mang
            a = [{**r, "ket": SAI, "ly_do": "App crash khi mất mạng. " + r["ly_do"], "bang_chung": crash_off + r["bang_chung"]}
                 if r["ma"] == "EV-04" else r for r in a]
        co_resume = any(m and m.group(2) == MARK_TAG and "resume" in d for d in fo.splitlines() for m in [_TT.match(d)])
        ket += a + sdk_nextgen_cham_ev_3b.tat_ca(ev, ev_off, off, crash_off, chan_khi_offline(off or "", pkg),
                                                 co_resume, mang_tat)
    if "2" in bc["muc"]:
        ket += sdk_nextgen_cham_muc4.muc2(ev, fo)
    if "4" in bc["muc"]:
        ket += sdk_nextgen_cham_muc4.tat_ca(bc, ev, {"fo": fo, "khoi_dong": bc["log_khoi_dong"], "offline_mat": off_mat or "",
                                                     "offline_sau": off_sau, "cham": _doc(d, "log-cham.txt")}, pkg)
    if bc.get("fo_bo_qua"):
        ket = bo_qua_fo(ket, bc["fo_bo_qua"])
    if bc.get("fo_loi"):
        # Lai FO hong giua chung: log thieu doan sau -> "thieu event" co the chi la chua toi, khong ket luan Sai.
        ket = [{**r, "ket": DO_TAY, "ly_do": f"Lái FO lỗi ({bc['fo_loi']}) — code ra Sai trên log thiếu: {r['ly_do']}"}
               if r["ket"] == SAI and r["ma"].startswith(("EV", "1.7", "HT", "HV")) else r for r in ket]
    meta = {k: bc.get(k) for k in ("package", "serial", "muc", "debuggable", "mo_lai_ms", "ad_click", "app_label", "sdk",
                                   "phien_ban", "apk_sha256")}
    meta["cham_luc"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    return {"meta": meta, "ket_qua": ket}


# Dong chi doc log luot mat mang -> van cham duoc khi bo luot FO.
_TU_LOG_OFFLINE = {"EV-04", "EV-21", "EV-24"}


def bo_qua_fo(ket: list[dict], ly_do: str) -> list[dict]:
    """Bo luot FO -> log FO rong: dong dua vao FO (EV/HT/HV/1.7/1.8/MED-02) khong duoc ra Khop/Sai
    tren log rong (vd "khong ban trung" Khop vi khong co gi) -> Do tay kem ly do."""
    def dua_vao_fo(ma: str) -> bool:
        return ma not in _TU_LOG_OFFLINE and (ma.startswith(("EV", "HT", "HV")) or ma in ("1.7", "1.8", "MED-02"))
    return [{**r, "ket": DO_TAY, "ly_do": f"Không đo: {ly_do}."} if r["ket"] in KET_TAY and dua_vao_fo(r["ma"]) else r
            for r in ket]


def giu_cham_tay(moi: dict, cu: dict | None) -> dict:
    """Cham lai tu log thi dong do tay cu (cham_boi khac "code") giu nguyen, khong bi ghi de."""
    if not cu:
        return moi
    tay = {r["ma"]: r for r in cu.get("ket_qua", []) if r.get("cham_boi", "code") != "code"}
    moi["ket_qua"] = [tay.get(r["ma"], r) for r in moi["ket_qua"]]
    if cu.get("luot_truoc"):
        moi["luot_truoc"] = cu["luot_truoc"]
    return moi


def ghi(d: Path, data: dict) -> Path:
    f = Path(d) / KET_QUA
    f.write_text(json.dumps(data, ensure_ascii=False, indent=1), "utf-8")
    return f


def doc(d: Path) -> dict:
    f = Path(d) / KET_QUA
    if not f.exists():
        raise RcError(f"Không thấy {f}")
    return json.loads(f.read_text("utf-8"))


def cham_tay(data: dict, ma: str, ket: str, ly_do: str, ai: str = "Claude", buoc: dict | None = None,
             khong_tai_hien: str = "") -> dict:
    """Ghi ket qua do tay cho dong `ma` (thuong la DO_TAY): Khop/Sai, hoac Khong ap dung + ly do co so do.

    `buoc`: {id: ok|sai|khong:<ly do>} theo `sdk_nextgen_buoc_do_tay.BUOC` - thieu buoc thi khong duoc Khop /
    ngoai pham vi. Dong da co Sai (luot nay hoac luot truoc cung build) chi doi sang ket khac khi
    `khong_tai_hien` ghi lai da chay dung buoc tai hien cua Sai do ma khong ra loi.
    """
    if ket not in KET_GHI_TAY:
        raise RcError("--ket phải là KHOP, SAI hoặc KHONG_AP_DUNG (ngoài phạm vi / N/A)")
    if not (ly_do or "").strip():
        raise RcError("--ly-do bắt buộc: ghi số đo / cách đo để người đọc kiểm lại được")
    hit = [r for r in data["ket_qua"] if r["ma"] == ma]
    if len(hit) != 1:
        raise RcError(f"Không có dòng {ma!r}. Có: " + ", ".join(r["ma"] for r in data["ket_qua"]))
    da_khai = sdk_nextgen_buoc_do_tay.kiem(ma, ket, buoc or {})
    # Dong theo (1.2 -> KT-03/04) cung bi doi: Sai rieng cua dong theo cung dinh nhu dong chinh.
    dich = [m for m in (ma, *sdk_nextgen_buoc_do_tay.THEO.get(ma, ())) if any(x["ma"] == m for x in data["ket_qua"])]
    cu_sai = {m: s for m in dich if (s := sdk_nextgen_gop_luot.sai_truoc(data, m))}
    if ket != SAI and cu_sai and not (khong_tai_hien or "").strip():
        raise RcError("; ".join(f"{m} đã Sai ở {s['thu_muc']}: {s['ly_do'][:300]}" for m, s in cu_sai.items())
                      + f" — muốn đổi sang {ket} phải chạy lại đúng các bước tái hiện đó rồi ghi "
                      "--khong-tai-hien \"<đã làm gì, kết quả>\"")
    luc = time.strftime('%d/%m/%Y %H:%M')
    for m in dich:
        r = next(x for x in data["ket_qua"] if x["ma"] == m)
        r.update(ket=ket, ly_do=" ".join(ly_do.split()) if m == ma else f"Theo {ma}: {' '.join(ly_do.split())}",
                 cham_boi=f"{ai} đo tay {luc}", ket_code=r.get("ket_code", r["ket"]), buoc=da_khai)
        r.pop("tu_luot", None)
        r.pop("khong_tai_hien", None)   # ghi de lan cham cu: chi giu ghi chu cua lan cham nay
        if (khong_tai_hien or "").strip() and m in cu_sai:
            r["khong_tai_hien"] = {"sai_o": cu_sai[m]["thu_muc"], "ghi": " ".join(khong_tai_hien.split())}
    return data


def dem(data: dict) -> dict:
    ra = {KHOP: 0, SAI: 0, DO_TAY: 0, "KHONG_AP_DUNG": 0}
    for r in data["ket_qua"]:
        ra[r["ket"]] += 1
    return ra
