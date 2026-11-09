"""Buoc bat buoc cho tung dong do tay cua checklist SDK Next-Gen + luat ngoai pham vi co dinh.

Dong do tay truoc day do Claude tu nghi cach do -> hai luot cung build ra khac nhau (ADA895 3.3.0, 09/11/2026:
luot chieu bam ca inter lan native o HV-01 ra Sai, luot toi chi bam inter ra Khop; KT-03/04 luot nay cham theo
minSdk lib, luot kia de ngoai pham vi). Tu nay moi dong co danh sach nhanh PHAI thu; `--cham-tay` doi khai tung
buoc bang `--buoc id=ok|sai|khong:<ly do>` (moi buoc mot co):
  ok         da lam, dung ky vong
  sai        da lam, ra loi (bang chung trong --ly-do)
  khong:...  nhanh nay khong co trong app (vd khong co banner trong luong) - phai ghi vi sao
Khop / ngoai pham vi: moi buoc phai co, khong buoc nao `sai`. Sai: chi can mot buoc `sai` (luat 6: mot luot bang
chung chac la du), buoc chua lam khong bat buoc.
"""

from __future__ import annotations

from .models import RcError
from .sdk_nextgen_ket import KHONG_AP_DUNG, KHOP, SAI

_INTER = ("inter", "bấm inter (splash hoặc resume) → trang đích → quay lại app")
_NATIVE = ("native", "bấm native (LFO/OB/Question) → trang đích, đứng ≥5s cho ad resume kịp load → quay lại app")
_BANNER = ("banner", "bấm banner trong luồng tutorial → trang đích → quay lại (không có banner thì khong:)")

# ma -> [(id buoc, mo ta)]. Nhanh theo DINH DANG ad: app co dinh dang nao trong luong thi phai thu dinh dang do.
BUOC: dict[str, list[tuple[str, str]]] = {
    "1.2": [("demo_lib", "minSdk app demo lib ads com.apero.moduleads (máy, ~/.cache/ad-checklist-diff, APK máy QA khác)"),
            ("demo_sdk", "minSdk app mẫu SDK tutorial (com.apero.tutorialsdk.sample / com.apero.firstopen.sample, aapt2 dump badging)")],
    "1.7": [("preload", "track_ad_request native trước khi vào màn, ad_show ≤2s sau *_view")],
    "1.8": [("compose", "dumpsys activity top tìm ComposeView/AndroidComposeView từng màn tutorial + Home"),
            ("ad_compose", "ad trên màn Compose load/show không crash (không có màn Compose thì khong:)")],
    "EV-06": [("home_loading", "Home đúng lúc khung Loading Ads ở bước chuyển màn có inter (Question → Home, Splash)"),
              ("tim_log", "grep ad_show show_status=failed trong mọi log của lượt (cả banner ERROR_VIEW)")],
    "EV-07": [("inter", "bấm inter → đúng 1 event_user_click_ads cùng unit"),
              ("native", "bấm native → đúng 1 event_user_click_ads cùng unit"),
              ("banner", "bấm banner → đúng 1 event (không có banner trong luồng thì khong:)")],
    "EV-25": [("resume_tutorial", "Home → mở lại bằng icon ở Language/OB (không ở Home), đủ chuỗi request→matched→load→show→paid")],
    "EV-26": [("show_paid", "native ad_show → paid_ad_impression(+value) đúng 1 lần"),
              ("click", "bấm native → đúng 1 event_user_click_ads cùng unit")],
    "EV-27": [("click_reload", "bấm native → về app: có/không track_ad_request mới, đối chiếu logic lib (soi dex NativeAdReload…)"),
              ("het_video", "đứng màn native video tới hết video (hoặc ≥60s): có/không request mới")],
    "EV-30": [("ad_that", "tìm paid_ad_impression valuemicros>0 (precision≠0, không nhãn Test Ad) trong mọi log lượt + lượt offline")],
    "HT-01": [("co_mang", "banner có mạng: load hoặc no fill thì vùng banner ẩn"), ("mat_mang", "tắt mạng: không ô banner trống, không crash")],
    "HT-02": [("bounds", "bounds view banner = chiều rộng màn")],
    "HT-03": [("bam_cta", "bấm CTA inter → trang đích"), ("ve_lai", "về app: vẫn đúng inter cũ"), ("dong_x", "bấm X → đúng màn kế")],
    "HT-04": [("resume_tutorial", "Home → mở lại bằng icon ở luồng tutorial ≥2 lần")],
    "HT-05": [("home_khi_hien", "inter đang hiện → Home → mở lại: số AdActivity trong stack = 1, không ad resume mới")],
    "HT-06": [("cay_view", "cây view native: Ad badge, headline, media, CTA, AdChoices"), ("validator", "popup validator / không che nút")],
    "HT-07": [("video", "native creative video: tự chạy, tắt tiếng, đúng tỉ lệ (không có video thì khong:)")],
    "HT-09": [("native_full", "OB native toàn màn: chạy user mới tới khi fill, chờ quá timer_button_x, kiểm btnSkip/X"),
              ("dialog_thoat", "Home → Back: dialog thoát app có native không")],
    "HT-11": [("mua_sub", "mua sub test trên Play"), ("mo_lanh", "mở lạnh + đi luồng: 0 track_ad_request / ad_show")],
    "MED-02": [("nguon", "Ad Inspector hoặc won_ad_source/non_won_ad_source từng nguồn trong ad_load + log adapter")],
    "HV-01": [_INTER, _NATIVE, _BANNER],
    "HV-07": [("ad_ve_muon", "giữ request ad toàn màn (proxy chậm domain ads 6s / chặn mạng theo app Android 13+) rồi rời màn")],
    "HV-08": [("home_loading", "Home ngay sau onAdLoaded khi khung Loading Ads → mở lại: không inter, không ad chồng")],
}

# Dong KHONG duoc dua ra ngoai pham vi: co luat cham thay co dinh (khong co may / khong co app demo khong phai ly do).
CAM_NGOAI_PHAM_VI: dict[str, str] = {
    "1.2": "luật 3: chấm theo minSdk lib ads + SDK tutorial; không có app demo trên máy thì lấy APK ở "
           "~/.cache/ad-checklist-diff, scratchpad, máy QA khác (aapt2 dump badging)",
    "KT-03": "đi theo 1.2 (minSdk lib ads + SDK = 24) — chấm 1.2 là KT-03/04 tự lấy kết quả",
    "KT-04": "đi theo 1.2 (minSdk lib ads + SDK = 24) — chấm 1.2 là KT-03/04 tự lấy kết quả",
    "HV-01": "luồng tutorial luôn có inter/native để bấm — đo theo các bước",
    "HT-03": "luồng tutorial luôn có inter — đo theo các bước",
}
# Dong ket qua di theo dong khac (cung bang chung).
THEO: dict[str, tuple[str, ...]] = {"1.2": ("KT-03", "KT-04")}

_GIA_TRI = ("ok", "sai")


def doc_buoc(phan: list[str] | str) -> dict[str, str]:
    """["inter=ok", "banner=khong:không có banner, chỉ native"] -> {id: gia tri}. Moi buoc mot `--buoc` (ly do co dau phay)."""
    ra: dict[str, str] = {}
    for x in [phan] if isinstance(phan, str) else phan:
        if not (x or "").strip():
            continue
        k, sep, v = x.partition("=")
        k, v = k.strip(), v.strip()
        if not sep or not k:
            raise RcError(f"--buoc sai dạng ở {x.strip()!r}: cần id=ok|sai|khong:<lý do>")
        ra[k] = v
    return ra


def kiem(ma: str, ket: str, buoc: dict[str, str]) -> list[dict]:
    """Kiem buoc cho dong `ma` truoc khi ghi ket qua. -> danh sach buoc da khai (de luu + hien report)."""
    if ket == KHONG_AP_DUNG and ma in CAM_NGOAI_PHAM_VI:
        raise RcError(f"{ma} không được để ngoài phạm vi — {CAM_NGOAI_PHAM_VI[ma]}")
    can = BUOC.get(ma)
    if not can:
        return [{"id": k, "v": v} for k, v in buoc.items()]
    ids = [i for i, _ in can]
    la = [k for k in buoc if k not in ids]
    if la:
        raise RcError(f"{ma}: bước {', '.join(la)} không có. Bước của {ma}: {', '.join(ids)}")
    for k, v in buoc.items():
        if v not in _GIA_TRI and not (v.startswith("khong:") and v[6:].strip()):
            raise RcError(f"{ma}: bước {k}={v!r} — giá trị phải là ok, sai hoặc khong:<lý do>")
    sai = [k for k, v in buoc.items() if v == "sai"]
    if ket == SAI and not sai:
        raise RcError(f"{ma}: chấm Sai thì phải có ít nhất một bước =sai (bước ra lỗi)")
    if ket in (KHOP, KHONG_AP_DUNG):
        thieu = [f"{i} ({m})" for i, m in can if i not in buoc]
        if thieu:
            raise RcError(f"{ma}: chưa làm đủ bước, không được chấm {ket}. Còn thiếu: " + "; ".join(thieu))
        if sai:
            raise RcError(f"{ma}: bước {', '.join(sai)} =sai mà chấm {ket} — bước ra lỗi thì dòng là Sai")
        if ket == KHOP and not any(v == "ok" for v in buoc.values()):
            raise RcError(f"{ma}: mọi bước đều khong: → không có gì để chấm Khớp; dùng KHONG_AP_DUNG")
    mo_ta = dict(can)
    return [{"id": i, "mo_ta": mo_ta[i], "v": buoc[i]} for i in ids if i in buoc]


def du_buoc(r: dict) -> bool:
    """Dong da cham tay voi du buoc (dung lai duoc o luot sau). Dong khong co danh sach buoc: co ly do la du."""
    can = BUOC.get(r["ma"])
    if not can:
        return True
    co = {b["id"] for b in r.get("buoc") or []}
    return all(i in co for i, _ in can)


def goi_y(ket_qua: list[dict]) -> dict[str, list[str]]:
    """Dong con DO_TAY -> buoc phai lam (in ra stdout cho Claude / bot)."""
    return {r["ma"]: [f"{i}: {m}" for i, m in BUOC.get(r["ma"], [])] for r in ket_qua if r["ket"] == "DO_TAY"}
