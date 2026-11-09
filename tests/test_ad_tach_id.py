"""Tach unit gop vi trung 3 so cuoi ID (AIP872: 202 …2764762034 va 303 …8588924034 deu la `*****034`)."""
from __future__ import annotations

from rcr import ad_tach_id, assert_ad_screen

ID_202 = "ca-app-pub-1/2764762034"
ID_303 = "ca-app-pub-1/8588924034"
GOP = {"native:*****034": {
    "type": "native", "unit": "*****034", "requested": 3, "loaded": 3, "load_failed": 0, "shown": 2,
    "rc_keys": ["id_202_lfo2_n_native_high", "id_303_onb3_n_native_high"],
    "ids": {"id_202_lfo2_n_native_high": [ID_202], "id_303_onb3_n_native_high": [ID_303]}}}


def ev(name, uid, **p):
    key = "adunitid" if name == "track_ad_request" else "ad_unit_id"
    return {"name": name, "params": {key: uid, **p}}


def test_tach_dem_lai_tung_vi_tri_bang_event_id_day_du():
    events = [ev("track_ad_request", ID_202), ev("ad_load", ID_202, load_status="success"), ev("ad_show", ID_202),
              ev("track_ad_request", ID_202), ev("ad_load", ID_202, load_status="success"), ev("ad_show", ID_202),
              ev("track_ad_request", ID_303), ev("ad_load", ID_303, load_status="success")]
    ra = ad_tach_id.tach(GOP, events)
    u202, u303 = ra["native:*****034#202"], ra["native:*****034#303"]
    assert (u202["requested"], u202["loaded"], u202["shown"]) == (2, 2, 2)
    assert (u303["requested"], u303["loaded"], u303["shown"]) == (1, 1, 0)   # 303 ve nhung KHONG show
    assert u303["rc_keys"] == ["id_303_onb3_n_native_high"] and u303["tach_tu"] == "*****034"


def test_load_fail_khong_tinh_la_load():
    ra = ad_tach_id.tach(GOP, [ev("ad_load", ID_303, load_status="fail")])
    assert ra["native:*****034#303"]["loaded"] == 0


def test_app_khong_ban_event_thi_giu_nguyen():
    assert ad_tach_id.tach(GOP, [{"name": "ob1_view"}]) is GOP


def test_loai_event_khong_ban_thi_giu_so_dem_cu():
    ra = ad_tach_id.tach(GOP, [ev("ad_show", ID_303)])
    assert ra["native:*****034#303"]["shown"] == 1 and ra["native:*****034#303"]["requested"] == 3


def test_unit_mot_vi_tri_hoac_thieu_id_khong_tach():
    mot = {"x": {"unit": "*****174", "rc_keys": ["id_102_spl_n_inter_high", "splash_inter_high_n_id"],
                 "ids": {"id_102_spl_n_inter_high": ["ca-app-pub-1/4383472174"]}}}
    assert ad_tach_id.tach(mot, [ev("ad_show", "ca-app-pub-1/4383472174")]) == mot
    thieu = {"x": {**GOP["native:*****034"], "ids": {"id_202_lfo2_n_native_high": [ID_202]}}}
    assert ad_tach_id.tach(thieu, [ev("ad_show", ID_202)]) == thieu


def test_man_show_van_gan_dung_vi_tri_sau_khi_tach():
    ra = list(ad_tach_id.tach(GOP, [ev("ad_show", ID_202)]).values())
    events = [{"name": "ad_show", "params": {"ad_unit_id": ID_303}}, {"name": "ob5_view"}]
    assert [(s["man"], s["vi_tri"]) for s in assert_ad_screen.show_theo_man(events, ra)] == [("ob5", {"303"})]
