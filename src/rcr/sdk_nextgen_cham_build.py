"""Muc 1 checklist SDK Next-Gen: phien ban, ban build, khoi tao SDK (8 dong).

Nhan "bang chung" da thu tren may (`sdk_nextgen_thu_log`): danh sach file trong
APK, co debuggable, minSdk app demo, log 10 lan mo lanh, log 10 lan mo lai.
Luat theo cot Expected cua `sdk-check/references/checklist-muc1-sdk-build.txt` +
cach cham user chot trong `how-to-measure-each-case.md` (vd minSdk chi cham lib
ads + SDK tutorial, minSdk app ke).
"""

from __future__ import annotations

import re

from . import fa_log
from .sdk_nextgen_events import _TT, crash, dong, dong_cua_app, fmt, gan, loc, loi_thieu_lop, ok, unit
from .sdk_nextgen_ket import DO_TAY, KHONG_AP_DUNG, KHOP, SAI, kq

MIN_SDK_LIB = 24
DEMO = {"com.apero.moduleads": "lib ads", "com.apero.tutorialsdk.sample": "SDK tutorial"}
MARK_TAG = "RCR_SDK"  # moc `adb shell log -t RCR_SDK "lan N"` chia log thanh tung lan mo
_QUEUED = re.compile(r"queued \(\d+\)")
_READY = re.compile(r"MobileAds ready")
_ADAPTER = re.compile(r"Adapter name:\s*(.*)", re.I)
_STATE = re.compile(r"State:\s*(\w+)", re.I)
_DESC = re.compile(r"Description:\s*([^,]*)", re.I)
_DESC_LOI = re.compile(r"error|fail|not ready|timeout|timed out|exception", re.I)
# Native "hien ngay khi vao man": show cach luc vao man khong qua muc nay.
NATIVE_HIEN_NGAY_S = 2.0
SHOW_TRUOC_SCREEN_VIEW_S = 1.0


def chia_lan(text: str) -> list[str]:
    """Log nhieu lan mo -> moi lan mot doan, theo dong moc RCR_SDK."""
    doan, cur = [], None
    for d in (text or "").splitlines():
        m = _TT.match(d)
        if m and m.group(2) == MARK_TAG:  # dung cot tag: dong `adbd ... log -t RCR_SDK` khong phai moc
            cur = []
            doan.append(cur)
        elif cur is not None:
            cur.append(d)
    return ["\n".join(x) for x in doan]


def muc11(apk_files: list[str], logs: str, package: str) -> dict:
    ten = "Không còn SDK AdMob cũ, không xung đột"
    cu = [f for f in apk_files if f.endswith("play-services-ads.properties")]
    moi = [f for f in apk_files if f.endswith("ads-mobile-sdk.properties")]
    loi = loi_thieu_lop(logs, package)
    tester = [d.strip() for d in logs.splitlines() if "FOR_TESTER_CONFIG" in d][:4]
    if cu or loi:
        return kq("1.1", ten, SAI, ("APK còn play-services-ads.properties (SDK cũ). " if cu else "")
                  + (f"{len(loi)} lỗi thiếu lớp khi chạy." if loi else ""), cu + loi + tester)
    return kq("1.1", ten, KHOP, f"APK không có play-services-ads.properties, {'có' if moi else 'KHÔNG thấy'} ads-mobile-sdk.properties; "
              "0 lỗi NoClassDefFoundError / ClassNotFoundException / NoSuchMethodError", moi + tester)


def muc12(demo_min_sdk: dict) -> dict:
    ten = "minSdk (lib ads + SDK tutorial)"
    co = {p: v for p, v in demo_min_sdk.items() if v is not None}
    if len(co) < len(DEMO):
        thieu = [f"{DEMO[p]} ({p})" for p in DEMO if p not in co]
        return kq("1.2", ten, DO_TAY, "Máy chưa cài app demo: " + ", ".join(thieu))
    sai = {p: v for p, v in co.items() if v != MIN_SDK_LIB}
    bang = [f"{DEMO[p]} {p}: minSdk={v}" for p, v in co.items()]
    return kq("1.2", ten, SAI if sai else KHOP, f"minSdk {'≠' if sai else '='} {MIN_SDK_LIB} ở " + ", ".join(DEMO[p] for p in (sai or co)),
              bang, "minSdk của app không chấm (user chốt)")


def muc13(log_khoi_dong: str, package: str) -> dict:
    ten = "Thứ tự khởi tạo và cổng chờ"
    lan = chia_lan(log_khoi_dong)
    dung, sai, chua_ready, khong_thay = [], [], [], 0
    for i, d in enumerate(lan, 1):
        # Moi lan mo: moc -> am start -> am_proc_start cua app nam trong doan -> loc duoc PID.
        dongs = dong_cua_app(d, package)
        q = next((k for k, x in enumerate(dongs) if _QUEUED.search(x)), None)
        r = next((k for k, x in enumerate(dongs) if _READY.search(x)), None)
        loi_khoi_tao = any("UninitializedPropertyAccessException" in x for x in dongs)
        if loi_khoi_tao or (q is not None and r is not None and r < q):
            sai.append(f"lần {i}: " + ("UninitializedPropertyAccessException" if loi_khoi_tao else "ready trước queued"))
        elif q is not None and r is None:
            chua_ready.append(f"lần {i}: queued nhưng chưa thấy ready")
        elif r is not None:
            dung.append(f"lần {i}: " + (dongs[q].strip()[-70:] + " → " if q is not None else "") + dongs[r].strip()[-60:])
        else:
            khong_thay += 1
    if not lan:
        return kq("1.3", ten, DO_TAY, "Chưa có lượt mở lạnh")
    if sai:
        return kq("1.3", ten, SAI, f"{len(sai)}/{len(lan)} lần sai thứ tự / lỗi khởi tạo", sai)
    if chua_ready or not dung:
        return kq("1.3", ten, DO_TAY, (f"{len(chua_ready)} lần queued mà chưa thấy ready (chậm hay treo?)" if chua_ready
                                      else f"{len(lan)} lần mở không thấy dòng AperoAdmob queued/ready của app (bản tắt log?)"),
                  chua_ready)
    return kq("1.3", ten, KHOP, f"{len(dung)}/{len(lan)} lần: queued trước ready, không UninitializedPropertyAccessException"
              + (f"; {khong_thay} lần không in dòng nào" if khong_thay else ""), dung)


def muc14(log_mo_lai: str, mo_lai_ms: list[int], package: str) -> dict:
    ten = "Mở app nhiều lần không treo"
    if not mo_lai_ms:
        return kq("1.4", ten, DO_TAY, "Chưa có lượt mở lại 10 lần")
    anr = crash(log_mo_lai, package)
    return kq("1.4", ten, SAI if anr else KHOP,
              f"{len(mo_lai_ms)} lần force-stop + mở lại, TotalTime {min(mo_lai_ms)}–{max(mo_lai_ms)} ms, {len(anr)} ANR/crash", anr)


def adapter(logs: str, package: str) -> list[tuple[str, str]]:
    """[(dong adapter, trang thai)] cua app: 'ok' | 'loi' | '?'.

    Lib Next-Gen in `State: COMPLETE`; lib cu in `Description: , Latency: 654` khong co
    State (Sorapix 24/10/2026). Khong State thi xet Description: rong = ok (skill goc:
    "Description cua Meta de trong la binh thuong"), co chu loi = loi.
    """
    ra = []
    for d in dong_cua_app(logs, package):
        m = _ADAPTER.search(d)
        if not m:
            continue
        a = m.group(1).strip()
        st = _STATE.search(a)
        desc = (_DESC.search(a).group(1).strip() if _DESC.search(a) else None)
        if st:
            tt = "ok" if st.group(1).upper() in ("READY", "COMPLETE") else "loi"
        elif desc is not None:
            tt = "loi" if _DESC_LOI.search(desc) else "ok"
        else:
            tt = "?"
        ra.append((a, tt))
    return ra


def muc15(logs: str, package: str) -> dict:
    ten = "Adapter Meta báo sẵn sàng"
    ads = adapter(logs, package)
    meta = [(a, t) for a, t in ads if re.search(r"facebook|meta", a, re.I)]
    if not ads:
        return kq("1.5", ten, DO_TAY, "Không thấy dòng 'Adapter name:' nào của app trong log khởi động")
    if not meta:
        return kq("1.5", ten, KHONG_AP_DUNG, "Mediation không có adapter Meta", sorted({a for a, _ in ads})[:6])
    tt = {t for _, t in meta}
    ket = SAI if "loi" in tt else DO_TAY if "?" in tt else KHOP
    return kq("1.5", ten, ket, {"loi": "Adapter Meta báo lỗi / chưa sẵn sàng", "?": "Không đọc được trạng thái adapter Meta",
                                 None: "Adapter Meta khởi tạo xong"}["loi" if "loi" in tt else "?" if "?" in tt else None],
              sorted({a for a, _ in meta})[:4], "Description của Meta để trống là bình thường")


def muc16(debuggable: bool, logs: str, package: str, ev) -> dict:
    ten = "Bản release (R8) chạy bình thường"
    if debuggable:
        return kq("1.6", ten, DO_TAY, "Bản đang cài là debuggable — cần cài bản release dev gửi rồi chạy lại mục 1")
    loi = loi_thieu_lop(logs, package) + crash(logs, package)
    hien = sorted({fmt(e) for e in loc(ev, "ad_show", thanh_cong=True)})
    return kq("1.6", ten, SAI if loi else KHOP, f"Bản release, {len(loi)} crash/lỗi thiếu lớp; loại đã hiện: {', '.join(hien) or 'không có'}", loi)


def muc17(text_fo: str) -> dict:
    """Native preload: unit da request TRUOC luc vao man (va chua hien lan nao tu request do),
    show trong 2 s sau khi vao. Man khong preload duoc thi khong xet."""
    ten = "Preload native tự viết vẫn chạy"
    tat_ca = fa_log.parse_co_gio(text_fo)
    # Man quang cao toan man (AdActivity) khong phai man cua app.
    vao_man = [e for e in tat_ca if e["name"] == "screen_view" and "AdActivity" not in e["params"].get("ga_screen_class", "")]
    shows = [e for e in tat_ca if e["name"] == "ad_show" and fmt(e) == "native" and ok(e)]
    reqs = [e for e in tat_ca if e["name"] == "track_ad_request"]
    preload, cham = [], []
    for i, v in enumerate(vao_man):
        het = vao_man[i + 1]["ts"] if i + 1 < len(vao_man) else float("inf")
        lop = v["params"].get("ga_screen_class", "")
        # Show co the log truoc screen_view vai ms (Language13 24/10/2026: show 20.511, screen_view 20.522).
        dau = next((s for s in shows if v["ts"] - SHOW_TRUOC_SCREEN_VIEW_S <= s["ts"] < het), None)
        if not dau:
            continue
        req = [r for r in reqs if unit(r) == unit(dau) and r["ts"] < v["ts"] - SHOW_TRUOC_SCREEN_VIEW_S]
        # Request do phai chua duoc dung cho mot lan hien khac (reload dung lai unit cu khong phai preload).
        if not req or any(unit(s) == unit(dau) and req[-1]["ts"] < s["ts"] < dau["ts"] for s in shows):
            continue
        (preload if dau["ts"] - v["ts"] <= NATIVE_HIEN_NGAY_S else cham).append(
            f"{lop}: request {req[-1]['t'][6:]}, vào {v['t'][6:]}, show {dau['t'][6:]} ({dau['ts'] - v['ts']:+.1f}s) …{unit(dau)}")
    if cham:
        return kq("1.7", ten, SAI, f"{len(cham)} native đã preload mà hiện chậm > {NATIVE_HIEN_NGAY_S:.0f}s sau khi vào màn", cham)
    if not preload:
        return kq("1.7", ten, DO_TAY, "Không thấy native nào request trước khi vào màn trong luồng FO", [dong(s) for s in shows[:4]])
    return kq("1.7", ten, KHOP, f"{len(preload)} native request trước khi vào màn, hiện ≤ {NATIVE_HIEN_NGAY_S:.0f}s sau khi vào", preload)


def tat_ca(bc: dict, package: str, ev) -> list[dict]:
    logs = "\n".join(bc.get(k) or "" for k in ("log_khoi_dong", "log_mo_lai", "log_fo"))
    return [muc11(bc.get("apk_files", []), logs, package), muc12(bc.get("demo_min_sdk", {})),
            muc13(bc.get("log_khoi_dong", ""), package), muc14(bc.get("log_mo_lai", ""), bc.get("mo_lai_ms", []), package),
            muc15(bc.get("log_khoi_dong", ""), package), muc16(bc.get("debuggable", True), logs, package, ev),
            muc17(bc.get("log_fo", "")),
            kq("1.8", "Màn dùng Compose và app demo", DO_TAY, "Cần dev chỉ màn Compose + mở từng màn app demo — đo tay")]
