"""Dem event quang cao trong log FA-SVC."""

from __future__ import annotations

from rcr import fa_log


def test_dem_ad_click_cua_sdk_quang_cao():
    """Do 24/10/2026: BACK tren inter that -> 2 dong ad_click(_ac), origin=am."""
    log = "\n".join(
        "V FA-SVC  : Logging event: origin=am,name=ad_click(_ac),params=Bundle[{ga_event_origin(_o)=am, "
        f"_r=1, ga_screen_class(_sc)=AdActivity, ad_event_id(_aeid)={i}}}]" for i in (556, 557))
    events = fa_log.parse(log)
    assert fa_log.ad_clicks(events) == 2


def test_khong_co_ad_click_thi_bang_0():
    log = ("V FA-SVC  : Logging event: origin=app,name=ad_show,params=Bundle[{ad_format=native, "
           "show_status=success}]")
    assert fa_log.ad_clicks(fa_log.parse(log)) == 0
