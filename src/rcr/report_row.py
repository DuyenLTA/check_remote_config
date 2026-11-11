"""Mot case da chay -> mot muc trong `DATA` cua trang report.

Tach khoi `report_html` (dung khung trang) va `report_data` (gom ket qua chay):
file nay chi dich tu vung tu cua tool sang tu vung tester doc tren report.

DICH NHAN LA VIEC CO Y: tool phan biet NEEDS_HUMAN voi BLOCKED voi
NOT_VERIFIABLE vi ba thu do sua bang ba cach khac nhau, nhung tren bang tong
ket cua tester chi co bon o. Gop sai o la doc sai viec phai lam:
  - BLOCKED = luot chay chua ket luan duoc, phai chay lai (mo lai, doi may,
    doi dieu kien) -> viec cua TESTER
  - N/A      = dong nay khong thuoc pham vi tester (so lieu console, dong doi
    nhin mat) -> viec cua PO, hoac khong ai lam duoc
"""

from __future__ import annotations

import re


from .verdict_levels import (
    CONFIG_BLOCKED,
    CONFIG_OK,
    FAIL,
    NEEDS_HUMAN,
    NOT_VERIFIABLE,
    PASS,
)

# Verdict cua tool -> o tren bang tong ket.
NHAN = {
    PASS: "PASS",
    FAIL: "FAIL",
    # Chua lai toi duoc man / quang cao che man / config khong song: deu la
    # "chay lai thi ra ket qua", khong phai ket luan ve app.
    NEEDS_HUMAN: "BLOCKED",
    CONFIG_BLOCKED: "BLOCKED",
    "KEY_NOT_USED": "BLOCKED",
    # Dong phai nhin mat, hoac so lieu tren console ngoai.
    NOT_VERIFIABLE: "NA",
    # Case khong co dong Expected nao: dat duoc config la het phan tool.
    CONFIG_OK: "NA",
}


def nhan_cua(verdict: str) -> str:
    """Verdict tool -> nhan tren report. La -> BLOCKED, khong phai PASS.

    Mac dinh phai la BLOCKED chu khong phai NA: mot verdict moi chua ai dich
    thi nguoi doc can nhin thay no, dung de no lan vao o "ngoai pham vi".
    """
    return NHAN.get(verdict, "BLOCKED")


def _so_case(key: str) -> str:
    """Ma case sau dau '#': so (`17`) hoac TC ID (`SDK340-SPL-001`)."""
    return (key or "").rsplit("#", 1)[-1]


def _tieu_de(rec: dict) -> str:
    """Bo tien to "#17 " o dau label: so case da nam o cot rieng."""
    nhan_ = (rec.get("label") or "").strip()
    so = f"#{_so_case(rec.get('key', ''))}"
    if nhan_.startswith(so):
        nhan_ = nhan_[len(so):].lstrip(" -–—:.")
    return nhan_ or rec.get("group") or rec.get("key", "")


def _config(rec: dict) -> str:
    """Config case da dat + kieu reset - hai thu quyet dinh luot chay nay."""
    cap = " · ".join(f"{k} = {v}" for k, v in (rec.get("overrides") or {}).items())
    reset = rec.get("reset") or ""
    thieu = rec.get("keys_not_used") or []
    phan = [cap or "— không đặt key nào —"]
    if reset and reset != "—":
        phan.append(f"reset: {reset}")
    if thieu:
        phan.append("app KHÔNG đọc: " + ", ".join(thieu))
    return " · ".join(phan)


DAU_DUNG_LAI_RE = re.compile(r"^Đo tay [\d/]+ cùng build [^:]*?\(lượt trước\):\s*")
DO_TAY_RE = re.compile(r"[Đđ]o tay")


def _ly_do(r: str) -> dict:
    """'Claude chấm tay: OB2 ...' -> {r: 'OB2 ...', tay: True}; ly do cua tool giu nguyen. Report chi ghi "đo tay",
    khong ghi ai do (user 03/11/2026: chu "Claude đo tay" tren report khong hop)."""
    ai, sep, con = (r or "").partition(" chấm tay: ")
    if not (sep and ai and len(ai) <= 20):
        return {"r": r, "tay": False}
    # Report khong ghi "do tay" (user 03/11/2026): bo dau dong lap "Do tay <ngay> cung build ... (luot truoc): ",
    # con lai doi "do tay" -> "do tren may"; so do + duong dan log giu nguyen lam bang chung.
    con = DAU_DUNG_LAI_RE.sub("", con)
    con = DO_TAY_RE.sub(lambda m: "Đo trên máy" if m.group(0)[0] == "Đ" else "đo trên máy", con)
    return {"r": con, "tay": True}


EP_AI_RE = re.compile(r"^\S{1,20} tạo điều kiện ở lượt đo tay:\s*")


def _ep(ep: str) -> str:
    """'Claude tạo điều kiện ở lượt đo tay: Cắm máy...' -> 'Tạo điều kiện trên máy: Cắm máy...'. Cung luat voi
    `_ly_do`: report khong ghi ai do, khong ghi "do tay" (user 03/11/2026, nhac lai 11/11/2026)."""
    if not ep:
        return ep
    ep = EP_AI_RE.sub("Tạo điều kiện trên máy: ", ep)
    return DO_TAY_RE.sub(lambda m: "Đo trên máy" if m.group(0)[0] == "Đ" else "đo trên máy", ep)


def build(rec: dict) -> dict:
    """Mot ban ghi case -> mot muc `DATA`. Chi du lieu, khong HTML."""
    return {
        "n": _so_case(rec.get("key", "")),
        "key": rec.get("key", ""),
        "group": rec.get("group") or "Khác",
        "title": _tieu_de(rec),
        "status": nhan_cua(rec.get("verdict", "")),
        "verdict": rec.get("verdict", ""),
        "pre": rec.get("precondition") or "—",
        "cfg": _config(rec),
        "actual": rec.get("actual") or "—",
        "expects": [l["e"] for l in (rec.get("lines") or [])],
        # `s` la nhan da dich cua RIENG dong do - mot case PASS van co the co
        # dong N/A, va nguoc lai.
        "lines": [{"s": nhan_cua(l["v"]), "v": l["v"], **_ly_do(l["r"])} for l in (rec.get("lines") or [])],
        # Case co dong cham tay: report dua ket luan do tay len dau, luot tool gap lai (user 29/10/2026).
        "tay": bool(rec.get("cham_tay")),
        "anh_tay": rec.get("anh_tay") or [],
        "po": rec.get("po", 0),
        "pending": rec.get("pending", 0),
        "thieu": list(dict.fromkeys(DO_TAY_RE.sub("đo trên máy", DAU_DUNG_LAI_RE.sub("", t))
                                    for t in rec.get("precondition_thieu") or [])),
        "ep": _ep(rec.get("ep_ad_fail", "")),
        "lech": rec.get("tc_lech") or [],
        "tuban": rec.get("ad_click_tu_ban", 0),
        "ads": rec.get("ads") or [],
        "steps": rec.get("steps") or [],
        "chuoi": bool(rec.get("noi_chuoi")),
    }
