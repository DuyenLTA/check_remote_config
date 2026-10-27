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


# Log that Lingix 1.5.0, Pixel 6, 24/10/2026: inter 102 …443 show, ~10,2s sau GMA ghi
# 2 ad_click ma khong co lenh input nao; tap Close cua tool den 3s SAU click.
CLICK_LOG = (
    "  1792858541.696 26687  9279 V FA-SVC  : Logging event: origin=am,name=ad_click(_ac),params=Bundle[{"
    "ga_event_origin(_o)=am, _r=1, ga_screen_class(_sc)=AdActivity, ad_event_id(_aeid)=-1}]\n"
    "  1792858541.710 26687  9279 V FA-SVC  : Logging event: origin=am,name=ad_click(_ac),params=Bundle[{"
    "ga_event_origin(_o)=am, _r=1, ga_screen_class(_sc)=AdActivity, ad_event_id(_aeid)=-2}]\n"
)
ADBD_LOG = (
    "  1792858538.613  1750  1750 I adbd    : adbd service requested 'shell,v2,TERM=xterm-256color,"
    "raw:uiautomator dump /data/local/tmp/rcr_uidump.xml'\n"
    "  1792858544.779  1750  1750 I adbd    : adbd service requested 'shell,v2,TERM=xterm-256color,"
    "raw:input tap 223 2271'\n"
)


def test_ad_click_khong_co_thao_tac_nao_truoc_do_la_tu_ban():
    events = fa_log.parse(CLICK_LOG)
    assert events[0]["t"] == 1792858541.696
    assert fa_log.parse_input(ADBD_LOG) == [1792858544.779]   # dump UI khong phai thao tac
    assert fa_log.chia_click(events, fa_log.parse_input(ADBD_LOG)) == (0, 2)


def test_ad_click_ngay_sau_thao_tac_cua_tool_la_do_tool():
    """Piclux 2.4.0: BACK tren inter, 2,2s sau co click."""
    back = ("  1792858539.500  1750  1750 I adbd    : adbd service requested "
            "'shell,v2,TERM=xterm-256color,raw:input keyevent 4'\n")
    assert fa_log.chia_click(fa_log.parse(CLICK_LOG), fa_log.parse_input(ADBD_LOG + back)) == (2, 0)


def test_khong_doc_duoc_gio_thao_tac_thi_tinh_het_la_do_tool():
    events = fa_log.parse(CLICK_LOG)
    assert fa_log.parse_input("") is None
    assert fa_log.chia_click(events, None) == (2, 0)
    khong_gio = fa_log.parse(CLICK_LOG.replace("1792858541.696", "10-24 22:30:41.696"))
    assert fa_log.chia_click(khong_gio, []) == (1, 1)
