"""Giu / tra mang app theo man (tuong lua Android 13+) de ad cua man dich ve MUON.

AIP872 1.9.0 (09/11/2026): tre co dinh khong du - 202 preload tu inter splash, 303 tu OB1, nen den man dich
ad da nam san (S03-01, S04-01 BLOCKED). Proxy HTTP khong giu duoc vi GMA tai ad bang QUIC di thang.
"""
from __future__ import annotations

import asyncio

from rcr import mang_cham_cua_so as cs


def test_ke_hoach_chan_truoc_luc_preload_mot_nhip():
    assert cs.ke_hoach("lfo2") == {"man": "lfo2", "bat_dau": "spl_inter", "ids": []}
    assert cs.ke_hoach("ob3") == {"man": "ob3", "bat_dau": "lfo2", "ids": []}
    assert cs.ke_hoach("ob4")["bat_dau"] == "ob2"
    assert cs.ke_hoach("") is None
    assert "lúc inter splash hiện" in cs.mo_ta(cs.ke_hoach("lfo2"))


def _cua_so(man):
    return cs.CuaSo(None, "S", "com.ai.app", cs.ke_hoach(man))


def _log(*names):
    return [f"1794201020.810  1  2 V FA-SVC: Logging event: origin=app,name={n},params=Bundle[{{ga=1}}]"
            for n in names]


def _chay(w, *names):
    for dong in _log(*names):
        w._dong_log(dong)


def test_chan_tu_lfo2_toi_khi_roi_ob3():
    w = _cua_so("ob3")
    _chay(w, "splash_view", "lfo1_view")
    assert w.che_do == "tha"
    _chay(w, "lfo2_view")
    assert w.che_do == "giu"
    _chay(w, "ob1_view", "ob2_view", "ob3_view")
    assert w.che_do == "giu"
    _chay(w, "ob4_view")
    assert w.che_do == "tha" and "rời OB3 sang OB4" in w.lich[-1]
    # Luot lai cua case (app mo lai tu Splash) -> ke hoach chay lai tu dau
    _chay(w, "splash_view", "lfo1_view", "lfo2_view")
    assert w.che_do == "giu"


def test_inter_splash_la_adactivity_ngay_sau_splash():
    w = _cua_so("lfo2")
    act = ("1794201020.810  1719  3628 I ActivityTaskManager: START u0 {xflg=0x4 cmp=com.x/"
           "com.google.android.gms.ads.AdActivity (has extras)} with LAUNCH_MULTIPLE")
    _chay(w, "splash_view")
    w._dong_log(act)
    assert w.che_do == "giu"
    _chay(w, "lfo1_view", "lfo2_view")
    assert w.che_do == "giu"
    _chay(w, "ob1_view")
    assert w.che_do == "tha"
    w._dong_log(act)          # AdActivity muon hon (inter OB5 / resume) khong chan lai
    assert w.che_do == "tha"


def test_inter_splash_khong_fill_thi_chan_tu_lfo1():
    w = _cua_so("lfo2")
    _chay(w, "splash_view", "lfo1_view")
    assert w.che_do == "giu"


def test_doi_che_do_dua_vao_hang_dat_tuong_lua_theo_thu_tu(monkeypatch):
    goi = []

    async def chan(client, serial, package, chan_mang):
        goi.append(chan_mang)
    monkeypatch.setattr(cs.mang_cham, "chan", chan)

    async def kich_ban():
        w = _cua_so("ob3")
        w._hang = asyncio.Queue()
        task = asyncio.ensure_future(w._ap_dung())
        _chay(w, "splash_view", "lfo1_view", "lfo2_view", "ob1_view", "ob3_view", "ob4_view", "ob5_view")
        await asyncio.sleep(0.05)
        task.cancel()
    asyncio.run(kich_ban())
    assert goi == [True, False]


def test_vua_tra_mang_thi_dung_o_man_hung_cho_ad_show(monkeypatch):
    monkeypatch.setattr(cs, "CHO_AD_HUNG_S", 0.6)
    w = _cua_so("lfo2")
    monkeypatch.setattr(cs, "_DANG_CHAY", w)
    assert asyncio.run(cs.cho_ad_ve_muon()) == 0.0          # chua tra mang -> khong cho
    _chay(w, "splash_view", "lfo1_view", "lfo2_view", "ob1_view")
    assert asyncio.run(cs.cho_ad_ve_muon()) >= 0.5          # het gio, khong thay ad_show
    assert asyncio.run(cs.cho_ad_ve_muon()) == 0.0          # mot lan moi luot
    _chay(w, "splash_view", "lfo1_view", "lfo2_view", "ob1_view", "ad_show")
    assert asyncio.run(cs.cho_ad_ve_muon()) < 0.3           # thay ad_show -> di tiep ngay
    assert "ad đã về" in w.lich[-1]


def test_biet_id_thi_cho_dung_ad_load_cua_ad_dich_khong_phai_ad_show_bat_ky(monkeypatch):
    """Pixel 6 09/11/2026: tool di tiep khi 304 show o OB4; 303 ve sau 18s thi OB5 da bi bo qua."""
    monkeypatch.setattr(cs, "CHO_AD_HUNG_S", 0.6)
    w = cs.CuaSo(None, "S", "com.ai.app", cs.ke_hoach("ob3", [ID_303]))
    monkeypatch.setattr(cs, "_DANG_CHAY", w)
    _chay(w, "splash_view", "ob1_view")
    w._dong_log(_request(ID_303))
    _chay(w, "ob3_view", "ob4_view", "ad_show")
    assert not w.thay_show
    w._dong_log("1 2 3 V FA-SVC: Logging event: origin=app,name=ad_load,params=Bundle[{load_status=success, "
                f"ad_unit_id={ID_303}, ga_event_origin(_o)=app}}]")
    assert w.thay_show and asyncio.run(cs.cho_ad_ve_muon()) < 0.3


ID_303 = "ca-app-pub-4973559944609228/8588924034"
ID_202 = "ca-app-pub-4973559944609228/2764762034"


def _request(uid):
    return ("1794201020.810  1  2 V FA-SVC: Logging event: origin=app,name=track_ad_request,params=Bundle[{"
            f"network_status=1, adunitid={uid}, ga_event_origin(_o)=app, ad_format=NATIVE, ad_platform=Admob}}]")


def test_biet_id_thi_chan_dung_luc_app_gui_request_ad_dich():
    """SDK bo request khi app mat mang -> chan theo man truoc luc preload thi 303 khong bao gio duoc request
    (Pixel 6 09/11/2026). Phai chan NGAY SAU request cua chinh ad dich."""
    w = cs.CuaSo(None, "S", "com.ai.app", cs.ke_hoach("ob3", [ID_303]))
    _chay(w, "splash_view", "lfo1_view", "lfo2_view")
    assert w.che_do == "tha"                          # biet ID -> khong chan theo man
    w._dong_log(_request(ID_202))                     # request ad khac (cung duoi …034) khong tinh
    _chay(w, "ob1_view")
    assert w.che_do == "tha"
    w._dong_log(_request(ID_303))
    assert w.che_do == "giu" and "…8588924034" in w.lich[-1]
    _chay(w, "ob2_view", "ob3_view")
    assert w.che_do == "giu"
    _chay(w, "ob4_view")
    assert w.che_do == "tha"
    w._dong_log(_request(ID_303))                     # reload sau khi da tra mang khong chan lai
    assert w.che_do == "tha"


def test_request_ad_dich_sau_khi_qua_man_dich_khong_chan():
    w = cs.CuaSo(None, "S", "com.ai.app", cs.ke_hoach("lfo2", [ID_202]))
    _chay(w, "splash_view", "lfo1_view", "lfo2_view", "ob1_view")
    w._dong_log(_request(ID_202))
    assert w.che_do == "tha"
    assert "lúc app gửi request ad LFO2" in cs.mo_ta(cs.ke_hoach("lfo2", [ID_202]))


def test_di_den_ob4_hoan_thanh_ob4_la_roi_ob4_sang_trang_sau():
    """S04-01 "Đi đến OB4, hoàn thành OB4." - tool tung dung o OB4 toi het case, OB5 khong bao gio hien."""
    from rcr import act_cau_fo

    assert act_cau_fo.resolve("Đi đến OB4, hoàn thành OB4.", []).target == "OnboardingActivity#5"
    assert act_cau_fo.resolve("Đi đến OB4.", []).target == "OnboardingActivity#4"
    assert act_cau_fo.resolve("Hoàn thành OB4.", []).target == act_cau_fo.RA_KHOI_OB
