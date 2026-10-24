"""Cham dong BO CUC tren splash bang bounds trong cay UI (khong nhin anh).

"Progress + text neo NGAY TREN mep native", "KHONG de len native", "neo tren mep banner
12-16dp", "nhan nam ngay DUOI progress bar", "progress o giua man", "progress KHONG dich
chuyen khi native show". Truoc day cac dong nay ra NOT_VERIFIABLE ("khong neu ro ky vong")
hoac PASS chi vi THAY nhan (Piclux 2.4.0, 24/10/2026: 7 case phai cham tay) - trong khi
dump moi buoc da co san bounds cua tung node.

Ten id lay tu muc `bo_cuc` trong `data/ui_names.yaml`. Mat do man hinh (dpi) do bang
`wm density` luc chay, de trong `drive["density"]`; px / (dpi / 160) = dp.
"""

from __future__ import annotations

import re

from . import ui_dump, ui_names
from .verdict_levels import FAIL, NEEDS_HUMAN, PASS, out, worst

CUM_RE = re.compile(r"progress|nh[ãa]n|may contain ads", re.I)
KHONG_DE_RE = re.compile(r"kh[ôo]ng\s+(?:b[ịi]\s+)?đ[èe]", re.I)
TREN_MEP_RE = re.compile(r"tr[êe]n\s+m[ée]p|neo\s+(?:ngay\s+)?tr[êe]n", re.I)
DP_RE = re.compile(r"(\d+)\s*[–-]\s*(\d+)\s*dp", re.I)
DUOI_PROGRESS_RE = re.compile(r"d[ưu][ớo]i\s+progress", re.I)
NGAY_TREN_RE = re.compile(r"ngay\s+tr[êe]n", re.I)
CUNG_CUM_RE = re.compile(r"di\s+chuy[ểe]n\s+c[ùu]ng", re.I)
GIUA_MAN_RE = re.compile(r"gi[ữu]a\s+m[àa]n", re.I)
KHONG_DICH_RE = re.compile(r"kh[ôo]ng\s+d[ịi]ch\s+chuy[ểe]n|\b0\s*shift", re.I)
# Bounds la so nguyen px; lech 1dp la sai so lam tron cua layout, khong phai loi.
SAI_SO_DP = 1.0


def routes(text: str) -> bool:
    """Dong noi ve vi tri cum progress/nhan so voi ad hoac man hinh."""
    return bool(CUM_RE.search(text) and (
        KHONG_DE_RE.search(text) or TREN_MEP_RE.search(text) or DP_RE.search(text)
        or DUOI_PROGRESS_RE.search(text) or GIUA_MAN_RE.search(text) or KHONG_DICH_RE.search(text)))


def _tim(nodes, nhom: dict):
    ids, classes = set(nhom.get("ids") or ()), tuple(nhom.get("classes") or ())
    texts = [t.casefold() for t in nhom.get("texts") or ()]
    for n in nodes:
        if not n.visible or n.bounds.empty:
            continue
        if (n.resource_id in ids or (classes and n.short_cls in classes)
                or any(t in (n.text or "").casefold() for t in texts)):
            return n
    return None


def _khung(drive: dict) -> list[dict]:
    """Moi dump cua lan chay -> cac node bo cuc tim duoc. Dump hong bo qua."""
    cfg = ui_names.bo_cuc()
    ra = []
    for step in (drive or {}).get("steps") or []:
        xml = step.get("dump") or ""
        if not xml:
            continue
        try:
            nodes = [n for n in ui_dump.parse_dump(xml) if not ui_dump.is_system_node(n)]
        except Exception:  # noqa: BLE001 - mot dump hong khong lam hong ca dong
            continue
        cao = max((n.bounds.bottom for n in nodes), default=0)
        ra.append({"buoc": step.get("n"), "cao": cao, "nodes": nodes,
                   **{k: _tim(nodes, cfg.get(k) or {}) for k in ("progress", "nhan_ads", "native", "banner")}})
    return ra


def _cum(k: dict):
    """Hop cua progress + nhan (TC goi "progress + text")."""
    phan = [n.bounds for n in (k["progress"], k["nhan_ads"]) if n]
    if not phan:
        return None
    return ui_dump.Bounds(min(b.left for b in phan), min(b.top for b in phan),
                          max(b.right for b in phan), max(b.bottom for b in phan))


def _de(a, b) -> bool:
    return a.left < b.right and b.left < a.right and a.top < b.bottom and b.top < a.bottom


def _dp(px: float, dpi) -> str:
    return f"{px / (dpi / 160):.0f}dp" if dpi else f"{px:.0f}px"


def _voi_ad(text: str, loai: str, khung: list[dict], dpi) -> list[dict]:
    co = [k for k in khung if k[loai] and _cum(k)]
    if not co:
        thay_cum = any(_cum(k) for k in khung)
        return [out(NEEDS_HUMAN, f"không có khung nào thấy cùng lúc cụm progress và {loai} "
                    f"({'có progress, chưa thấy ' + loai if thay_cum else 'chưa thấy progress'}) — "
                    "ad chưa về hoặc bị inter che", text)]
    k = co[-1]
    cum, ad = _cum(k), k[loai].bounds
    tag = f"bước {k['buoc']}: cụm y={cum.top}–{cum.bottom}, {loai} `{k[loai].resource_id or k[loai].short_cls}` y={ad.top}–{ad.bottom}"
    ra = []
    if KHONG_DE_RE.search(text):
        ra.append(out(FAIL if _de(cum, ad) else PASS,
                      ("cụm progress ĐÈ lên " if _de(cum, ad) else "cụm progress không đè ") + f"{loai} — {tag}", text))
    gap = ad.top - cum.bottom
    if TREN_MEP_RE.search(text) or DP_RE.search(text):
        if gap < 0:
            ra.append(out(FAIL, f"cụm progress không nằm trên mép {loai} (lấn {_dp(-gap, dpi)}) — {tag}", text))
        else:
            m = DP_RE.search(text)
            if m and not dpi:
                ra.append(out(NEEDS_HUMAN, f"cách {gap}px nhưng chưa đo được mật độ màn hình để đổi dp — {tag}", text))
            elif m:
                dp, lo, hi = gap / (dpi / 160), float(m.group(1)), float(m.group(2))
                ok = lo - SAI_SO_DP <= dp <= hi + SAI_SO_DP
                ra.append(out(PASS if ok else FAIL, f"cụm cách mép {loai} {dp:.1f}dp, kỳ vọng "
                              f"{m.group(1)}–{m.group(2)}dp — {tag}", text))
            elif NGAY_TREN_RE.search(text) and (chen := _chen_giua(k, cum, ad)):
                ra.append(out(FAIL, f"giữa cụm progress và mép {loai} còn {chen} (cách {_dp(gap, dpi)}) "
                                    f"— không phải ngay trên — {tag}", text))
            else:
                ra.append(out(PASS, f"cụm progress nằm trên mép {loai}, cách {_dp(gap, dpi)}"
                              + (", không node nào chen giữa" if NGAY_TREN_RE.search(text) else "")
                              + f" — {tag}", text))
    return ra


def _chen_giua(k: dict, cum, ad) -> str:
    """Node app nam HAN trong khoang giua cum va ad (cung cot ngang) - "ngay tren" thi khong co."""
    for n in k["nodes"]:
        b = n.bounds
        if (n.visible and not b.empty and b.top >= cum.bottom and b.bottom <= ad.top
                and b.left < ad.right and ad.left < b.right):
            return n.label
    return ""


def _nhan_duoi(text: str, khung: list[dict]) -> list[dict]:
    co = [k for k in khung if k["progress"] and k["nhan_ads"]]
    if not co:
        return [out(NEEDS_HUMAN, "không có khung nào thấy cùng lúc progress và nhãn ads", text)]
    lech = []
    for k in co:
        p, n = k["progress"].bounds, k["nhan_ads"].bounds
        if not (n.center[1] > p.center[1] and n.left < p.right and p.left < n.right):
            return [out(FAIL, f"bước {k['buoc']}: nhãn y={n.top}–{n.bottom} không nằm dưới progress "
                              f"y={p.top}–{p.bottom}", text)]
        lech.append(n.top - p.top)
    p, n = co[-1]["progress"].bounds, co[-1]["nhan_ads"].bounds
    dong = f"nhãn (tâm y={n.center[1]}) nằm dưới tâm progress (y={p.center[1]}) ở {len(co)} khung"
    if len(set(lech)) > 1:
        return [out(FAIL, dong + f"; khoảng nhãn–progress đổi giữa các khung ({sorted(set(lech))}px) — "
                                 "nhãn không đi cùng cụm", text)]
    if CUNG_CUM_RE.search(text) and len({k["progress"].bounds.top for k in co}) < 2:
        # Progress chua tung doi cho thi "nhan di chuyen cung cum" chua duoc thu.
        return [out(PASS, dong, text),
                out(NEEDS_HUMAN, "progress chưa đổi vị trí ở khung nào nên chưa thấy nhãn di chuyển "
                                 "cùng cụm", text)]
    return [out(PASS, dong + (", di chuyển cùng progress" if CUNG_CUM_RE.search(text) else ""), text)]


def _giua_man(text: str, khung: list[dict]) -> list[dict]:
    co = [k for k in khung if k["progress"] and k["cao"]]
    if not co:
        return [out(NEEDS_HUMAN, "không có khung nào thấy progress", text)]
    # Case layout native/banner: vi tri luc AD DA HIEN moi la thu TC hoi (truoc do cum o day).
    k = ([c for c in co if c["native"] or c["banner"]] or co)[-1]
    ti_le = k["progress"].bounds.center[1] / k["cao"]
    return [out(PASS if 0.35 <= ti_le <= 0.65 else FAIL,
                f"tâm progress ở {ti_le:.0%} chiều cao màn (giữa màn = 35–65%)", text)]


def _khong_dich(text: str, loai: str, khung: list[dict]) -> list[dict]:
    truoc = [k for k in khung if k["progress"] and not k[loai]]
    sau = [k for k in khung if k["progress"] and k[loai]]
    if not truoc or not sau:
        return [out(NEEDS_HUMAN, f"cần khung trước VÀ sau khi {loai} hiện để so vị trí progress "
                                 f"(có {len(truoc)} trước, {len(sau)} sau)", text)]
    a, b = truoc[-1]["progress"].bounds, sau[0]["progress"].bounds
    dich = b.top - a.top
    return [out(PASS if dich == 0 else FAIL, f"progress y={a.top} trước khi {loai} hiện, y={b.top} "
                f"sau — dịch {dich}px", text)]


def cham(text: str, drive: dict) -> dict | None:
    """Cham dong bo cuc; None neu dong khong thuoc luat nay."""
    if not routes(text):
        return None
    khung, dpi = _khung(drive), (drive or {}).get("density")
    loai = "native" if re.search(r"native", text, re.I) else "banner" if re.search(r"banner", text, re.I) else ""
    ket: list[dict] = []
    if loai and KHONG_DICH_RE.search(text):
        ket += _khong_dich(text, loai, khung)
    elif loai and (KHONG_DE_RE.search(text) or TREN_MEP_RE.search(text) or DP_RE.search(text)):
        ket += _voi_ad(text, loai, khung, dpi)
    if DUOI_PROGRESS_RE.search(text):
        ket += _nhan_duoi(text, khung)
    if GIUA_MAN_RE.search(text):
        ket += _giua_man(text, khung)
    if not ket:
        return None
    if len(ket) == 1:
        return ket[0]
    return out(worst(k["verdict"] for k in ket), "; ".join(k["reason"] for k in ket), text)
