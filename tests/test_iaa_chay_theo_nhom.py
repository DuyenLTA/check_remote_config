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
    assert kq[("IAA-01-02", 2)][0] == "PASS" and "không fill" in kq[("IAA-01-02", 2)][1]
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
    hop_le = {"ve_chu", "cho", "back", "mo_lai", "dong_ad", "shortcut", "nhap", "xem_ads_chu", "ve_man", "dong_neu_co",
              "tap", "tap_duoi", "cho_man", "cho_chu", "chon_anh", "xem_ads"}
    doan = iaa_lai.duong_lai("com.aiphotogenerator.aivideomaker.photoslideshow")
    assert doan and all(d.get("ten") and d.get("buoc") for d in doan)
    for d in doan:
        for b in d["buoc"]:
            assert hop_le & set(b), (d["ten"], b)


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
