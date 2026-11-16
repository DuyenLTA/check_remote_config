"""Precondition 'App bat man Add widget' ma Test Data thieu key -> tool tu dat widget_screen_placement=true."""

from rcr import precondition_config


def test_bat_add_widget_thi_dat_widget_screen_placement():
    wl = {"widget_screen_placement", "show_checkin_screen"}
    assert precondition_config.them("1. Clear data.\n2. App bật màn Add widget.", wl, {}) == \
        {"widget_screen_placement": "true"}
    assert precondition_config.them("2. App bật màn Add widget.", wl, {"widget_screen_placement": "false"}) == {}
    assert precondition_config.them("2. App bật màn Add widget.", set(), {}) == {}
