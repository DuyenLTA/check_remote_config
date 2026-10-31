"""Cham dong ve NEN splash va progress / inter splash bang so do cua `splash_media` va log ads.

  - "Nen anh theo media_url, phu kin man."
  - "Nen GIF chay lap lien tuc (video_loop=true)." / "Nen GIF chay 1 lan roi dung o frame cuoi (video_loop=false)".
  - "Progress va inter splash chay nhu 3.6.0." - progress = view progress hien tren splash, inter splash = unit vi
    tri 102 co request (no-fill van la request dung, cung luat voi cac vi tri khac).
Truoc day ca ba ra NOT_VERIFIABLE (AIP886 31/10/2026) du deu do duoc.
"""

from __future__ import annotations

import re

from . import ui_dump
from .ad_positions import _khop_vi_tri
from .splash_media import MEP_TQ
from .verdict_levels import FAIL, NEEDS_HUMAN, PASS, out

NEN_RE = re.compile(r"\bn[ềe]n\b.{0,20}(?:gif|[ảa]nh|image|media|video)", re.I)
GIF_RE = re.compile(r"\bgif\b", re.I)
LAP_RE = re.compile(r"l[ặa]p|loop\s*=\s*true|li[êe]n\s*t[ụu]c", re.I)
MOT_LAN_RE = re.compile(r"1\s*l[ầa]n|m[ộo]t\s*l[ầa]n|d[ừu]ng\s*[ởo]\s*frame\s*cu[ốo]i|loop\s*=\s*false", re.I)
PHU_KIN_RE = re.compile(r"ph[ủu]\s*k[íi]n|full\s*m[àa]n|to[àa]n\s*m[àa]n", re.I)
PROGRESS_RE = re.compile(r"progress.{0,40}inter\s*splash|inter\s*splash.{0,40}progress", re.I)
PROGRESS_ID_RE = re.compile(r"process|progress|loading_?bar", re.I)


def _ket_qua(drive: dict) -> dict | None:
    return (drive or {}).get("splash_media")


GIU_CUOI = 1.0            # dung o khung cuoi it nhat bay nhieu giay moi tinh la "dung lai"


def _gif(text: str, sm: dict) -> dict:
    """Chuoi chi so khung GIF theo thoi gian: quay vong (chi so tut ve dau) = lap; toi khung cuoi roi dung yen = mot
    lan. Do that R02-01: 0->23 (2,5-6,6s) roi 0,1,2; R03-01: 1->23 roi dung 23 suot 7s."""
    dong = sm["splash"]
    n = sm["so_khung_media"]
    idx = [d["khung"] for d in dong]
    vong = [b["t"] for a, b in zip(dong, dong[1:]) if a["khung"] - b["khung"] >= n // 2]
    cuoi = [d["t"] for d in dong if d["khung"] >= n - 1]
    giu = 0.0
    if cuoi and not [t for t in vong if t > cuoi[0]]:
        sau = [d for d in dong if d["t"] >= cuoi[0]]
        if all(d["khung"] >= n - 2 for d in sau):
            giu = sau[-1]["t"] - cuoi[0]
    lan = " (lần mở lại app, config đã cache: lần mở đầu GIF chỉ hiện <1,5s trước inter splash)" \
        if sm.get("lan_mo_lai") else ""
    if sm.get("giu_splash"):
        lan = (" (đo ở lần mở lại app với ID inter splash đổi sang slot trống trên testvsl để inter không che: "
               "luồng thường inter che GIF ở giây 4-5, chưa hết một vòng)")
    tom = (f"{len(dong)} khung splash khớp file GIF ({n} khung, {sm.get('thoi_luong_ms', 0) / 1000:.1f}s, scale "
           f"{sm['che_do']}) từ giây {dong[0]['t']:.1f} tới {dong[-1]['t']:.1f}{lan}; chỉ số khung "
           f"{idx[0]}→{max(idx)}")
    if MOT_LAN_RE.search(text):
        if vong:
            return out(FAIL, f"{tom}; GIF quay lại khung đầu ở giây {vong[0]:.2f} — đang lặp", "lặp")
        if giu >= GIU_CUOI:
            return out(PASS, f"{tom}; tới khung cuối ({n - 1}) ở giây {cuoi[0]:.2f} rồi đứng yên {giu:.1f}s, không "
                             "quay vòng", "dừng ở khung cuối")
        return out(NEEDS_HUMAN, f"{tom}; splash tắt trước khi thấy GIF dừng ở khung cuối", "chưa thấy dừng")
    if LAP_RE.search(text):
        if vong:
            return out(PASS, f"{tom}; chạy hết vòng rồi quay lại khung đầu ở giây {vong[0]:.2f} — GIF lặp", "lặp")
        if giu >= GIU_CUOI:
            return out(FAIL, f"{tom}; tới khung cuối rồi đứng yên {giu:.1f}s, không quay vòng — GIF không lặp",
                       "dừng")
        return out(NEEDS_HUMAN, f"{tom}; splash tắt trước khi GIF hết một vòng, chưa chứng minh được lặp",
                   "splash ngắn hơn GIF")
    return out(PASS if len(set(idx)) > 1 else FAIL, f"{tom}; {'có' if len(set(idx)) > 1 else 'không'} chuyển động", "")


def _anh(text: str, sm: dict) -> dict:
    dong = sm["splash"]
    ly = (f"{len(dong)} khung splash khớp ảnh media_url (tương quan {max(d['tq'] for d in dong)}, scale "
          f"{sm['che_do']})")
    if not PHU_KIN_RE.search(text):
        return out(PASS, ly, "khớp media_url")
    mep = sm.get("mep") or {}
    lech = {k: v for k, v in mep.items() if v < MEP_TQ}
    if sm["che_do"] == "fit_center" or lech:
        return out(FAIL, f"{ly}; ảnh không phủ kín — mép {', '.join(lech) or 'hai bên'} không khớp ảnh "
                         f"(tương quan {mep})", "có viền")
    node = " , ImageView nền phủ cả màn" if sm.get("nen_full_node") else ""
    return out(PASS, f"{ly}; mép trên/trái/phải đều là ảnh (tương quan {mep}){node}", "phủ kín")


def cham_nen(text: str, drive: dict) -> dict | None:
    sm = _ket_qua(drive)
    if not sm or not NEN_RE.search(text):
        return None
    if sm.get("loi"):
        return out(NEEDS_HUMAN, f"đo nền splash: {sm['loi']}", "")
    if GIF_RE.search(text) or sm.get("loai") == "gif":
        return _gif(text, sm)
    return _anh(text, sm)


def cham_progress(text: str, units: list[dict], drive: dict) -> dict | None:
    if not PROGRESS_RE.search(text):
        return None
    prog = ""
    for st in (drive or {}).get("steps") or []:
        if "plash" not in (st.get("activity") or "") or not st.get("dump"):
            continue
        try:
            nodes = ui_dump.parse_dump(st["dump"])
        except Exception:  # noqa: BLE001
            continue
        hit = [n for n in nodes if n.visible and not n.bounds.empty
               and PROGRESS_ID_RE.search(n.resource_id.rsplit("/", 1)[-1])]
        if hit:
            prog = hit[0].resource_id.rsplit("/", 1)[-1]
            break
    inter = [u for u in units if _khop_vi_tri(u, "102")]
    req = sum(int(u.get("requested") or 0) for u in inter)
    show = sum(int(u.get("shown") or 0) for u in inter)
    phan = [f"progress `{prog}` hiện trên splash" if prog else "không thấy view progress trên splash",
            f"inter splash (102) {req} request, {show} show" if inter else "không có unit inter splash (102) nào"]
    v = PASS if prog and req else FAIL
    return out(v, "; ".join(phan), "; ".join(phan))
