"""Muc 4 (KT / MED / CMP / EV-30..32 / HV / RG) checklist SDK Next-Gen.

Luat theo `sdk-check/references/checklist-muc4-nextgen-KT-MED-CMP-EV3x-HV-RG.txt`
va cach cham user chot trong `how-to-measure-each-case.md`:
  - case can ban cu de so (KT-07, CMP-01/02/03, HV-06): bo theo yeu cau (15/10/2026)
  - KT-03/04: cham theo minSdk lib ads + SDK tutorial, minSdk app ke
  - UMP "no form configured" = cau hinh tai khoan AdMob, khong phai bug dev
"""

from __future__ import annotations

import re

from .sdk_nextgen_cham_build import MARK_TAG, adapter, muc12
from .sdk_nextgen_events import crash, dong, dong_cua_app, doc_events, fmt, loc, tach_moc, unit
from .sdk_nextgen_ket import DO_TAY, KHONG_AP_DUNG, KHOP, SAI, kq

MOC_MAC_DINH_SPLASH_S = 60.0   # spec "logic preload publishing": app khong khai timeout -> 60 s tong inter splash
DU_SPLASH_S = 3.0              # sai so do (poll 0,5 s + dumpsys)
HV02_CUA_SO_S = 30.0
BO_THEO_YEU_CAU = "Bỏ theo yêu cầu (user chốt 15/10/2026): cần APK bản cũ cùng key để so"
_UMP_KHONG_FORM = re.compile(r"misconfiguration|no form", re.I)
_APPSFLYER = re.compile(r"pushTrackEventAdmob enableAppsflyer:(true|false)", re.I)
_ADJUST_OK = re.compile(r"AdSdkAdjust.*Event success callback", re.I)


def kt01(bc: dict, off_mat: str, off_sau: str, package: str) -> dict:
    ten = "Mở app khi không có mạng"
    if not off_mat:
        return kq("KT-01", ten, DO_TAY, "Chưa có lượt mất mạng")
    if not bc.get("offline_mang_that_tat", True):
        return kq("KT-01", ten, DO_TAY, "Đã tắt wifi + data mà máy vẫn ra được internet — lượt không dùng được")
    cr = crash(off_mat + "\n" + off_sau, package)
    if cr:
        return kq("KT-01", ten, SAI, "App crash / ANR", cr)
    roi = bc.get("offline_roi_splash_s")
    if roi is None:
        return kq("KT-01", ten, SAI, f"Mất mạng: sau 30s vẫn đứng ở splash ({bc.get('offline_man')})")
    ev_sau = doc_events(off_sau)
    thanh_cong = loc(ev_sau, "ad_load", thanh_cong=True)
    if thanh_cong:
        return kq("KT-01", ten, KHOP, f"Rời splash sau {roi}s khi mất mạng; bật mạng lại → {len(thanh_cong)} ad_load success ở màn sau",
                  [f"rời splash → {bc.get('offline_man')}"] + [dong(e) for e in thanh_cong[:4]])
    xin = [e for e in ev_sau if e["name"] in ("track_ad_request", "ad_load")]
    return kq("KT-01", ten, DO_TAY, f"Rời splash sau {roi}s; bật mạng lại chưa thấy ad_load success "
              + ("(có request — có thể no-fill)" if xin else "(màn sau không xin quảng cáo)"), [dong(e) for e in xin[:4]])


def kt02(bc: dict, log_cham: str | None, package: str) -> dict:
    ten = "Mở app khi mạng chậm"
    if log_cham is None:
        return kq("KT-02", ten, DO_TAY, "Chưa có lượt mạng chậm")
    cr = crash(log_cham, package)
    if cr:
        return kq("KT-02", ten, SAI, "App crash / ANR khi mạng chậm", cr)
    moc = bc.get("cham_timeout_s") or MOC_MAC_DINH_SPLASH_S
    nguon = f"key {bc['cham_timeout_key']}" if bc.get("cham_timeout_key") else "mặc định 60s (app không khai timeout)"
    roi = bc.get("cham_roi_splash_s")
    if roi is None:
        return kq("KT-02", ten, SAI, f"Mạng chậm: đứng ở splash quá 120s (timeout {moc:.0f}s, {nguon})")
    ly = f"Mạng chậm (proxy 3s, 8 KB/s): rời splash sau {roi}s, timeout {moc:.0f}s ({nguon}) → {bc.get('cham_man')}"
    if roi <= moc + DU_SPLASH_S:
        return kq("KT-02", ten, KHOP, ly)
    # Timeout la cua inter splash (spec "60 s tong inter splash"), tinh tu request inter splash dau tien.
    # Thoi gian truoc do (UMP, khoi tao MobileAds qua mang cham) khong thuoc timeout nay.
    cua_so = _inter_splash_s(log_cham or "", package)
    if cua_so is None:
        return kq("KT-02", ten, SAI, ly)
    inter_s, truoc_s, bc_dong = cua_so
    ly_inter = (f"{ly}; inter splash {inter_s:.1f}s (request inter đầu → rời splash), "
                f"{truoc_s:.1f}s trước đó là khởi tạo trước khi xin inter")
    return kq("KT-02", ten, KHOP if inter_s <= moc + DU_SPLASH_S else SAI, ly_inter, bc_dong)


_THOI_GIAN = re.compile(r"^(\d\d-\d\d \d\d:\d\d:\d\d\.\d+)")


def _inter_splash_s(log: str, package: str) -> tuple[float, float, list[str]] | None:
    """(giay tu request inter splash dau -> rời splash, giay tu mo app -> request do, dong bang chung).

    Mo app = START launcher cua package; roi splash = START dau tien cua package khong phai Splash.
    Thieu moc nao -> None (giu cach cham theo tong thoi gian splash)."""
    from datetime import datetime

    def gio(dong_log: str):
        m = _THOI_GIAN.match(dong_log)
        # nam 2000 (nhuan) chi de strptime khong canh bao / khong hong ngay 29-02; chi dung hieu so
        return datetime.strptime("2000-" + m.group(1), "%Y-%m-%d %H:%M:%S.%f") if m else None

    mo = roi = None
    mo_dong = roi_dong = ""
    for d in log.splitlines():
        if "ActivityTaskManager: START" not in d or f"cmp={package}/" not in d:
            continue
        if mo is None and "LAUNCHER" in d:
            mo, mo_dong = gio(d), d
        elif mo is not None and "Splash" not in d.split(f"cmp={package}/", 1)[1].split()[0]:
            roi, roi_dong = gio(d), d
            break
    req = next((e for e in loc(doc_events(log), "track_ad_request")
                if fmt(e) == "interstitial" and "Splash" in e["params"].get("ga_screen_class", "")), None)
    if not (mo and roi and req) or gio(req["t"]) is None:
        return None
    t_req = gio(req["t"])
    if not (mo <= t_req <= roi):
        return None
    return ((roi - t_req).total_seconds(), (t_req - mo).total_seconds(),
            [mo_dong.strip()[:160], dong(req), roi_dong.strip()[:160]])


def kt03_04(demo: dict) -> list[dict]:
    r = muc12(demo)
    return [{**r, "ma": "KT-03", "ten": "Chạy trên Android 7.0 (API 24)"},
            {**r, "ma": "KT-04", "ten": "Không cài được dưới Android 7.0"}]


def kt05_06(log_khoi_dong: str, package: str) -> list[dict]:
    ump = [d.strip() for d in dong_cua_app(log_khoi_dong, package) if "AdsConsentManager" in d]
    if any(_UMP_KHONG_FORM.search(d) for d in ump):
        ly = "Tài khoản AdMob chưa cấu hình form UMP (Publisher misconfiguration) — không phải bug dev"
        return [kq(m, t, KHONG_AP_DUNG, ly, ump[:3]) for m, t in (("KT-05", "Form đồng ý (UMP) hiện trước quảng cáo đầu tiên"),
                                                                   ("KT-06", "Từ chối đồng ý vẫn chạy bình thường"))]
    ly = "Cần dev bật debug geography = EEA + thêm máy test rồi đo tay"
    return [kq("KT-05", "Form đồng ý (UMP) hiện trước quảng cáo đầu tiên", DO_TAY, ly, ump[:3]),
            kq("KT-06", "Từ chối đồng ý vẫn chạy bình thường", DO_TAY, ly)]


def med01(log_khoi_dong: str, package: str) -> dict:
    ten = "Tất cả adapter mediation báo sẵn sàng"
    ads = adapter(log_khoi_dong, package)
    if not ads:
        return kq("MED-01", ten, DO_TAY, "Không thấy dòng 'Adapter name:' nào của app")
    loi = sorted({a for a, t in ads if t == "loi"})
    if loi:
        return kq("MED-01", ten, SAI, f"{len(loi)} adapter báo lỗi / chưa sẵn sàng", loi)
    if any(t == "?" for _, t in ads):
        return kq("MED-01", ten, DO_TAY, "Có adapter không đọc được trạng thái", sorted({a for a, t in ads if t == "?"}))
    return kq("MED-01", ten, KHOP, f"{len({a for a, _ in ads})} adapter khởi tạo xong", sorted({a for a, _ in ads})[:8],
              "So với danh sách mediation dev gửi nếu có")


def ev30(ev) -> dict:
    ten = "Giá trị doanh thu với quảng cáo thật"
    that = []
    for p in loc(ev, "paid_ad_impression"):
        try:
            if float(p["params"].get("valuemicros", 0)) > 0:
                that.append(p)
        except ValueError:
            continue
    if not that:
        return kq("EV-30", ten, DO_TAY, "Chỉ có quảng cáo test (valuemicros = 0) — cần bản dùng ad unit thật, chỉ xem không bấm")
    tien = sorted({p["params"].get("currency", "") for p in that})
    if "" in tien:
        return kq("EV-30", ten, SAI, "paid_ad_impression có valuemicros > 0 mà thiếu currency", [dong(p) for p in that[:4]])
    return kq("EV-30", ten, KHOP, f"{len(that)} paid có valuemicros > 0, currency {', '.join(tien)} (value = valuemicros/1e6 kiểm ở EV-09)",
              [dong(p) + f" micros={p['params'].get('valuemicros')}" for p in that[:4]],
              "" if tien == ["USD"] else "Currency khác USD: ghi lại để dev xác nhận cách quy đổi")


def ev31(ev) -> dict:
    ten = "Nguồn doanh thu khớp nguồn thắng"
    loads = loc(ev, "ad_load", thanh_cong=True)
    cap, lech = 0, []
    for l in loads:
        sau = [e["ts"] for e in loads if unit(e) == unit(l) and e["ts"] > l["ts"]]
        p = next((x for x in loc(ev, "paid_ad_impression") if unit(x) == unit(l) and l["ts"] < x["ts"] < min(sau, default=float("inf"))), None)
        if p is None:
            continue
        cap += 1
        if l["params"].get("won_ad_source") != p["params"].get("ad_source"):
            lech.append(f"{dong(l)} won={l['params'].get('won_ad_source')} ≠ ad_source={p['params'].get('ad_source')}")
    if not cap:
        return kq("EV-31", ten, DO_TAY, "Không có cặp ad_load success → paid cùng unit")
    return kq("EV-31", ten, SAI if lech else KHOP, f"{cap - len(lech)}/{cap} lượt won_ad_source = ad_source", lech)


def ev32(text_fo: str, ev, package: str) -> dict:
    ten = "Doanh thu gửi sang Adjust / AppsFlyer"
    app = dong_cua_app(text_fo, package)
    af = [m.group(1).lower() for m in map(_APPSFLYER.search, app) if m]
    adj = [d for d in app if _ADJUST_OK.search(d)]
    paid = len(loc(ev, "paid_ad_impression"))
    if not af and not adj:
        return kq("EV-32", ten, DO_TAY, "Không thấy log AperoAppsflyer / AdSdkAdjust — hỏi dev app có gửi doanh thu sang MMP không")
    if "true" not in af and not adj:
        return kq("EV-32", ten, KHONG_AP_DUNG, "App tắt gửi doanh thu sang AppsFlyer (enableAppsflyer:false), không có Adjust")
    n = len(adj) if adj else af.count("true")
    return kq("EV-32", ten, KHOP if n == paid else SAI, f"{n} lần gửi MMP cho {paid} paid_ad_impression",
              ghi_chu="Giá trị trên trang test của MMP cần đối chiếu tay nếu dev yêu cầu")


def hv02(text_fo: str) -> dict:
    """Sau inter (FO, truoc luc Home -> mo lai) khong duoc co app open trong 30 s."""
    ten = "Không hiện app open ngay sau khi đóng quảng cáo toàn màn hình"
    truoc, _ = tach_moc(text_fo, MARK_TAG, "resume")
    ev = doc_events(truoc)
    inters = loc(ev, "ad_show", thanh_cong=True, dinh_dang="interstitial")
    if not inters:
        return kq("HV-02", ten, DO_TAY, "Luồng FO không có inter nào hiện")
    ao = loc(ev, "ad_show", thanh_cong=True, dinh_dang="app_open")
    chong = [f"{dong(i)} → app open {a['t']}" for i in inters for a in ao if 0 < a["ts"] - i["ts"] <= HV02_CUA_SO_S]
    return kq("HV-02", ten, SAI if chong else KHOP,
              f"{len(inters)} inter, {len(chong)} lần app open trong {HV02_CUA_SO_S:.0f}s sau đó", chong or [dong(i) for i in inters])


def ht04(text_fo: str) -> dict:
    ten = "App open hiện khi quay lại app"
    _, sau = tach_moc(text_fo, MARK_TAG, "resume")
    if not sau:
        return kq("HT-04", ten, DO_TAY, "Chưa có lượt Home → mở lại app")
    ao = loc(doc_events(sau), "ad_show", thanh_cong=True, dinh_dang="app_open")
    if ao:
        return kq("HT-04", ten, KHOP, f"{len(ao)} lần app open hiện sau Home → mở lại", [dong(a) for a in ao])
    return kq("HT-04", ten, DO_TAY, "Home → mở lại 2 lần không thấy app open — kiểm RC bật app open resume rồi đo tay")


def tat_ca(bc: dict, ev, logs: dict, package: str) -> list[dict]:
    co = {fmt(e) for e in ev}
    ra = [kt01(bc, logs.get("offline_mat", ""), logs.get("offline_sau", ""), package), kt02(bc, logs.get("cham"), package)]
    ra += kt03_04(bc.get("demo_min_sdk", {})) + kt05_06(logs.get("khoi_dong", ""), package)
    ra += [kq("KT-07", "Cập nhật đè từ bản cũ lên bản Next-Gen", KHONG_AP_DUNG, BO_THEO_YEU_CAU),
           med01(logs.get("khoi_dong", ""), package),
           kq("MED-02", "Từng nguồn mediation có trả quảng cáo", DO_TAY, "Ad Inspector cần lắc máy — đo tay")]
    ra += [kq(m, t, KHONG_AP_DUNG, BO_THEO_YEU_CAU) for m, t in (("CMP-01", "Số lần xin quảng cáo mỗi ad unit"),
           ("CMP-02", "Tỉ lệ load thành công"), ("CMP-03", "Thời gian mở app đến màn đầu"))]
    ra += [ev30(ev), ev31(ev), ev32(logs.get("fo", ""), ev, package),
           kq("HV-01", "Không hiện app open khi quay lại sau khi bấm quảng cáo", DO_TAY, "Cần bấm quảng cáo test → trang đích → quay lại"),
           hv02(logs.get("fo", ""))]
    thuong = "rewarded" in co or "rewarded_interstitial" in co
    for m, t in (("HV-03", "Rewarded: đóng sớm không nhận thưởng"), ("HV-04", "Rewarded: xem hết nhận thưởng đúng 1 lần"),
                 ("HV-05", "Rewarded interstitial: chuỗi event và nhận thưởng")):
        ra.append(kq(m, t, DO_TAY, "Có rewarded trong luồng — đo tay phần thưởng") if thuong
                  else kq(m, t, KHONG_AP_DUNG, "Rewarded chỉ có trong app, ngoài luồng tutorial"))
    ra += [kq("HV-06", "Bấm Back khi đang xem quảng cáo toàn màn hình", KHONG_AP_DUNG, BO_THEO_YEU_CAU),
           kq("HV-07", "Quảng cáo về muộn khi đã rời màn", DO_TAY, "Cần proxy chậm riêng domain ads 6s + rời màn đúng lúc — đo tay"),
           kq("HV-08", "Bấm Home khi inter đang load", DO_TAY, "Cần bấm Home đúng lúc khung Loading Ads — đo tay")]
    collapsible = any("collapsible" in d.lower() for d in dong_cua_app(logs.get("fo", ""), package))
    ra.append(kq("HV-09", "Collapsible banner", DO_TAY, "Có collapsible banner — đo tay") if collapsible
              else kq("HV-09", "Collapsible banner", KHONG_AP_DUNG, "Không có collapsible banner trong luồng"))
    ra.append(kq("RG-01", "Chạy lại bộ test case luồng FO", KHONG_AP_DUNG, "Bản SDK này không có bộ TC"))
    return ra


def muc2(ev, text_fo: str) -> list[dict]:
    """Muc 2 HT: phan lon can nhin mat -> DO_TAY; HT-04 cham bang log, HT-08/10 ngoai luong tutorial."""
    co_banner = bool(loc(ev, "ad_load", dinh_dang="banner"))
    nhin = "Cần nhìn màn hình — đo tay"
    ra = [kq(m, t, DO_TAY if co_banner else KHONG_AP_DUNG, nhin if co_banner else "Luồng tutorial không có banner")
          for m, t in (("HT-01", "Banner load xong hoặc lỗi, vùng banner đúng"), ("HT-02", "Adaptive banner hiện đủ chiều rộng"))]
    ra += [kq("HT-03", "Interstitial: bấm quảng cáo và đóng quảng cáo", DO_TAY, "Cần bấm quảng cáo test → trang đích → X"), ht04(text_fo),
           kq("HT-05", "App open không đè lên quảng cáo toàn màn hình", DO_TAY, "Cần Home đúng lúc inter đang hiện — đo tay"),
           kq("HT-06", "Native hiện đủ thành phần", DO_TAY, nhin), kq("HT-07", "Native video", DO_TAY, nhin),
           kq("HT-08", "Tải nhiều native một lúc (danh sách)", KHONG_AP_DUNG, "Native danh sách chỉ có trong app"),
           kq("HT-09", "Dialog thoát app và interstitial dạng native", DO_TAY, nhin),
           kq("HT-10", "Vào ra màn có native nhiều lần", KHONG_AP_DUNG, "Chỉ có trong app"),
           kq("HT-11", "User đã mua thì không load quảng cáo", DO_TAY, "Cần mua sub test — đo tay")]
    return ra

