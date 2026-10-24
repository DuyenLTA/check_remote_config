"""Muc 3A checklist SDK Next-Gen: tung event dung tham so, dung so lan (EV-01..EV-13).

Moi ham nhan `ev` (event quang cao cua cac luot co mang) va tra mot dong ket qua.
Luat viet tu cot Expected cua `sdk-check/references/checklist-muc3-event-EV.txt`;
chi chấm Sai cai checklist goi la loi, "loi co san / chi ghi nhan" khong tinh.
"""

from __future__ import annotations

from .sdk_nextgen_events import (CUA_SO_MATCHED_LOAD, CUA_SO_PAID_VALUE, CUA_SO_SHOW_PAID, dong, fmt,
                                 ghep_mot_mot, loc, unit)
from .sdk_nextgen_ket import DO_TAY, KHONG_AP_DUNG, KHOP, SAI, kq

NAM_LOAI = ("banner", "interstitial", "rewarded", "app_open", "native")
THAM_SO_PAID = ("valuemicros", "currency", "precision", "adunitid", "network", "ad_platform", "ad_format", "ad_source")
# Request co the xin truoc khi load xong kha lau (preload, mang cham): tim request trong 60 s truoc load.
CUA_SO_REQUEST_LOAD = 60.0


def _rong(v) -> bool:
    return str(v if v is not None else "").strip().lower() in ("", "null", "none")


def ev01(ev) -> dict:
    loads = loc(ev, "ad_load")
    if not loads:
        return kq("EV-01", "track_ad_request", DO_TAY, "Không thấy lượt load quảng cáo nào trong log")
    # Ghep 1-1: moi lan load (ca reload) phai co request RIENG; khong muon request cua lan truoc.
    _, thieu, _ = ghep_mot_mot(loads, loc(ev, "track_ad_request"), lambda l, r: unit(r) == unit(l) != ""
                               and l["ts"] - CUA_SO_REQUEST_LOAD <= r["ts"] <= l["ts"] + 0.5)
    # App open luong moi thieu event nay la loi co san (checklist), chi ghi nhan.
    loi = [l for l in thieu if fmt(l) != "app_open"]
    co = sorted({fmt(e) for e in loc(ev, "track_ad_request")})
    chua = [f for f in NAM_LOAI if f not in co]
    pham_vi = f"loại có trong luồng: {', '.join(co)}" + (f"; không có: {', '.join(chua)} (ngoài luồng tutorial)" if chua else "")
    if loi:
        return kq("EV-01", "track_ad_request", SAI, f"{len(loi)}/{len(loads)} lượt load không có track_ad_request riêng cùng unit ({pham_vi})",
                  [dong(l) for l in loi])
    return kq("EV-01", "track_ad_request", KHOP, f"{len(loads)}/{len(loads)} lượt load có track_ad_request riêng cùng unit ({pham_vi})",
              [dong(e) for e in loc(ev, "track_ad_request")[:6]])


def ev02(ev) -> dict:
    ls = loc(ev, "ad_load", thanh_cong=True)
    if not ls:
        return kq("EV-02", "track_ad_matched_request", DO_TAY, "Không có lượt load thành công nào")
    ms = loc(ev, "track_ad_matched_request")
    hop = lambda l, m: unit(m) == unit(l) != "" and l["ts"] - CUA_SO_MATCHED_LOAD <= m["ts"] <= l["ts"] + 0.5
    _, thieu, du = ghep_mot_mot(ls, ms, hop)
    trung = [m for m in du if any(hop(l, m) for l in ls)]  # matched thua sat mot lan load = ban 2 lan
    if thieu or trung:
        return kq("EV-02", "track_ad_matched_request", SAI,
                  f"{len(thieu)} lượt load thành công thiếu matched, {len(trung)} matched bắn thừa cho cùng lần load",
                  [dong(l) + " → thiếu matched" for l in thieu] + [dong(m) + " → thừa" for m in trung])
    return kq("EV-02", "track_ad_matched_request", KHOP, f"{len(ls)}/{len(ls)} lượt load thành công có đúng 1 matched cùng unit",
              [dong(l) for l in ls[:6]])


def ev03(ev) -> dict:
    ls = loc(ev, "ad_load", thanh_cong=True)
    if not ls:
        return kq("EV-03", "ad_load (thành công)", DO_TAY, "Không có lượt load thành công nào")
    sai = [l for l in ls if "non_won_ad_source" not in l["params"] or _rong(l["params"].get("won_ad_source"))]
    if sai:
        return kq("EV-03", "ad_load (thành công)", SAI, f"{len(sai)}/{len(ls)} ad_load success thiếu won_ad_source / non_won_ad_source",
                  [dong(l) + f" won={l['params'].get('won_ad_source')}" for l in sai])
    return kq("EV-03", "ad_load (thành công)", KHOP, f"{len(ls)}/{len(ls)} ad_load success đủ won_ad_source + non_won_ad_source",
              [dong(l) + f" won={l['params'].get('won_ad_source')}" for l in ls[:6]])


def loi_load_du_truong(failed) -> tuple[list, str]:
    """(event thieu truong, ghi chu gia tri loi cho PO). error_domain duoc trong."""
    thieu = [e for e in failed if not str(e["params"].get("error_code", "")).lstrip("-").isdigit()
             or _rong(e["params"].get("error_code_name"))]  # error_domain duoc trong / vang (lib truyen null -> Bundle bo key)
    gia_tri = sorted({f"{e['params'].get('error_code')}/{e['params'].get('error_code_name')}" for e in failed})
    return thieu, "error_code/error_code_name gặp: " + ", ".join(gia_tri)


def ev05(ev) -> dict:
    # App open co the qua luong AdmobAppOpenAd thieu paid - loi co san (EV-12), xet rieng o EV-25.
    ss = [s for s in loc(ev, "ad_show", thanh_cong=True) if fmt(s) != "app_open"]
    if not ss:
        return kq("EV-05", "ad_show (thành công)", DO_TAY, "Không có lượt hiện quảng cáo nào")
    _, sai, _ = ghep_mot_mot(ss, loc(ev, "paid_ad_impression"), lambda s, p: unit(p) == unit(s) != ""
                             and s["ts"] - 0.5 <= p["ts"] <= s["ts"] + CUA_SO_SHOW_PAID)
    if sai:
        return kq("EV-05", "ad_show (thành công)", SAI, f"{len(sai)}/{len(ss)} ad_show không có paid_ad_impression riêng cùng unit trong {CUA_SO_SHOW_PAID:.0f}s",
                  [dong(s) for s in sai])
    return kq("EV-05", "ad_show (thành công)", KHOP, f"{len(ss)}/{len(ss)} ad_show đều có paid_ad_impression riêng cùng unit (app open xét ở EV-25)",
              [dong(s) for s in ss[:6]])


def ev06(ev) -> dict:
    sf = loc(ev, "ad_show", thanh_cong=False)
    if not sf:
        return kq("EV-06", "ad_show (thất bại)", DO_TAY, "Luồng chạy không có ad_show thất bại — cần dev chỉ nút hiện quảng cáo chưa sẵn sàng")
    sai = [e for e in sf if _rong(e["params"].get("error_code")) or "error_message" not in e["params"]]
    if sai:
        return kq("EV-06", "ad_show (thất bại)", SAI, f"{len(sai)}/{len(sf)} ad_show failed thiếu error_code / error_message", [dong(e) for e in sai])
    return kq("EV-06", "ad_show (thất bại)", KHOP, f"{len(sf)} ad_show failed đủ error_code + error_message", [dong(e) for e in sf[:6]])


def ev07(ev) -> dict:
    app = loc(ev, "event_user_click_ads")
    sdk = loc(ev, "ad_click")
    return kq("EV-07", "event_user_click_ads", DO_TAY,
              "Cần bấm từng loại quảng cáo test rồi đếm — code không biết lúc nào người bấm",
              [dong(e) for e in app + sdk], f"Trong log: {len(app)} event_user_click_ads của app, {len(sdk)} ad_click của SDK Google")


def ev08(ev) -> dict:
    pi = loc(ev, "paid_ad_impression")
    if not pi:
        return kq("EV-08", "paid_ad_impression: đủ tham số", DO_TAY, "Không có paid_ad_impression nào")
    sai = []
    for p in pi:
        x = p["params"]
        loi = [k for k in THAM_SO_PAID if k not in x]
        pr = str(x.get("precision", ""))
        if not (pr.isdigit() and int(pr) <= 3):
            loi.append(f"precision={pr}")
        loi += [f"{k} rỗng" for k in ("network", "ad_source") if k in x and _rong(x[k])]
        if loi:
            sai.append(f"{dong(p)} {loi}")
    if sai:
        return kq("EV-08", "paid_ad_impression: đủ tham số", SAI, f"{len(sai)}/{len(pi)} paid_ad_impression sai tham số", sai)
    return kq("EV-08", "paid_ad_impression: đủ tham số", KHOP, f"{len(pi)}/{len(pi)} paid đủ 8 tham số, precision là số 0–3, network/ad_source không rỗng",
              [dong(p) + f" network={p['params'].get('network')} precision={p['params'].get('precision')}" for p in pi[:6]])


def ev09(ev) -> dict:
    pi = loc(ev, "paid_ad_impression")
    if not pi:
        return kq("EV-09", "paid_ad_impression_value", DO_TAY, "Không có paid_ad_impression nào")
    cap, le, _ = ghep_mot_mot(pi, loc(ev, "paid_ad_impression_value"), lambda p, v: unit(v) == unit(p) != ""
                              and abs(v["ts"] - p["ts"]) <= CUA_SO_PAID_VALUE)
    sai = [f"{dong(p)} → không có paid_ad_impression_value" for p in le]
    for p, v in cap:
        try:
            lech = abs(float(v["params"].get("value")) - float(p["params"].get("valuemicros")) / 1e6) > 1e-9
        except (TypeError, ValueError):
            lech = True
        if lech:
            sai.append(f"{dong(p)} micros={p['params'].get('valuemicros')} value={v['params'].get('value')}")
    if sai:
        return kq("EV-09", "paid_ad_impression_value", SAI, f"{len(sai)}/{len(pi)} lượt paid không có value = valuemicros/1e6 cùng lúc", sai)
    return kq("EV-09", "paid_ad_impression_value", KHOP, f"{len(pi)}/{len(pi)} paid có paid_ad_impression_value cùng unit, value = valuemicros/1e6",
              [dong(p) + f" micros={p['params'].get('valuemicros')}" for p in pi[:6]])


def ev10(ev) -> dict:
    khong_ao = lambda xs: [e for e in xs if fmt(e) != "app_open"]
    n = (len(khong_ao(loc(ev, "ad_show", thanh_cong=True))), len(khong_ao(loc(ev, "paid_ad_impression"))),
         len(khong_ao(loc(ev, "paid_ad_impression_value"))))
    if not n[0]:
        return kq("EV-10", "Số event khớp nhau", DO_TAY, "Không có lượt hiện quảng cáo nào")
    ket = KHOP if len(set(n)) == 1 else SAI
    return kq("EV-10", "Số event khớp nhau", ket,
              f"ad_show success={n[0]}, paid_ad_impression={n[1]}, paid_ad_impression_value={n[2]} (không tính app open — xem EV-25)")


def ev11(ev) -> dict:
    pi, ai = loc(ev, "paid_ad_impression"), loc(ev, "ad_impression")
    if not pi:
        return kq("EV-11", "ad_impression (Firebase tự bắn)", DO_TAY, "Không có lượt hiện quảng cáo nào")
    return kq("EV-11", "ad_impression (Firebase tự bắn)", KHOP if ai else SAI,
              f"{len(ai)} ad_impression cho {len(pi)} paid_ad_impression", [dong(e) for e in ai[:4]])


def ev12_13() -> list[dict]:
    return [kq("EV-12", "App open luồng AdmobAppOpenAd", KHONG_AP_DUNG, "Checklist chỉ ghi nhận lỗi có sẵn; cần dev chỉ màn dùng luồng này"),
            kq("EV-13", "Native trong danh sách có event doanh thu", KHONG_AP_DUNG, "Native danh sách chỉ có trong app, ngoài luồng tutorial")]


def tat_ca(ev, failed_loads) -> list[dict]:
    """EV-01..13. `failed_loads`: ad_load failed tu moi luot (ca luot offline) cho EV-04."""
    ra = [ev01(ev), ev02(ev), ev03(ev)]
    if failed_loads:
        thieu, note = loi_load_du_truong(failed_loads)
        ra.append(kq("EV-04", "ad_load (thất bại)", SAI if thieu else KHOP,
                     f"{len(failed_loads) - len(thieu)}/{len(failed_loads)} ad_load failed đủ error_code (số), error_code_name",
                     [dong(e) for e in (thieu or failed_loads)], note))
    else:
        ra.append(kq("EV-04", "ad_load (thất bại)", DO_TAY, "Không có ad_load thất bại nào trong các lượt"))
    return ra + [ev05(ev), ev06(ev), ev07(ev), ev08(ev), ev09(ev), ev10(ev), ev11(ev)] + ev12_13()

