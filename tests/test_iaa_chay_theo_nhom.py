"""Bo IAA chay theo nhom bien the (rcr-iaa): dat config cho moi vi tri + tu cham dong doc duoc tu log FA-SVC."""

from rcr import cli_iaa, iaa_cham_log, iaa_nhom
from rcr.tc_iaa_tu_sheet_kt import Tang, ViTri

PUB = "ca-app-pub-4584260126367940"
LOADING = ViTri("native_loading", man="Loading", loai="Native", mo_ta="Native ở màn loading\nReload mỗi 5 giây",
                high=Tang("native_loading_high", f"{PUB}/5560105865", "show_native_loading_high"),
                thuong=Tang("native_loading", f"{PUB}/6465993422", "show_native_loading"))
STYLE = ViTri("inter_style", man="Home", loai="Interstitial", mo_ta="Inter khi bấm style",
              high=Tang("inter_style_high", f"{PUB}/5278915165", "show_inter_style_high"),
              thuong=Tang("inter_style", f"{PUB}/9445390883", "show_inter_style"))
DS = [LOADING, STYLE]


def _dong(t: float, ten: str, unit: str, trang_thai: str = "") -> str:
    """Mot dong logcat -v epoch cua FA-SVC, dung khuon may that (AIP893 13/11/2026)."""
    if ten == "track_ad_request":
        body = f"network_status=1, adunitid={unit}, ga_screen_class(_sc)=MainActivity, ad_format=NATIVE"
    elif ten == "ad_load":
        body = f"load_status={trang_thai or 'success'}, ad_unit_id={unit}, ad_format=native"
    else:
        body = f"ad_unit_id={unit}, show_status={trang_thai or 'success'}, ad_format=native"
    return f"   {t:.3f}  7191 30944 V FA-SVC  : Logging event: origin=app,name={ten},params=Bundle[{{{body}}}]"


def _log(*dong: str) -> str:
    return "\n".join(dong) + "\n"


def test_gia_tri_moi_bien_the_cho_moi_vi_tri():
    assert iaa_nhom.gia_tri(DS, "bat") == {k: "true" for k in (
        "show_native_loading_high", "show_native_loading", "show_inter_style_high", "show_inter_style")}
    thuong = iaa_nhom.gia_tri(DS, "thuong")
    assert thuong["show_native_loading_high"] == "false" and thuong["show_native_loading"] == "true"
    assert set(iaa_nhom.gia_tri(DS, "tat").values()) == {"false"}
    assert iaa_nhom.ma_case(2, "high") == "IAA-02-03"


def test_vi_tri_mot_tang_giu_bat_o_bien_the_thuong_high():
    don = ViTri("banner_home", high=None, thuong=Tang("banner_home", f"{PUB}/1", "show_banner_home"))
    assert iaa_nhom.gia_tri([don], "high") == {"show_banner_home": "true"}
    assert iaa_nhom.gia_tri([don], "tat") == {"show_banner_home": "false"}


def test_thu_tu_high_fail_roi_moi_goi_thuong_la_pass():
    log = _log(_dong(1.0, "track_ad_request", LOADING.high.id), _dong(2.0, "ad_load", LOADING.high.id, "failed"),
               _dong(2.1, "track_ad_request", LOADING.thuong.id), _dong(4.0, "ad_load", LOADING.thuong.id))
    ev = iaa_cham_log.su_kien(log, iaa_nhom.ban_do_unit(DS))
    assert iaa_cham_log.cham_thu_tu(ev, 1, LOADING.high.id, LOADING.thuong.id)[0] == "PASS"


def test_hai_ad_song_song_moi_cai_high_fail_roi_thuong_la_pass():
    """Man Uninstall AIP893: native show + preload man sau -> 2 request high, 2 fail, 2 request thuong."""
    h, t = LOADING.high.id, LOADING.thuong.id
    log = _log(_dong(1.0, "track_ad_request", h), _dong(1.1, "track_ad_request", h), _dong(2.6, "ad_load", h, "failed"),
               _dong(2.6, "track_ad_request", t), _dong(3.1, "ad_load", h, "failed"), _dong(3.1, "track_ad_request", t))
    ev = iaa_cham_log.su_kien(log, iaa_nhom.ban_do_unit(DS))
    assert iaa_cham_log.cham_thu_tu(ev, 1, h, t)[0] == "PASS"


def test_high_fill_ma_van_goi_thuong_la_fail():
    h, t = LOADING.high.id, LOADING.thuong.id
    log = _log(_dong(1.0, "track_ad_request", h), _dong(2.0, "ad_load", h), _dong(2.1, "track_ad_request", t))
    ev = iaa_cham_log.su_kien(log, iaa_nhom.ban_do_unit(DS))
    assert iaa_cham_log.cham_thu_tu(ev, 1, h, t)[0] == "FAIL"


def test_banner_khong_ghi_load_fail_cua_high_van_pass():
    """Banner Home AIP893: high request -> goi thuong, KHONG co dong ad_load failed cua high."""
    log = _log(_dong(1.0, "track_ad_request", LOADING.high.id), _dong(2.5, "track_ad_request", LOADING.thuong.id),
               _dong(11.0, "track_ad_request", LOADING.high.id), _dong(12.4, "track_ad_request", LOADING.thuong.id))
    ev = iaa_cham_log.su_kien(log, iaa_nhom.ban_do_unit(DS))
    assert iaa_cham_log.cham_thu_tu(ev, 1, LOADING.high.id, LOADING.thuong.id)[0] == "PASS"


def test_log_threadtime_van_doc_duoc_gio():
    dong = ("11-13 14:11:07.327  7191 30944 V FA-SVC  : Logging event: origin=app,name=track_ad_request,"
            f"params=Bundle[{{adunitid={LOADING.high.id}, ad_format=NATIVE}}]")
    ev = iaa_cham_log.su_kien(dong, iaa_nhom.ban_do_unit(DS))
    assert len(ev) == 1 and ev[0]["t"] > 0


def test_goi_thuong_khi_high_da_fill_la_fail():
    log = _log(_dong(1.0, "track_ad_request", LOADING.high.id), _dong(1.5, "ad_load", LOADING.high.id),
               _dong(1.6, "track_ad_request", LOADING.thuong.id))
    ev = iaa_cham_log.su_kien(log, iaa_nhom.ban_do_unit(DS))
    kq = iaa_cham_log.cham_thu_tu(ev, 1, LOADING.high.id, LOADING.thuong.id)
    assert kq[0] == "FAIL" and "high đã fill" in kq[1]


def test_log_chung_may_chi_lay_unit_cua_vi_tri():
    """Log FA-SVC chung ca may (app khac cung chay): unit la khong duoc tinh."""
    log = _log(_dong(1.0, "track_ad_request", "ca-app-pub-1/999"), _dong(2.0, "track_ad_request", STYLE.high.id))
    ev = iaa_cham_log.su_kien(log, iaa_nhom.ban_do_unit(DS))
    assert [e["vi_tri"] for e in ev] == [2]


def test_cham_ca_bon_bien_the_tu_log():
    bat = _log(_dong(1.0, "track_ad_request", LOADING.high.id), _dong(1.5, "ad_load", LOADING.high.id, "failed"),
               _dong(1.6, "track_ad_request", LOADING.thuong.id), _dong(3.0, "ad_load", LOADING.thuong.id),
               _dong(3.1, "ad_show", LOADING.thuong.id),
               _dong(5.0, "track_ad_request", STYLE.high.id), _dong(6.0, "ad_load", STYLE.high.id))
    thuong = _log(_dong(1.0, "track_ad_request", LOADING.thuong.id), _dong(2.0, "ad_load", LOADING.thuong.id, "failed"),
                  _dong(3.0, "track_ad_request", STYLE.high.id))           # style: van request tang high da tat
    tat = _log(_dong(1.0, "track_ad_request", STYLE.thuong.id))            # loading: 0 event; style: con request
    kq = {(m, d): (k, ly) for m, d, k, ly in cli_iaa.ket_qua(DS, {"bat": bat, "thuong": thuong, "tat": tat})}
    assert kq[("IAA-01-01", 0)][0] == "PASS" and kq[("IAA-02-01", 0)][0] == "PASS"
    assert kq[("IAA-01-02", 1)][0] == "PASS"
    # "Co fill thi ... hien thi" ma kho khong fill: chua kiem duoc hien thi -> BLOCKED (luat 13/11/2026)
    assert kq[("IAA-01-02", 2)][0] == "BLOCKED" and "không fill" in kq[("IAA-01-02", 2)][1]
    assert kq[("IAA-02-02", 1)][0] == "FAIL"
    assert kq[("IAA-01-04", 1)][0] == "PASS" and kq[("IAA-01-04", 2)][0] == "PASS"
    assert kq[("IAA-02-04", 1)][0] == "FAIL"


def test_tat_khong_pass_khi_luot_bat_chua_toi_vi_tri():
    """0 request chi la bang chung khi lan lai cung duong (bien the bat) da toi vi tri."""
    kq = cli_iaa.ket_qua(DS, {"tat": _log()})
    assert kq == []
    bat = _log(_dong(1.0, "track_ad_request", LOADING.high.id))
    kq = {m for m, *_ in cli_iaa.ket_qua(DS, {"bat": bat, "tat": _log()})}
    assert "IAA-01-04" in kq and "IAA-02-04" not in kq


def test_banner_reload_chu_ky_truoc_high_fill_khong_tinh_vao_chu_ky_sau():
    """Banner reload 10s: chu ky 1 high fill (khong goi thuong); chu ky 2 high khong ve -> goi thuong la dung."""
    log = _log(_dong(1.0, "track_ad_request", LOADING.high.id), _dong(3.0, "ad_load", LOADING.high.id),
               _dong(13.0, "track_ad_request", LOADING.high.id), _dong(15.0, "track_ad_request", LOADING.thuong.id))
    ev = iaa_cham_log.su_kien(log, iaa_nhom.ban_do_unit(DS))
    assert iaa_cham_log.cham_thu_tu(ev, 1, LOADING.high.id, LOADING.thuong.id)[0] == "PASS"


def test_duong_lai_aip893_khai_du_doan_va_buoc_hop_le():
    """Moi buoc trong data/iaa_duong_lai.yaml phai la loai buoc iaa_lai / rating_cong_thuc hieu duoc."""
    from rcr import iaa_lai
    hop_le = {"ve_chu", "tap_neu_co", "cho", "back", "mo_lai", "dong_ad", "shortcut", "nhap", "xem_ads_chu", "ve_man", "dong_neu_co",
              "tap", "tap_duoi", "cho_man", "cho_chu", "chon_anh", "xem_ads", "tap_toa_do", "cap_quyen"}
    for pkg in ("com.aiphotogenerator.aivideomaker.photoslideshow", "fitness.workout.aitraining.abs.exercises"):
        doan = iaa_lai.duong_lai(pkg)
        assert doan and all(d.get("ten") and d.get("buoc") for d in doan)
        for d in doan:
            for b in d["buoc"]:
                assert hop_le & set(b), (d["ten"], b)


def test_nhan_shortcut_khop_ca_long_label():
    """vivo V2143 AIP921: shortLabel 'Uninstall' nhung popup launcher ghi longLabel 'Uninstall app'."""
    import asyncio
    from rcr import iaa_lai

    class May:
        async def shell(self, *_a):
            return ("ShortcutInfo {id=shortcut_uninstall, flags=0x85\n packageName=fitness.x\n"
                    " shortLabel=Uninstall, resId=0[null]\n longLabel=Uninstall app, resId=0[null]\n"
                    "ShortcutInfo {id=shortcut_uninstall, flags=0x85\n packageName=com.khac\n"
                    " shortLabel=Uninstall, resId=0[null]\n longLabel=null, resId=0[null]\n", "", 0)
    assert asyncio.run(iaa_lai.cac_nhan_shortcut(May(), "S", "fitness.x", ".*uninstall.*")) == ["Uninstall", "Uninstall app"]
    assert asyncio.run(iaa_lai.cac_nhan_shortcut(May(), "S", "com.khac", ".*uninstall.*")) == ["Uninstall"]


def test_buoc_neu_co_bo_qua_khi_khong_co_chu_va_tap_toa_do_khi_co():
    """Nut Compose bounds rong ('Continue'): `neu_co` thay chu (ke ca bounds rong) thi bam theo ti le man hinh."""
    import asyncio
    from rcr import device_app, iaa_lai, rating_cong_thuc
    from rcr.ui_dump import parse_dump

    xml = ('<hierarchy><node text="Continue" resource-id="" class="android.widget.TextView" package="p" '
           'content-desc="" clickable="false" bounds="[0,0][0,0]" /></hierarchy>')
    bam: list = []

    class May:
        async def shell(self, *a):
            return ("Physical size: 1080x2408\n" if "wm" in a else "", "", 0)

    async def focus(*_a):
        return "p", "p.MainActivity"

    async def nodes(*_a):
        return parse_dump(xml)

    async def tap(_c, _s, x, y):
        bam.append((x, y))

    cu = (device_app.focus, rating_cong_thuc._nodes, device_app.tap)
    device_app.focus, rating_cong_thuc._nodes, device_app.tap = focus, nodes, tap
    try:
        b = {"tap_toa_do": [0.5, 0.943], "neu_co": "^Continue$", "cho_sau": 0}
        assert asyncio.run(iaa_lai.buoc(May(), "S", "p", b, []))
        assert bam == [(540, 2270)]
        assert asyncio.run(iaa_lai.buoc(May(), "S", "p", {**b, "neu_co": "^Enter app$"}, []))
        assert len(bam) == 1
    finally:
        device_app.focus, rating_cong_thuc._nodes, device_app.tap = cu


def test_nhap_tim_o_theo_class_khi_o_khong_co_chu_goi_y():
    """AIP932 AI Tutor: o chat la EditText text="" (khong lo chu goi y) -> `o_lop` tim theo class, go chu vao do."""
    import asyncio
    from rcr import device_app, iaa_lai, rating_cong_thuc
    from rcr.ui_dump import parse_dump

    xml = ('<hierarchy><node text="Moss" resource-id="" class="android.widget.TextView" package="p" '
           'content-desc="" clickable="false" bounds="[236,103][328,147]" />'
           '<node text="" resource-id="" class="android.widget.EditText" package="p" '
           'content-desc="" clickable="true" bounds="[64,1363][552,1442]" /></hierarchy>')
    bam: list = []
    lenh: list = []

    class May:
        async def shell(self, *a):
            lenh.append(a)
            return ("", "", 0)

    async def focus(*_a):
        return "p", "p.MainActivity"

    async def nodes(*_a):
        return parse_dump(xml)

    async def tap(_c, _s, x, y):
        bam.append((x, y))

    async def ngu(*_a):
        return None

    cu = (device_app.focus, rating_cong_thuc._nodes, device_app.tap, iaa_lai.asyncio.sleep)
    device_app.focus, rating_cong_thuc._nodes, device_app.tap = focus, nodes, tap
    iaa_lai.asyncio.sleep = ngu
    try:
        assert asyncio.run(iaa_lai.buoc(May(), "S", "p", {"nhap": "hello", "o_lop": "EditText$"}, []))
        assert bam == [(308, 1402)]
        assert any(a[1:] == ("input", "text", "hello") for a in lenh)
        assert not asyncio.run(iaa_lai.buoc(May(), "S", "p", {"nhap": "hello", "o_lop": "SearchView$"}, []))
    finally:
        device_app.focus, rating_cong_thuc._nodes, device_app.tap, iaa_lai.asyncio.sleep = cu


def test_nhan_shortcut_lay_theo_id_cua_dung_app():
    """Shortcut 'uninstall' cua AIP893 tren may tieng Viet ten 'Go cai dat' - trung chu lenh go cua launcher."""
    import asyncio
    from rcr import iaa_lai

    class May:
        async def shell(self, *_a):
            return ("ShortcutInfo {id=uninstall, flags=0x85\n packageName=com.khac\n shortLabel=Uninstall, resId=0\n"
                    "ShortcutInfo {id=uninstall, flags=0x85\n packageName=com.aiphotogenerator.x\n"
                    " shortLabel=Gỡ cài đặt, resId=0[null]\n", "", 0)
    assert asyncio.run(iaa_lai.nhan_shortcut(May(), "S", "com.aiphotogenerator.x", "uninstall")) == "Gỡ cài đặt"
    assert asyncio.run(iaa_lai.nhan_shortcut(May(), "S", "com.aiphotogenerator.x", "rate")) == ""


def _vong_fail(t: float, vi_tri=STYLE) -> list[str]:
    """Mot luot load fail ca hai tang: high request -> fail -> thuong request -> fail."""
    h, n = vi_tri.high.id, vi_tri.thuong.id
    return [_dong(t, "track_ad_request", h), _dong(t + 1, "ad_load", h, "failed"),
            _dong(t + 1.1, "track_ad_request", n), _dong(t + 2, "ad_load", n, "failed")]


def test_fail_time_dem_tu_lan_fail_dau_du_3_lan_thi_thoi_la_pass():
    """inter_style_fail_time=3: preload fail la lan 1, them 2 lan fail nua roi khong request lai -> PASS."""
    ev = iaa_cham_log.su_kien(_log(*_vong_fail(1), *_vong_fail(20), *_vong_fail(40)), iaa_nhom.ban_do_unit(DS))
    ket, ly = iaa_cham_log.cham_fail_time(ev, 2, 3)
    assert ket == "PASS" and "fail đủ 3 lần" in ly


def test_fail_time_con_request_sau_lan_fail_thu_n_la_fail():
    ev = iaa_cham_log.su_kien(_log(*_vong_fail(1), *_vong_fail(20), *_vong_fail(40), *_vong_fail(60)),
                              iaa_nhom.ban_do_unit(DS))
    ket, ly = iaa_cham_log.cham_fail_time(ev, 2, 3)
    assert ket == "FAIL" and "vẫn request lại 2 lần" in ly


def test_fail_time_chua_du_n_lan_fail_thi_chua_ket_luan():
    ev = iaa_cham_log.su_kien(_log(*_vong_fail(1), *_vong_fail(20)), iaa_nhom.ban_do_unit(DS))
    assert iaa_cham_log.cham_fail_time(ev, 2, 3) is None
    assert iaa_cham_log.cham_fail_time(ev, 2, 0) is None


def test_fail_time_mot_tang_dem_fail_cua_tang_do():
    h = STYLE.high.id
    ev = iaa_cham_log.su_kien(_log(*[d for t in (1, 20) for d in (_dong(t, "track_ad_request", h),
                                                                   _dong(t + 1, "ad_load", h, "failed"))]),
                              iaa_nhom.ban_do_unit(DS))
    assert iaa_cham_log.cham_fail_time(ev, 2, 2)[0] == "PASS"


def test_dong_hien_thi_theo_id_khong_fill_la_blocked():
    """'Co fill thi Banner van hien thi' chi co request, khong load -> BLOCKED; dong request van PASS."""
    from rcr import assert_ad_theo_id
    units = [{"unit": "*****352", "requested": 1, "loaded": 0, "shown": 0}]
    drive = {"status": "DONE"}
    hien = assert_ad_theo_id.cham_theo_case("Có fill thì Banner vẫn hiển thị tại Home.", units, drive, ["5660837352"],
                                           False)
    assert hien["verdict"] == "BLOCKED"
    req = assert_ad_theo_id.cham_theo_case("Unit của vị trí được gọi.", units, drive, ["5660837352"], False)
    assert req["verdict"] == "PASS"


def test_shortcut_chi_nhan_giu_icon_app_khong_nhan_giu_widget():
    """Pixel 6 AIP893 16/11/2026: widget cua app mang dung ten app -> tool nhan giu widget, popup khong co Uninstall."""
    from rcr import iaa_lai
    from rcr.ui_dump import Bounds, DeviceNode
    L = "com.google.android.apps.nexuslauncher"
    ten = "Synza: AI Photo Generator"

    def n(i, cls, text="", desc="", b=(0, 0, 10, 10), cha=None):
        return DeviceNode(i, "", cls, text, desc, Bounds(*b), True, True, True, L, cha, 0)
    nodes = [
        n("0", "android.widget.FrameLayout", desc=ten, b=(40, 200, 1040, 620)),                 # widget cua app
        n("1", "android.appwidget.AppWidgetHostView", b=(40, 700, 1040, 900)),
        n("1.0", "android.widget.TextView", text=ten, b=(60, 720, 600, 780), cha="1"),          # chu trong widget
        n("2", "android.widget.TextView", text=ten, desc=f"{ten}, has 1 notification", b=(441, 107, 640, 416)),
    ]
    import re
    assert [x.node_id for x in iaa_lai._icon_app(nodes, f"^{re.escape(ten)}$")] == ["2"]


def test_doan_hong_cua_bien_the_dau_dung_luot_som():
    """Khuon moi: bien the dau hong doan nao thi dung, khong chay 3 bien the sau (~20 phut moi bien the)."""
    assert cli_iaa.doan_hong({"doan": [{"ten": "home", "xong": True}, {"ten": "reward", "xong": False}]}) == ["reward"]
    assert cli_iaa.doan_hong({"doan": [{"ten": "home", "xong": True}]}) == []
    assert cli_iaa.doan_hong(None) == []


def test_load_ok_ma_khong_show_la_dat():
    """QA chot 17/11/2026: request + load ok dung unit ma khong show -> dong hien thi PASS, khong FAIL/BLOCKED."""
    ev = [{"t": 1.0, "ten": "track_ad_request", "unit": "u1", "vi_tri": 0, "tang": "high", "ok": True},
          {"t": 2.0, "ten": "ad_load", "unit": "u1", "vi_tri": 0, "tang": "high", "ok": True}]
    ra = dict((n, (k, ly)) for n, k, ly in iaa_cham_log.cham_mot_tang(ev, 0, "high", "thuong", "u1", "u2", True))
    assert ra[1][0] == "PASS" and ra[2][0] == "PASS" and "load ok" in ra[2][1]


def test_config_cua_case_cho_report():
    """Report IAA ghi đúng key rcr-iaa đã đặt cho vị trí của case (không còn "không đặt key nào")."""
    cfg = iaa_nhom.config_cua_case(DS, "IAA-01-01")
    assert cfg and set(cfg.values()) == {"true"}
    tat = iaa_nhom.config_cua_case(DS, "IAA-01-04")
    assert tat and set(tat.values()) == {"false"}
    assert iaa_nhom.config_cua_case(DS, "widget#W1") == {}


def test_shortcut_bi_che_tren_samsung():
    """Samsung One UI ghi id / nhan shortcut la '***' -> dung nhan khai trong khuon (`nhan:`)."""
    from rcr import iaa_lai
    che = ("ShortcutInfo {id=***, flags=0x85\n  packageName=p.app\n  shortLabel=***, resId=0\n"
           "ShortcutInfo {id=***, flags=0x85\n  packageName=khac.app\n")
    ro = "ShortcutInfo {id=uninstall, flags=0x85\n  packageName=p.app\n  shortLabel=Uninstall, resId=0\n"
    assert iaa_lai.bi_che(che, "p.app")
    assert not iaa_lai.bi_che(ro, "p.app")
    assert not iaa_lai.bi_che(che, "khong.co")


def test_tap_toa_do_y_theo_tam_chu_khong_theo_ti_le_co_dinh():
    """Pixel 7 AIP916 19/11/2026: y 0.794 cham mep tren nut 'Still want to uninstall' [1901..2011] -> khong vao man Why."""
    from rcr import iaa_lai
    from rcr.ui_dump import Bounds, DeviceNode
    P = "photomaker.image.editor.ai"
    nodes = [
        DeviceNode("0", "", "android.widget.TextView", "Don't uninstall yet", "", Bounds(331, 1767, 749, 1827),
                   True, True, True, P, None, 0),
        DeviceNode("1", "", "android.widget.TextView", "Still want to uninstall", "", Bounds(302, 1943, 778, 2003),
                   True, True, True, P, None, 0),
        DeviceNode("2", "", "android.widget.TextView", "Still want to uninstall", "", Bounds(0, 0, 0, 0),
                   True, True, True, P, None, 0),
    ]
    assert iaa_lai.y_tam_node(nodes, "^Still want to uninstall$") == 1973
    assert iaa_lai.y_tam_node(nodes, "^Why do you uninstall\\?$") is None


def test_shortcut_ngan_keo_pixel_go_tu_dau_va_bam_dong_chu(monkeypatch):
    """Pixel 4 AIP508 19/11/2026: go du ten 'Homova - AI Home Design' chi ra icon (khong ra dong shortcut); go tu
    dau 'Homova' moi ra dong 'Uninstall' - nam duoi ban phim (bam la trung phim) va bam vao icon thi khong mo."""
    import asyncio
    from rcr import device_app, iaa_lai, ui_dump
    from rcr.ui_dump import Bounds, DeviceNode
    L = "com.google.android.apps.nexuslauncher"
    ten = "Homova - AI Home Design"

    def n(i, text="", desc="", b=(0, 0, 10, 10)):
        return DeviceNode(i, "", "android.widget.TextView", text, desc, Bounds(*b), True, True, True, L, None, 0)
    o_tim = n("s", desc="Search your phone", b=(0, 113, 1080, 302))
    chi_icon = [o_tim, n("a", ten, ten, (41, 323, 241, 632))]
    co_dong = chi_icon + [n("u1", "", "Uninstall", (89, 1268, 185, 1364)), n("u2", "Uninstall", "", (209, 1281, 411, 1351))]
    st = {"go": "", "ban_phim": True, "tap": [], "back": 0}

    class C:
        async def shell(self, serial, *args):
            if args[:2] == ("input", "text"):
                st["go"] = args[2].strip("'")
                st["ban_phim"] = True
            if args[:2] == ("input", "keyevent") and args[2] == "KEYCODE_BACK":
                st["back"] += 1
                st["ban_phim"] = False
            if args[:1] == ("dumpsys",):
                return (f"mInputShown={'true' if st['ban_phim'] else 'false'}", "", 0)
            return ("", "", 0)

    async def dump(c, s, *a):
        return "tu_dau" if st["go"] == "Homova" else "du_ten"

    async def tap(c, s, x, y):
        st["tap"].append((x, y))

    async def focus(c, s):
        return ("p.app", "p.app.SplashActivity") if (310, 1316) in st["tap"] else (L, "Launcher")

    async def size(c, s):
        return (1080, 2280)
    monkeypatch.setattr(ui_dump, "dump", dump)
    monkeypatch.setattr(ui_dump, "parse_dump", lambda x: co_dong if x == "tu_dau" else chi_icon)
    monkeypatch.setattr(device_app, "tap", tap)
    monkeypatch.setattr(device_app, "focus", focus)
    monkeypatch.setattr(device_app, "screen_size", size)
    import re
    log: list[str] = []
    kq = asyncio.run(iaa_lai._shortcut_ngan_keo(C(), "S", "p.app", f"^{re.escape(ten)}$", ["Uninstall"],
                                                "^(Uninstall)$", log))
    assert kq is True
    assert st["tap"][-1] == (310, 1316)          # dong chu, khong phai icon (137,1316)
    assert st["back"] >= 1                       # an ban phim truoc khi doc ket qua


def test_lai_khong_crash_khi_logcat_da_tu_thoat(monkeypatch, tmp_path):
    """Pixel 4 19/11/2026: adb logcat tu thoat truoc -> terminate() nem ProcessLookupError, rcr-iaa crash sau khi
    lai xong bien the (config khong duoc tra). Phai bo qua, tra ket qua doan binh thuong; logcat chet giua luot thi
    ghi tiep tu moc cuoi (-T), khong dump lai ca buffer."""
    import asyncio
    from rcr import iaa_lai
    goi: list = []
    that = asyncio.sleep

    class P:
        returncode = 1                      # da chet ngay tu dau

        def terminate(self):
            raise ProcessLookupError()

        async def wait(self):
            return 0

    async def tao(*a, **k):
        goi.append(a)
        k["stdout"].write("         1795081059.478 14729  4775 V FA-SVC  : x\n")
        return P()

    async def ngu(giay, *a):
        await that(0)

    class C:
        adb = "adb"

        async def shell(self, *a):
            return ("", "", 0)
    monkeypatch.setattr(asyncio, "create_subprocess_exec", tao)
    monkeypatch.setattr(asyncio, "sleep", ngu)
    kq = asyncio.run(iaa_lai.lai(C(), "S", "p.app", [{"ten": "cho", "buoc": [{"cho": 0}] * 10}],
                                tmp_path / "x.log"))
    assert kq["doan"][0]["xong"] is True
    assert "-T" not in goi[0]
    assert any("-T" in g and "1795081059.479" in g for g in goi[1:])
    assert iaa_lai.moc_cuoi_log(tmp_path / "khong_co.log") is None


def test_tap_khi_rong_bam_theo_ti_le_khi_chu_co_bounds_rong(monkeypatch):
    """AIP508 Homova Pixel 4 19/11/2026: tat banner -> nav bar tut xuong, chu "AI CHAT" co bounds rong -> bam theo
    `khi_rong`; co bounds thi bam dung node; khong co chu thi KHONG bam mu (vung do luc co banner la banner ad)."""
    import asyncio
    from rcr import device_app, iaa_lai, rating_cong_thuc
    from rcr.ui_dump import Bounds, DeviceNode
    P = "p.app"
    st = {"nodes": [], "tap": []}

    def n(b):
        return DeviceNode("0", "", "android.widget.TextView", "AI CHAT", "", Bounds(*b), True, True, True, P, None, 0)

    async def nodes(c, s, p):
        return st["nodes"]

    async def tap(c, s, x, y):
        st["tap"].append((x, y))

    class C:
        async def shell(self, serial, *a):
            return ("Physical size: 1080x2280", "", 0)

    async def ngu(*_a):
        return None
    monkeypatch.setattr(rating_cong_thuc, "_nodes", nodes)
    monkeypatch.setattr(device_app, "tap", tap)
    b = {"tap": "^AI CHAT$", "khi_rong": [0.205, 0.93], "toi_da": 0.01}
    st["nodes"] = [n((0, 0, 0, 0))]
    assert asyncio.run(iaa_lai.buoc(C(), "S", P, b, []))
    assert st["tap"][-1] == (221, 2120)
    st["nodes"] = [n((160, 1991, 288, 2030))]
    assert asyncio.run(iaa_lai.buoc(C(), "S", P, b, []))
    assert st["tap"][-1] == (224, 2010)
    st["nodes"], st["tap"] = [], []
    monkeypatch.setattr(asyncio, "sleep", ngu)
    assert not asyncio.run(iaa_lai.buoc(C(), "S", P, b, []))
    assert st["tap"] == []


def test_unit_that_thay_id_sheet_lech_build_va_cham_theo_unit_that():
    """AIP933 Hypix 20/11/2026: ID muc 3 sheet KT vang trong APK -> cham theo ID sheet thi moi vi tri 0 request."""
    import pytest
    from rcr.models import RcError
    that_h, that_t = f"{PUB}/1704598632", f"{PUB}/7239996344"
    ds, doi = iaa_nhom.ap_unit_that(DS, {"native_loading_high": that_h, "native_loading": that_t})
    assert ds[0].high.id == that_h and ds[0].thuong.id == that_t and ds[0].high.key == "show_native_loading_high"
    assert ds[1] is STYLE and len(doi) == 2 and DS[0].high.id != that_h     # khong sua ds goc
    log = _log(_dong(100.0, "track_ad_request", that_h), _dong(100.4, "ad_load", that_h, "failed"),
               _dong(100.5, "track_ad_request", that_t), _dong(101.0, "ad_load", that_t))
    assert {e["vi_tri"] for e in iaa_cham_log.su_kien(log, iaa_nhom.ban_do_unit(ds))} == {1}
    assert iaa_cham_log.su_kien(log, iaa_nhom.ban_do_unit(DS)) == []
    with pytest.raises(RcError):
        iaa_nhom.ap_unit_that(DS, {"native_loadin_high": that_h})       # go sai ten ad -> dung, khong cham nham
    assert cli_iaa._cap_unit([f"inter_style={PUB}/1"]) == {"inter_style": f"{PUB}/1"}
    with pytest.raises(RcError):
        cli_iaa._cap_unit(["inter_style=1542026074"])


def test_rc_them_cua_khuon_dat_cung_moi_bien_the(monkeypatch):
    """Hypix: shortcut Uninstall chi co khi enabled_flow_uninstall=true -> khuon khai rc_them, dat ca 4 bien the."""
    from rcr import iaa_khuon
    data = {"khuon": {"k1": {"nhan_dien": "^X$", "rc_them": {"enabled_flow_uninstall": True}, "doan": []}},
            "p.a": {"khuon": "k1"}, "p.b": {"khuon": "k1", "rc_them": {"x": 1}}, "p.c": []}
    monkeypatch.setattr(iaa_khuon, "_doc", lambda: data)
    assert iaa_khuon.rc_them("p.a") == {"enabled_flow_uninstall": "true"}
    assert iaa_khuon.rc_them("p.b") == {"enabled_flow_uninstall": "true", "x": "1"}
    assert iaa_khuon.rc_them("p.c") == {} and iaa_khuon.rc_them("p.khong") == {}


def test_khuon_hypix_ghim_package_va_bat_luong_uninstall():
    from rcr import iaa_khuon
    pkg = "com.ai.videogenerator.photocreator.aiart"
    nguon, doan = iaa_khuon.doan_khai_san(pkg)
    assert nguon == "khuôn hypix" and any("Uninstall" in d["ten"] for d in doan)
    assert iaa_khuon.rc_them(pkg) == {"enabled_flow_uninstall": "true"}
    import re
    tap = [b["tap"] for d in doan for b in d["buoc"] if "tap" in b]
    assert any(re.search(t, "Image to Image\nGenerate") for t in tap)        # chu the carousel co xuong dong


def test_tap_vua_hien_chi_bam_khi_the_carousel_vua_xoay_toi(monkeypatch):
    """Hypix AIP933 20/11/2026: carousel tu xoay ~4s, bam the da hien tu truoc thi trung luc chuyen the -> vao nham
    T2I thanh I2I. `vua_hien`: bo qua lan thay dau neu the da hien san, chi bam o lan dump ngay sau lan vang."""
    import asyncio
    from rcr import device_app, rating_cong_thuc
    from rcr.ui_dump import Bounds, DeviceNode
    P = "p.app"
    the = DeviceNode("0", "", "android.widget.TextView", "Text to Image\nGenerate", "", Bounds(110, 663, 527, 822),
                     True, True, True, P, None, 0)
    chuoi = [[the], [the], [], [the], [the]]          # dang hien -> xoay di -> vua xoay toi
    st = {"i": 0, "tap": []}

    async def nodes(c, s, p):
        st["i"] += 1
        return chuoi[min(st["i"] - 1, len(chuoi) - 1)]

    async def tap(c, s, x, y):
        st["tap"].append(st["i"])

    async def ngu(*_a):
        return None

    class C:
        async def shell(self, serial, *a):
            return ("Physical size: 1080x2400", "", 0)
    monkeypatch.setattr(rating_cong_thuc, "_nodes", nodes)
    monkeypatch.setattr(device_app, "tap", tap)
    monkeypatch.setattr(asyncio, "sleep", ngu)
    b = {"tap": r"^Text to Image\sGenerate$", "vua_hien": True}
    assert asyncio.run(rating_cong_thuc._mot_buoc(C(), "S", P, b, []))
    assert st["tap"] == [4]                           # bam o lan dump thu 4 (vua hien lai), khong o lan 1
    st["i"], st["tap"] = 0, []
    assert asyncio.run(rating_cong_thuc._mot_buoc(C(), "S", P, {"tap": b["tap"]}, []))
    assert st["tap"] == [1]                           # khong co vua_hien: bam ngay nhu cu


def test_tap_sau_chu_vao_nham_the_thi_back_bam_lai(monkeypatch):
    """Hypix AIP933 Samsung A13 20/11/2026: `vua_hien` van trung luc carousel doi the -> vao I2I thay T2I.
    `sau_chu`: bam xong chua thay chu man dich thi BACK, cho the hien lai roi bam lai."""
    import asyncio
    from rcr import device_app, rating_cong_thuc
    from rcr.ui_dump import Bounds, DeviceNode
    P = "p.app"

    def nut(chu):
        return DeviceNode("0", "", "android.widget.TextView", chu, "", Bounds(110, 663, 527, 822),
                          True, True, True, P, None, 0)
    the, i2i, t2i = nut("Text to Image\nGenerate"), nut("Image to Image"), nut("Text to Image")
    # bam lan 1 -> vao I2I (3 dump), BACK -> the hien lai -> bam lan 2 -> vao T2I
    chuoi = [[the], [i2i], [i2i], [i2i], [the], [t2i]]
    st = {"i": 0, "tap": [], "back": 0}

    async def nodes(c, s, p):
        st["i"] += 1
        return chuoi[min(st["i"] - 1, len(chuoi) - 1)]

    async def tap(c, s, x, y):
        st["tap"].append(st["i"])

    async def focus(c, s):
        return P, "MainActivity"

    async def ngu(*_a):
        return None

    class C:
        async def shell(self, serial, *a):
            if "KEYCODE_BACK" in a:
                st["back"] += 1
            return ("Physical size: 1080x2400", "", 0)
    monkeypatch.setattr(rating_cong_thuc, "_nodes", nodes)
    monkeypatch.setattr(device_app, "tap", tap)
    monkeypatch.setattr(device_app, "focus", focus)
    monkeypatch.setattr(asyncio, "sleep", ngu)
    b = {"tap": r"^Text to Image\sGenerate$", "sau_chu": "^Text to Image$"}
    assert asyncio.run(rating_cong_thuc._mot_buoc(C(), "S", P, b, []))
    assert st["tap"] == [1, 5] and st["back"] == 1


def test_vuot_xuong_keo_ve_dau_trang_vuot_len_cuon_len(monkeypatch):
    """Home AIP919 mo ra da cuon qua the I2I/I2V: `vuot_xuong` keo 30% -> 80% chieu cao; `vuot_len` giu 60% -> 30%."""
    import asyncio
    from rcr import iaa_lai

    lenh: list = []

    class May:
        async def shell(self, _s, *a, **_k):
            lenh.append(a)
            return ("Physical size: 1000x2000\n" if "wm" in a else "", "", 0)

    async def ngu(_s):
        return None

    monkeypatch.setattr(iaa_lai.asyncio, "sleep", ngu)
    log: list = []
    assert asyncio.run(iaa_lai.buoc(May(), "S", "p", {"vuot_xuong": 2}, log))
    vuot = [a for a in lenh if "swipe" in a]
    assert vuot == [("input", "swipe", "500", "600", "500", "1600", "400")] * 2
    assert log[-1] == "vuốt xuống ×2"
    lenh.clear()
    assert asyncio.run(iaa_lai.buoc(May(), "S", "p", {"vuot_len": 1}, log))
    assert [a for a in lenh if "swipe" in a] == [("input", "swipe", "500", "1200", "500", "600", "400")]
