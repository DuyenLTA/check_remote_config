"""Cong thuc dung chung theo khuon: app chua khai van chay duoc neu chu Home khop khuon (user chot 16/11/2026)."""

from rcr import act_checkin, cong_thuc_khuon, rating_cong_thuc
from rcr.ui_dump import Bounds, DeviceNode


def _n(text):
    return DeviceNode("0", "", "android.widget.TextView", text, "", Bounds(0, 0, 10, 10), True, True, True, "x", None, 0)


def test_app_moi_cung_khuon_dung_cong_thuc_chung():
    home = [_n("Magic With AI"), _n("Trending")]
    assert rating_cong_thuc.cong_thuc("com.app.moi", "anh") is None
    assert rating_cong_thuc.cong_thuc("com.app.moi", "anh", home) == \
        rating_cong_thuc.cong_thuc("com.aiphotogenerator.aivideomaker.photoslideshow", "anh")
    assert act_checkin.cong_thuc("com.app.moi", home)["vao_unlock"]
    assert rating_cong_thuc.cong_thuc("com.app.moi", "anh", [_n("Khac")]) is None


def test_muc_rieng_ghim_khuon_de_phan_rieng_len():
    data = {"khuon": {"k": {"nhan_dien": "^X$", "a": 1, "b": 2}}, "p": {"khuon": "k", "b": 3}, "q": {"a": 9}}
    assert cong_thuc_khuon.chon(data, "p") == ("khuôn k", {"nhan_dien": "^X$", "a": 1, "b": 3})
    assert cong_thuc_khuon.chon(data, "q") == ("rieng", {"a": 9})
    assert cong_thuc_khuon.chon(data, "z", [_n("X")])[0] == "khuôn k"
