"""Tab rating: config ep cua app trong rating_gen.yaml (`ep_cau_hinh`) duoc tool tu dat moi case."""
from rcr import rating_cong_thuc


def test_app_gen_ngam_ep_generating_wait():
    ep = rating_cong_thuc.ep_cau_hinh("com.aiphotogenerator.aivideomaker.photoslideshow")
    assert ep == {"generating_wait_image_seconds": "60", "generating_wait_video_seconds": "300"}


def test_app_chua_khai_khong_ep_gi():
    assert rating_cong_thuc.ep_cau_hinh("com.khong.co.app") == {}


def test_ep_cau_hinh_khong_lam_hong_cong_thuc():
    assert rating_cong_thuc.cong_thuc("com.aiphotogenerator.aivideomaker.photoslideshow", "anh")
