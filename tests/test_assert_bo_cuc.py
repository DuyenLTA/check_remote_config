"""Cham bo cuc splash bang bounds. Toa do lay tu dump that Piclux 2.4.0 (24/10/2026)."""

from __future__ import annotations

from rcr import assert_check as a

PKG = "aiphotogenerator.photoshoot.aiart.aiimagegenerator"


def _node(rid, bounds, text="", cls="android.widget.FrameLayout"):
    return (f'<node index="0" text="{text}" resource-id="{PKG}:id/{rid}" class="{cls}" package="{PKG}" '
            f'content-desc="" clickable="false" enabled="true" bounds="{bounds}" />')


def _dump(*nodes):
    return ('<?xml version="1.0" encoding="UTF-8"?><hierarchy rotation="0">'
            f'<node index="0" text="" resource-id="{PKG}:id/splash_root" class="android.view.ViewGroup" '
            f'package="{PKG}" content-desc="" clickable="false" enabled="true" bounds="[0,0][1080,2400]">'
            + "".join(nodes) + "</node></hierarchy>")


PROGRESS = _node("splProcessId", "[0,1140][1080,1404]", cls="android.widget.ImageView")
NHAN = _node("this_maybe_contain_ads", "[0,1344][1080,1401]", "This action may contain ads",
             "android.widget.TextView")
NATIVE = _node("nativeAdView", "[0,1514][1080,2400]")


def _drive(*dumps, density=480):
    return {"density": density, "steps": [{"n": i, "dump": d, "action": {"kind": "noop"},
                                           "activity": "SplashActivity"} for i, d in enumerate(dumps, 1)]}


def check(line, drive):
    return a.check(line, {}, drive, {"crashed": False})


def test_cum_neo_ngay_tren_native_khong_chen_gi():
    out = check("Progress + text neo NGAY TRÊN mép native", _drive(_dump(PROGRESS, NHAN, NATIVE)))
    assert out["verdict"] == a.PASS and "37dp" in out["reason"]


def test_co_node_chen_giua_thi_khong_phai_ngay_tren():
    chen = _node("tvNote", "[0,1420][1080,1500]", "Loading", "android.widget.TextView")
    out = check("Progress + text neo NGAY TRÊN mép native", _drive(_dump(PROGRESS, NHAN, chen, NATIVE)))
    assert out["verdict"] == a.FAIL and "chen" not in out["reason"] and "Loading" in out["reason"]


def test_de_len_native_thi_fail():
    native_cao = _node("nativeAdView", "[0,1300][1080,2400]")
    out = check("Progress/text KHÔNG đè lên native.", _drive(_dump(PROGRESS, NHAN, native_cao)))
    assert out["verdict"] == a.FAIL and "ĐÈ" in out["reason"]


def test_khoang_cach_dp_ngoai_khoang_thi_fail_co_so_do():
    banner = _node("banner_container", "[0,1514][1080,1700]")
    out = check("Progress + text neo trên mép banner 12–16dp, KHÔNG đè banner.",
                _drive(_dump(PROGRESS, NHAN, banner)))
    assert out["verdict"] == a.FAIL and "36.7dp" in out["reason"]


def test_khoang_cach_dp_trong_khoang_thi_pass():
    banner = _node("banner_container", "[0,1446][1080,1700]")     # 42px / 3 = 14dp
    out = check("Progress + text neo trên mép banner 12–16dp, KHÔNG đè banner.",
                _drive(_dump(PROGRESS, NHAN, banner)))
    assert out["verdict"] == a.PASS and "14.0dp" in out["reason"]


def test_chua_thay_banner_thi_can_nguoi_khong_doan():
    out = check("Progress + text neo trên mép banner 12–16dp", _drive(_dump(PROGRESS, NHAN)))
    assert out["verdict"] == a.NEEDS_HUMAN


def test_nhan_duoi_progress_va_mot_khung_chua_chung_minh_di_cung_cum():
    one = check("Nhãn nằm ngay DƯỚI progress bar, di chuyển cùng cụm progress.",
                _drive(_dump(PROGRESS, NHAN, NATIVE)))
    assert one["verdict"] == a.NEEDS_HUMAN and "chưa đổi vị trí" in one["reason"]
    len_tren = _dump(_node("splProcessId", "[0,1040][1080,1304]", cls="android.widget.ImageView"),
                     _node("this_maybe_contain_ads", "[0,1244][1080,1301]",
                           "This action may contain ads", "android.widget.TextView"), NATIVE)
    two = check("Nhãn nằm ngay DƯỚI progress bar, di chuyển cùng cụm progress.",
                _drive(_dump(PROGRESS, NHAN), len_tren))
    assert two["verdict"] == a.PASS


def test_progress_dich_khi_native_hien_thi_fail():
    truoc = _dump(_node("splProcessId", "[0,2000][1080,2264]", cls="android.widget.ImageView"), NHAN)
    out = check("Khi native show: progress + text KHÔNG dịch chuyển (0 shift).",
                _drive(truoc, _dump(PROGRESS, NHAN, NATIVE)))
    assert out["verdict"] == a.FAIL and "dịch -860px" in out["reason"]


def test_giua_man_lay_khung_co_ad():
    o_day = _dump(_node("splProcessId", "[0,1960][1080,2100]", cls="android.widget.ImageView"))
    out = check("Progress + text vẫn ở vị trí giữa màn", _drive(_dump(PROGRESS, NHAN, NATIVE), o_day))
    assert out["verdict"] == a.PASS and "53%" in out["reason"]
