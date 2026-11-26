"""Key RC rieng cua app (`rc_them` trong gen_ngam_cong_thuc.yaml) duoc dat cung config moi nhom gen ngam."""
from rcr import gen_ngam_may
from rcr.cli_gen_ngam import config_nhom

REC = [{"key": "GEN-R01-01", "overrides": {"limit_gen_image_free_per_day": "3"}},
       {"key": "GEN-R02-01", "overrides": {"limit_gen_image_free_per_day": "3"}}]


def test_rc_them_vao_config_nhom_nhung_key_ep_cua_nhom_thang():
    gt = config_nhom(REC, "r01", {"paywall_placement": "home", "generating_wait_image_seconds": 99})
    assert gt["paywall_placement"] == "home"
    assert gt["generating_wait_image_seconds"] == "45"      # key ep rieng cua nhom r01 de len rc_them
    assert gt["limit_gen_image_free_per_day"] == "3"


def test_khong_co_rc_them_giu_nguyen():
    assert config_nhom(REC, "chung") == {"limit_gen_image_free_per_day": "3"}


def test_hypix_mo_paywall_qua_rc():
    ct = gen_ngam_may.cong_thuc("com.ai.videogenerator.photocreator.aiart")
    assert ct["rc_them"] == {"paywall_placement": "home"}
    assert not ct.get("_khuon_chung")
    assert ct["toast_xong"]                                    # chu man van lay tu khuon chung
