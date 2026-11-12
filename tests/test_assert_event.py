"""Cham dong event cua bo TC tinh nang (rating / widget / daily checkin) - cau that tu sheet TC."""

from __future__ import annotations

from rcr.assert_event import event_da_ban

EV = [{"name": "widget_view", "params": {}},
      {"name": "rating_placement_viewed", "params": {"placement_name": "result"}},
      {"name": "ad_impression", "params": {}}]


def test_khong_co_event_vang_mat_la_pass():
    ket = event_da_ban("Không có event daily_checkin_button_clicked.", EV)
    assert ket["verdict"] == "PASS"


def test_khong_co_event_ma_co_ban_la_fail():
    ket = event_da_ban("Không có event widget_view.", EV)
    assert ket["verdict"] == "FAIL" and "1 lần" in ket["reason"]


def test_ten_event_lay_sau_chu_event_khong_lay_token_dau_cau():
    text = "Home, result, exit_click: popup không hiện, không có event rating_placement_viewed."
    ket = event_da_ban(text, [{"name": "ad_impression", "params": {}}])
    # event dung la vang mat, nhung ve "popup khong hien" chua ai do -> khong duoc PASS
    assert ket["verdict"] == "NEEDS_HUMAN" and "rating_placement_viewed" in ket["reason"]


def test_chi_neu_param_khong_doan_ten_event():
    ket = event_da_ban('Result hiện popup; event placement_name = "result".', EV)
    assert ket["verdict"] == "NEEDS_HUMAN"


def test_event_co_param():
    ket = event_da_ban('Event rating_placement_viewed, placement_name = "result".', EV)
    assert ket["verdict"] == "PASS" and "result" in ket["reason"]


def test_event_fire_mot_lan():
    assert event_da_ban("Event widget_view fire 1 lần.", EV)["verdict"] == "PASS"
