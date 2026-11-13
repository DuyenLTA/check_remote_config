"""Cham cac dong IAA cham duoc bang log FA-SVC (`logcat -v epoch`) cua mot lan lai app theo bien the.

Tu cham (ham thuan, khong can may):
- `-02` chi thuong / `-03` chi high: dong "Chi request unit X, khong request unit Y" + dong "Co fill thi ... van
  hien thi" (ad_show cua tang dang bat; kho khong fill ma request dung unit -> dat, luat 25/09/2026).
- `-04` tat: "Khong request unit nao" + "Khong preload, khong hien thi".
- Dong cuoi cua `-01` (thu tu high truoc, high khong fill moi goi thuong).
Cac dong mo ta cua `-01` (dung man, dung thoi diem, reload, gioi han so lan) Claude cham tay theo 5b.

"0 request" chi la bang chung khi lan lai app DA TOI vi tri: vi tri tinh la da toi khi lan lai bien the
"bat" (cung duong lai) co request cua no. Khong co log "bat" thi khong cham PASS dong "khong request".
"""

from __future__ import annotations

import re

from . import fa_log

TEN_EVENT = ("track_ad_request", "ad_load", "ad_show")


_THREADTIME = re.compile(r"^(\d\d-\d\d \d\d:\d\d:\d\d\.\d+)(\s)", re.M)


def _ve_epoch(text: str) -> str:
    """Log `-v threadtime` (khong co epoch) -> chen gio dang so de sap thu tu duoc nhu `-v epoch`."""
    return _THREADTIME.sub(lambda m: f"{fa_log.gio_threadtime(m.group(1)):.3f}{m.group(2)}", text or "")


def su_kien(text: str, units: dict[str, tuple[int, str]]) -> list[dict]:
    """Event ads cua cac unit IAA trong log (log chung ca may: loc theo ID day du, khong theo app).
    Nhan ca `logcat -v epoch` lan `-v threadtime`."""
    ra = []
    for e in fa_log.parse(_ve_epoch(text)):
        ten = e["name"].split("(", 1)[0]
        if ten not in TEN_EVENT:
            continue
        p = e["params"]
        u = p.get("adunitid") or p.get("ad_unit_id") or ""
        if u not in units:
            continue
        i, tang = units[u]
        ok = (p.get("load_status") or p.get("show_status") or "success") == "success"
        ra.append({"t": e.get("t", 0.0), "ten": ten, "unit": u, "vi_tri": i, "tang": tang, "ok": ok})
    return sorted(ra, key=lambda e: e["t"])


def _gio(e: dict) -> str:
    return f"{e['t']:.3f}"[-7:]


def _duoi(u: str) -> str:
    return "…" + u.rsplit("/", 1)[-1][-4:]


def dem(ev: list[dict], i: int) -> dict:
    """So request / load ok / load fail / show ok theo tang cua vi tri i."""
    ra = {t: {"req": 0, "load_ok": 0, "load_fail": 0, "show": 0, "ds": []} for t in ("high", "thuong")}
    for e in ev:
        if e["vi_tri"] != i:
            continue
        d = ra[e["tang"]]
        d["ds"].append(e)
        if e["ten"] == "track_ad_request":
            d["req"] += 1
        elif e["ten"] == "ad_load":
            d["load_ok" if e["ok"] else "load_fail"] += 1
        elif e["ok"]:
            d["show"] += 1
    return ra


def _mo_ta(d: dict, unit: str) -> str:
    return (f"{_duoi(unit)}: {d['req']} request, {d['load_ok']} load ok, {d['load_fail']} fail, "
            f"{d['show']} show" + (f" (request đầu {_gio(next(e for e in d['ds'] if e['ten'] == 'track_ad_request'))})"
                                   if d["req"] else ""))


def cham_mot_tang(ev: list[dict], i: int, bat: str, tat: str, unit_bat: str, unit_tat: str,
                  da_toi: bool) -> list[tuple[int, str, str]]:
    """Case `-02`/`-03`: [(so dong, PASS|FAIL, ly do)] cho 2 dong; dong khong ket luan duoc thi bo."""
    d = dem(ev, i)
    b, t = d[bat], d[tat]
    goc = f"{_mo_ta(b, unit_bat)}; {_mo_ta(t, unit_tat)}"
    ra = []
    if t["req"]:
        ra.append((1, "FAIL", f"vẫn request tầng đang tắt — {goc}"))
    elif b["req"]:
        ra.append((1, "PASS", f"chỉ request tầng đang bật — {goc}"))
    elif da_toi:
        ra.append((1, "FAIL", f"lượt lái đã tới vị trí (lượt 'bat' có request) mà tầng đang bật 0 request — {goc}"))
    if b["show"]:
        ra.append((2, "PASS", f"ad_show {_duoi(unit_bat)} lúc {_gio(next(e for e in b['ds'] if e['ten'] == 'ad_show' and e['ok']))}"))
    elif b["req"] and not b["load_ok"]:
        # Dong 2 la "Co fill thi ... van hien thi": khong fill = chua co dieu kien de kiem hien thi -> BLOCKED, khong
        # PASS (user chot 13/11/2026: report IAA AIP893 PASS 7 dong hien thi ma khong ai thay ad). Dong request
        # (dong 1) van giu luat cu "request dung unit la dat".
        ra.append((2, "BLOCKED", f"request đúng {_duoi(unit_bat)} {b['req']} lần nhưng kho không fill "
                                 f"({b['load_fail']} fail) — chưa có ad hiện để kiểm hiển thị, cần fill (lắc máy chọn "
                                 "ad source / test mode network)"))
    return ra


def cham_tat(ev: list[dict], i: int, units: list[str], da_toi: bool) -> list[tuple[int, str, str]]:
    """Case `-04`: hai dong cung mot ket luan."""
    d = dem(ev, i)
    tong = sum(d[t]["req"] + d[t]["show"] for t in d)
    if tong:
        ly = "; ".join(_mo_ta(d[t], u) for t, u in zip(("high", "thuong"), units) if u)
        return [(1, "FAIL", f"đã tắt remote mà vẫn có event — {ly}"), (2, "FAIL", f"đã tắt remote mà vẫn có event — {ly}")]
    if not da_toi:
        return []
    ly = f"lượt lái cùng đường với lượt 'bat' (lượt đó có request vị trí này): 0 request / 0 show {', '.join(map(_duoi, filter(None, units)))}"
    return [(1, "PASS", ly), (2, "PASS", ly)]


def cham_fail_time(ev: list[dict], i: int, n: int) -> tuple[str, str] | None:
    """Dong `*_fail_time=n` cua vi tri i: dem lan `ad_load` FAIL tu lan fail DAU TIEN (preload fail cung tinh, QA chot
    13/11/2026); fail du n lan thi khong duoc request lai nua. None = chua du n lan fail (chua ep du / log het som).
    Vi tri co ca high + thuong: mot luot load = high fail -> goi thuong, luot fail khi tang thuong fail -> chi dem
    fail cua tang thuong (khong dem doi). Chi bat mot tang thi dem fail cua tang do."""
    ds = [e for e in ev if e["vi_tri"] == i]
    cuoi = "thuong" if any(e["tang"] == "thuong" for e in ds) else "high"
    fail = [k for k, e in enumerate(ds) if e["ten"] == "ad_load" and not e["ok"] and e["tang"] == cuoi]
    if n < 1 or len(fail) < n:
        return None
    thu_n = ds[fail[n - 1]]
    sau = [e for e in ds[fail[n - 1] + 1:] if e["ten"] == "track_ad_request"]
    lan = ", ".join(_gio(ds[k]) for k in fail[:n])
    if sau:
        return ("FAIL", f"fail lần thứ {n} lúc {_gio(thu_n)} (các lần fail: {lan}) mà vẫn request lại "
                        f"{len(sau)} lần, lần đầu lúc {_gio(sau[0])}")
    return ("PASS", f"fail đủ {n} lần ({lan}), sau lần fail thứ {n} không còn request nào của vị trí")


def cham_thu_tu(ev: list[dict], i: int, unit_high: str, unit_thuong: str) -> tuple[str, str] | None:
    """Dong cuoi `-01`: high request truoc; moi request thuong phai sau mot lan high load FAIL. None = chua toi."""
    ds = [e for e in ev if e["vi_tri"] == i]
    if not ds:
        return None
    if not unit_thuong or not unit_high:
        u = unit_high or unit_thuong
        n = sum(1 for e in ds if e["ten"] == "track_ad_request")
        return ("PASS", f"request {_duoi(u)} {n} lần") if n else None
    # Moi chu ky (giua hai lan request thuong): phai co request high truoc, va high KHONG load thanh cong
    # (high fill ma van goi thuong la sai). Khong doi event `ad_load failed` cua high: banner khong ghi event do
    # (AIP893 13/11/2026 banner Home: high request -> 1-2s sau goi thuong, khong co dong fail).
    sai, cap, moc = [], 0, 0
    for k, e in enumerate(ds):
        if e["tang"] != "thuong" or e["ten"] != "track_ad_request":
            continue
        truoc = [x for x in ds[moc:k] if x["tang"] == "high"]
        moc = k + 1
        # Chu ky bat dau tu lan request high GAN NHAT (banner reload 10s: lan high fill cua chu ky truoc khong tinh).
        dau = max((j for j, x in enumerate(truoc) if x["ten"] == "track_ad_request"), default=None)
        co_req = dau is not None
        chu_ky = truoc[dau:] if co_req else []
        high_fill = any(x["ten"] == "ad_load" and x["ok"] for x in chu_ky)
        if not co_req or high_fill:
            sai.append(_gio(e))
        else:
            cap += 1
    req_h = sum(1 for e in ds if e["tang"] == "high" and e["ten"] == "track_ad_request")
    if not req_h:
        return ("FAIL", f"không request tầng high {_duoi(unit_high)} lần nào")
    if sai:
        return ("FAIL", f"gọi thường {_duoi(unit_thuong)} khi chưa request high hoặc high đã fill, lúc {', '.join(sai)}")
    if cap:
        return ("PASS", f"high {_duoi(unit_high)} request {req_h} lần; {cap} lần high không fill rồi mới gọi thường "
                        f"{_duoi(unit_thuong)}")
    return ("PASS", f"high {_duoi(unit_high)} request {req_h} lần, high fill nên không gọi thường")
