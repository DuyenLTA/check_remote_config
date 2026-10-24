"""Muc 3B checklist SDK Next-Gen: chuoi event theo tung dinh dang (EV-20..EV-27).

Chuoi chuan cua mot luot hien: track_ad_request -> track_ad_matched_request ->
ad_load(success) -> ad_show(success) -> paid_ad_impression, cung ad unit, moi
event mot lan. Ghep theo UNIT: splash nhieu bac gia moi bac mot unit rieng, nen
ghep theo unit khong bi lan bac nay sang bac kia.
"""

from __future__ import annotations

import re

from .sdk_nextgen_events import CUA_SO_MATCHED_LOAD, CUA_SO_SHOW_PAID, dong, fmt, gan, loc, ok, unit
from .sdk_nextgen_ket import DO_TAY, KHONG_AP_DUNG, KHOP, SAI, kq

_FOR_TESTER_FAIL = re.compile(r"FOR_TESTER_LOAD_FAILURE\s*:\s*(\w+)\s*-\s*(.*)")
# Ten loai trong dong FOR_TESTER_LOAD_FAILURE ("<ADTYPE> - <unit> - <message>") -> fmt() chuan.
_LOAI_TESTER = {"INTERSTITIAL": "interstitial", "REWARDED": "rewarded", "REWARDED_INTERSTITIAL": "rewarded_interstitial",
                "APP_OPEN": "app_open", "BANNER": "banner", "NATIVE": "native"}


def loi_chuoi(ev, show: dict) -> list[str]:
    """Cac mat xich thieu / trung cua luot hien `show`. Rong = du chuoi.

    Mot luot = khoang tu lan load thanh cong GAN NHAT cua unit (khong gioi han gio:
    app open load o splash co the hien sau FO dai) toi `show`. Trong luot: dung 1
    request (sau lan load truoc cua unit), dung 1 matched sat load, dung 1 show, dung 1 paid.
    """
    u = unit(show)
    if not u:
        return ["ad_show không có ad unit"]
    cung = [e for e in ev if unit(e) == u]
    loads = [l for l in cung if l["name"] == "ad_load" and ok(l)]
    truoc = [l for l in loads if l["ts"] <= show["ts"]]
    if not truoc:
        return ["thiếu ad_load success trước ad_show"]
    load = truoc[-1]
    load_truoc = truoc[-2]["ts"] if len(truoc) > 1 else float("-inf")
    load_sau = next((l["ts"] for l in loads if l["ts"] > show["ts"]), float("inf"))
    loi = []
    shows = [e for e in cung if e["name"] == "ad_show" and ok(e) and load["ts"] <= e["ts"] < load_sau]
    if len(shows) != 1:
        loi.append(f"ad_show={len(shows)} cho 1 lần load (phải 1)")
    req = [e for e in cung if e["name"] == "track_ad_request" and load_truoc < e["ts"] <= load["ts"] + 0.5]
    if len(req) != 1:
        loi.append(f"track_ad_request={len(req)} (phải 1)")
    matched = gan(ev, "track_ad_matched_request", load, CUA_SO_MATCHED_LOAD, 0.5)
    if len(matched) != 1:
        loi.append(f"track_ad_matched_request={len(matched)} (phải 1)")
    show_sau = next((e["ts"] for e in shows if e["ts"] > show["ts"]), float("inf"))
    paid = [e for e in cung if e["name"] == "paid_ad_impression" and show["ts"] - 0.5 <= e["ts"] <= min(show["ts"] + CUA_SO_SHOW_PAID, show_sau)]
    if len(paid) != 1:
        loi.append(f"paid_ad_impression={len(paid)} (phải 1)")
    return loi


def chuoi(ma: str, ten: str, ev, dinh_dang: str, khong_co: str) -> dict:
    """Moi luot hien thanh cong cua `dinh_dang` phai du chuoi 5 event."""
    shows = loc(ev, "ad_show", thanh_cong=True, dinh_dang=dinh_dang)
    if not shows:
        return kq(ma, ten, KHONG_AP_DUNG if khong_co == "ngoai" else DO_TAY,
                  f"Không có lượt hiện {dinh_dang} nào trong các lượt chạy" + (" (chỉ có trong app)" if khong_co == "ngoai" else ""))
    sai = [(s, loi_chuoi(ev, s)) for s in shows]
    sai = [f"{dong(s)}: {', '.join(l)}" for s, l in sai if l]
    if sai:
        return kq(ma, ten, SAI, f"{len(sai)}/{len(shows)} lượt hiện {dinh_dang} thiếu/trùng event trong chuỗi", sai)
    return kq(ma, ten, KHOP, f"{len(shows)}/{len(shows)} lượt hiện {dinh_dang} đủ request → matched → load → show → paid, mỗi event 1 lần",
              [dong(s) for s in shows[:6]])


def loi_offline(ma: str, ten: str, ev_off, text_off: str | None, dinh_dang: tuple[str, ...],
                crash_off: list[str], chan_offline: bool, mang_that_tat: bool = True) -> dict:
    """EV-21 / EV-24: luot mat mang co loi load ro rang (dung loai), khong crash."""
    if text_off is None:
        return kq(ma, ten, DO_TAY, "Chưa có lượt chạy mất mạng")
    if not mang_that_tat:
        return kq(ma, ten, DO_TAY, "Đã tắt wifi + data mà máy vẫn ra được internet (tether / ethernet?) — lượt mất mạng không dùng được")
    if crash_off:
        return kq(ma, ten, SAI, "App crash / ANR khi mất mạng", crash_off)
    failed = [e for e in loc(ev_off, "ad_load", thanh_cong=False) if fmt(e) in dinh_dang]
    tester = [f"{m.group(1)} - {m.group(2).strip()}" for m in map(_FOR_TESTER_FAIL.search, text_off.splitlines())
              if m and _LOAI_TESTER.get(m.group(1).upper()) in dinh_dang]
    if failed or tester:
        thieu = [e for e in failed if not str(e["params"].get("error_code", "")).lstrip("-").isdigit()
                 or not str(e["params"].get("error_code_name", "")).strip()]
        if thieu:
            return kq(ma, ten, SAI, f"{len(thieu)}/{len(failed)} ad_load failed thiếu error_code / error_code_name", [dong(e) for e in thieu])
        return kq(ma, ten, KHOP, f"{len(failed)} ad_load failed đủ trường lỗi, {len(tester)} dòng FOR_TESTER_LOAD_FAILURE, không crash",
                  [dong(e) for e in failed[:4]] + tester[:4])
    if chan_offline:
        return kq(ma, ten, KHOP, "Không crash; app chặn request khi mất mạng nên không có event lỗi",
                  ghi_chu="Checklist: app chặn request lúc offline thì ghi chú, không phải lỗi")
    if not [e for e in ev_off if e["name"] in ("track_ad_request", "ad_load") and fmt(e) in dinh_dang]:
        # Luot offline chi o splash 25 s: loai quang cao o man sau chua toi luot xin -> khong ket luan duoc.
        return kq(ma, ten, DO_TAY, f"Lượt mất mạng chưa tới chỗ xin {', '.join(dinh_dang)} — đo tay ở màn có loại đó")
    return kq(ma, ten, SAI, "Có xin quảng cáo lúc mất mạng mà không có event lỗi, không có dòng FOR_TESTER_LOAD_FAILURE, không thấy app chặn request")


def tat_ca(ev, ev_off, text_off, crash_off, chan_offline, co_resume: bool, mang_that_tat: bool = True) -> list[dict]:
    """EV-20..27. `ev`: event cac luot co mang (FO + quay lai app); `*_off`: luot mat mang."""
    co_banner = bool(loc(ev, "ad_load", dinh_dang="banner") or loc(ev_off, "ad_load", dinh_dang="banner"))
    ra = [chuoi("EV-20", "Banner: mỗi lần làm mới đủ bộ event", ev, "banner", "ngoai")]
    if co_banner:
        ra.append(loi_offline("EV-21", "Banner: lỗi khi tắt mạng", ev_off, text_off, ("banner",), crash_off, chan_offline, mang_that_tat))
    else:
        ra.append(kq("EV-21", "Banner: lỗi khi tắt mạng", KHONG_AP_DUNG, "Luồng tutorial không có banner"))
    ra.append(chuoi("EV-22", "Interstitial: chuỗi event đầy đủ", ev, "interstitial", "do_tay"))
    ra.append(chuoi("EV-23", "Rewarded: chuỗi event đầy đủ", ev, "rewarded", "ngoai"))
    ra.append(loi_offline("EV-24", "Lỗi load khi tắt mạng (inter, rewarded, app open)", ev_off, text_off,
                          ("interstitial", "rewarded", "app_open"), crash_off, chan_offline, mang_that_tat))
    if co_resume:
        ra.append(chuoi("EV-25", "App open: chuỗi event đầy đủ", ev, "app_open", "do_tay"))
    else:
        ra.append(kq("EV-25", "App open: chuỗi event đầy đủ", DO_TAY, "Chưa có lượt Home → mở lại app"))
    ra += [kq("EV-26", "Native: chuỗi event khi hiện và khi bấm", DO_TAY, "Cần bấm native test rồi quay lại — đo tay"),
           kq("EV-27", "Tải lại native khi click hoặc hết video", DO_TAY, "Cần bấm native / xem hết video native — đo tay")]
    return ra
