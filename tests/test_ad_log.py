"""Test doc log quang cao. Fixture la DONG LOG THAT do tren may 2026-09-25.

Diem phai gac:
  - ID bi che con 3 so cuoi -> doi chieu voi RC phai theo DUOI, va nhieu key
    cung duoi thi la mo ho, khong chon bua
  - unit khong khop key nao = app hardcode ID (do that: banner splash cua Piclux)
  - dem theo tung unit: request / loaded / fail / shown
"""

from __future__ import annotations

from rcr import ad_log

REAL_LOG = """
09-25 16:00:27.580 32353 32353 D BannerAdHelper: SplashActivity: adBannerState(None)
09-25 16:00:27.582 32353 32353 I AdEventLogger: trackAdShowFailed - adUnitId: *****825  -  adType: banner  -   errorType: ERROR_VIEW
09-25 16:00:27.585 32353 32353 D BannerAdHelper: SplashActivity: adBannerState(Loading)
09-25 16:00:27.591 32353 32353 I AdEventLogger: trackAdRequest adPlatform:Admob  - adUnitId: *****495  -  adType: BANNER
09-25 16:00:27.648 32353 32353 I AdEventLogger: trackAdRequest adPlatform:Admob  - adUnitId: *****588  -  adType: INTERSTITIAL
09-25 16:00:30.173 32353 32353 I AdEventLogger: trackAdLoadSuccess - adUnitId: *****588  -  adType: interstitial  -  wonAdSource: AdMob Network
09-25 16:00:31.042 32353 32353 I AdEventLogger: trackAdShowSuccess - adUnitId: *****588  -  adType: interstitial  -  showStatus: success
09-25 16:00:31.606 32353 32353 I AdEventLogger: trackAdLoadFailed  - adUnitId: *****825  -  adType: banner  -  errorCode: 3  -  errorMessage: No fill.  -  errorDomain: com.google.android.gms.ads
09-25 16:00:31.610 32353 32353 D BannerAdHelper: SplashActivity: adBannerState(Fail)
"""

RC_IDS = {
    "splash_inter_high_n_id": "ca-app-pub-4584260126367940/2920391588",
    "id_101_spl_a_banner": "ca-app-pub-4584260126367940/5682972717",
}


def test_doc_duoc_chuoi_trang_thai_banner():
    parsed = ad_log.parse(REAL_LOG)
    assert [s["state"] for s in parsed["banner_states"]] == ["None", "Loading", "Fail"]
    assert parsed["banner_states"][0]["screen"] == "SplashActivity"


def test_dem_theo_tung_unit():
    units = ad_log.summary(ad_log.parse(REAL_LOG))
    inter = units["interstitial:*****588"]
    assert (inter["requested"], inter["loaded"], inter["shown"]) == (1, 1, 1)
    banner = units["banner:*****825"]
    assert banner["load_failed"] == 1 and banner["errors"] == ["No fill."]


def test_doi_chieu_id_bi_che_theo_duoi():
    assert ad_log.match_rc_id("*****588", RC_IDS) == ["splash_inter_high_n_id"]
    assert ad_log.match_rc_id("*****717", RC_IDS) == ["id_101_spl_a_banner"]


def test_unit_khong_khop_key_nao_thi_tra_rong():
    """Do that: banner splash cua Piclux request unit *****825, khong key RC nao co."""
    assert ad_log.match_rc_id("*****825", RC_IDS) == []


def test_nhieu_key_cung_duoi_thi_tra_ca_hai_chu_khong_chon_bua():
    rc = dict(RC_IDS, trung_duoi="ca-app-pub-1111111111111111/9999999588")
    assert ad_log.match_rc_id("*****588", rc) == ["splash_inter_high_n_id", "trung_duoi"]


# --- thang bac verdict ------------------------------------------------------

def test_verdict_case_lay_dong_xau_nhat():
    from rcr import assert_check as a

    assert a.worst([a.PASS, a.PASS]) == a.PASS
    assert a.worst([a.PASS, a.NOT_VERIFIABLE]) == a.NOT_VERIFIABLE
    # config khong song -> chua test duoc, ken hon moi ket luan tu Expected
    assert a.worst([a.PASS, a.CONFIG_BLOCKED]) == a.CONFIG_BLOCKED
    # case khong co Expected nao -> "dat duoc config", ken hon PASS
    assert a.worst([a.CONFIG_OK, a.PASS]) == a.CONFIG_OK
