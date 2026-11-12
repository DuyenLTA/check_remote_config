"""Tin tao bang /check khong co link_tin -> tim nguoi gui build qua tin cung ma + version (AIP918-147 12/11/2026)."""

from types import SimpleNamespace

from rcr import bot_kenh_project as kp

L1 = "https://discord.com/channels/1/2/100"
L2 = "https://discord.com/channels/1/2/200"


def _bot(tin):
    return SimpleNamespace(q=SimpleNamespace(tin=tin))


def test_lay_link_tin_moi_nhat_cung_ma_va_version():
    tin = {"1": {"ma": "AIP918", "version": "2.5.0 (23)", "link_tin": L1, "msg_id": 1},
           "5": {"ma": "AIP918", "version": "2.5.0 (23)", "link_tin": L2, "msg_id": 5},
           "9": {"ma": "AIP918", "version": "2.4.0 (22)", "link_tin": "https://x/3/4/999", "msg_id": 9},
           "7": {"ma": "AIP918", "version": "2.5.0 (23)", "link_tin": "", "msg_id": 7}}
    assert kp.link_tin_cung_build(_bot(tin), {"ma": "AIP918", "version": "2.5.0 (23)", "link_tin": ""}) == L2


def test_khong_co_tin_nao_co_link_thi_rong():
    tin = {"7": {"ma": "AIP893", "version": "2.6.0 (16)", "link_tin": "", "msg_id": 7}}
    assert kp.link_tin_cung_build(_bot(tin), {"ma": "AIP893", "version": "2.6.0 (16)"}) == ""
    assert kp.link_tin_cung_build(SimpleNamespace(), {"ma": "AIP893"}) == ""
