"""Ten truong JSON TC dat vs gia tri server cua cung key."""

from __future__ import annotations

from rcr import rc_json_lech

# Do that 24/10/2026: Piclux 2.4.0 server vs TC SDK 3.4.0
SERVER = {"splash_ui_config": '{"type":"image","media_url":"https://x/a.png","video_loop":true,'
                              '"video_mute":true,"title":"Piclux","title_color":"#4957FF"}',
          "splash_banner_change": "true"}
TC = {"splash_ui_config": '{"type":"image","image_url":"https://x/b.webp","title":"Fravix",'
                          '"title_color":"#4957FF"}',
      "splash_banner_change": "false"}


def test_truong_tc_khong_co_tren_server_thi_canh_bao():
    ra = rc_json_lech.lech(TC, SERVER)
    assert len(ra) == 1
    assert "image_url" in ra[0] and "media_url" in ra[0] and "splash_ui_config" in ra[0]


def test_tc_chi_dat_mot_phan_truong_cua_server_thi_khong_canh_bao():
    tc = {"splash_ui_config": '{"type":"image","media_url":"https://x/b.png"}'}
    assert rc_json_lech.lech(tc, SERVER) == []


def test_gia_tri_khong_phai_json_object_thi_bo_qua():
    assert rc_json_lech.lech({"splash_banner_change": "false", "a": "[1,2]"},
                             {"splash_banner_change": "true", "a": "[3]"}) == []
    assert rc_json_lech.lech({"k": "{hong"}, {"k": '{"a":1}'}) == []
    assert rc_json_lech.lech({"k": '{"a":1}'}, {}) == []
