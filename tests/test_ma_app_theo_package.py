import json

from rcr import ma_app_theo_package as m


def _ghi(d, ten, obj):
    (d / ten).write_text(json.dumps(obj), encoding="utf-8")


def test_lay_ma_moi_nhat_tu_ca_may_chinh_va_may_phu(tmp_path):
    _ghi(tmp_path, "bot-hang-doi.json", {"jobs": [], "tin": {"100": {"ma": "AIP900", "package": "a.b"}}})
    _ghi(tmp_path, "bot-hang-doi-may-phu.json", {"jobs": [{"ma": "aip944", "package": "a.b", "msg_id": 200}], "tin": {}})
    assert m.ma_app("a.b", tmp_path) == "AIP944"
    assert m.gan_ma("App X 1.4.0", "a.b", tmp_path) == "AIP944 · App X 1.4.0"


def test_nhan_da_co_ma_hoac_khong_tra_duoc_thi_giu_nguyen(tmp_path):
    _ghi(tmp_path, "bot-hang-doi.json", {"jobs": [{"ma": "AIP944", "package": "a.b", "msg_id": 1}], "tin": {}})
    assert m.gan_ma("AIP944 App", "a.b", tmp_path) == "AIP944 App"
    assert m.gan_ma("App", "khong.co", tmp_path) == "App"
    assert m.ma_app("a.b", tmp_path / "khong-ton-tai") == ""
