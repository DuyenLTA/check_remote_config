"""Doi RC tren server qua dieu kien testvsl: chi sua template trong bo nho, khong goi Firebase that."""

from __future__ import annotations

import copy

import pytest

from rcr import rc_firebase as f
from rcr.models import RcError


def _t():
    return {"conditions": [{"name": "testvsl", "expression": "app.version.contains(['2.7.0'])"},
                           {"name": "language Chinese", "expression": "device.country in ['CN']"}],
            "parameters": {"enable_resume": {"defaultValue": {"value": "true"},
                                             "conditionalValues": {"language Chinese": {"value": "false"}}}},
            "parameterGroups": {"ads": {"parameters": {"show_101": {"defaultValue": {"value": "true"}}}}}}


def test_gan_chi_them_gia_tri_cua_testvsl_khong_dung_default_hay_dieu_kien_khac():
    t = f.gan(_t(), {"enable_resume": "false", "show_101": "false", "key_moi": "1"})
    p = t["parameters"]["enable_resume"]
    assert p["defaultValue"] == {"value": "true"} and p["conditionalValues"]["language Chinese"] == {"value": "false"}
    assert p["conditionalValues"]["testvsl"] == {"value": "false"}
    assert t["parameterGroups"]["ads"]["parameters"]["show_101"]["conditionalValues"] == {"testvsl": {"value": "false"}}
    assert t["parameters"]["key_moi"] == {"defaultValue": {"useInAppDefault": True}, "description": f.TOOL_TAO,
                                          "conditionalValues": {"testvsl": {"value": "1"}}}


def test_khong_xoa_tham_so_mac_dinh_trong_app_cua_nguoi_khac():
    cu = _t()
    cu["parameters"]["cua_nguoi_khac"] = {"defaultValue": {"useInAppDefault": True}, "description": "PM tạo"}
    t = f.go(f.gan(copy.deepcopy(cu), {"cua_nguoi_khac": "1", "key_moi": "2"}), ["cua_nguoi_khac", "key_moi"])
    assert t["parameters"]["cua_nguoi_khac"] == cu["parameters"]["cua_nguoi_khac"] and "key_moi" not in t["parameters"]
    f.chi_doi_dieu_kien(cu, t)
    bi_xoa = copy.deepcopy(cu)
    del bi_xoa["parameters"]["cua_nguoi_khac"]
    with pytest.raises(RcError, match="ngoài điều kiện"):
        f.chi_doi_dieu_kien(cu, bi_xoa)


def test_go_tra_template_ve_nhu_cu():
    goc = _t()
    t = f.go(f.gan(copy.deepcopy(goc), {"enable_resume": "false", "show_101": "false", "key_moi": "1"}),
             ["enable_resume", "show_101", "key_moi"])
    assert t["parameters"] == goc["parameters"]
    assert t["parameterGroups"] == goc["parameterGroups"]


def test_dieu_kien_phai_co_va_dung_thu_nhat():
    assert "2.7.0" in f.kiem_dieu_kien(_t())
    t = _t()
    t["conditions"].reverse()
    with pytest.raises(RcError, match="thứ 2"):
        f.kiem_dieu_kien(t)
    with pytest.raises(RcError, match="chưa có điều kiện"):
        f.kiem_dieu_kien({"conditions": []})


def test_key_absent_cua_bo_tc_thanh_gia_tri_mac_dinh_trong_app():
    t = f.gan(_t(), {"enable_resume": "<absent>"})
    assert t["parameters"]["enable_resume"]["conditionalValues"]["testvsl"] == {"useInAppDefault": True}


def _bl():
    from rcr.models import RcBaseline
    return RcBaseline(package="p", serial="S", app_id="1:2:android:x", activate_name="", settings_name="",
                      activate_raw="", settings_raw="", configs={"enable_resume": "true"}, write_mode="firebase",
                      firebase={"project": "proj", "app_id": "1:2:android:x", "api_key": "k", "package": "p",
                                "version": "2.7.0"})


def test_ban_release_patch_restore_verify_di_qua_firebase(monkeypatch):
    import asyncio

    from rcr import rc_firebase_app, rc_patch, rc_verify
    goi = []
    monkeypatch.setattr(f, "dat", lambda project, gt: goi.append(("dat", project, gt)) or 1)
    monkeypatch.setattr(f, "tra_het", lambda project: goi.append(("tra", project)) or 2)
    monkeypatch.setattr(rc_firebase_app, "gia_tri_that", lambda info: {"enable_resume": "false"})
    r = asyncio.run(rc_patch.patch(None, _bl(), {"enable_resume": "false"}))
    assert r.applied == {"enable_resume": "false"} and goi == [("dat", "proj", {"enable_resume": "false"})]
    assert asyncio.run(rc_verify.verify(None, _bl(), {"enable_resume": "false"})).ok
    v = asyncio.run(rc_verify.verify(None, _bl(), {"enable_resume": "true", "key_x": "<absent>"}))
    assert [m.key for m in v.mismatches] == ["enable_resume"]
    assert asyncio.run(rc_patch.restore(None, _bl())).restored and goi[-1] == ("tra", "proj")


def test_chot_chan_chi_cho_sua_gia_tri_cua_testvsl():
    cu = _t()
    f.chi_doi_dieu_kien(cu, f.gan(copy.deepcopy(cu), {"enable_resume": "false", "key_moi": "1", "show_101": "x"}))
    for hong in ("default", "dieu_kien_khac", "thu_tu"):
        moi = copy.deepcopy(cu)
        if hong == "default":
            moi["parameters"]["enable_resume"]["defaultValue"] = {"value": "false"}
        elif hong == "dieu_kien_khac":
            moi["parameters"]["enable_resume"]["conditionalValues"]["language Chinese"] = {"value": "true"}
        else:
            moi["conditions"].reverse()
        with pytest.raises(RcError, match="ngoài điều kiện"):
            f.chi_doi_dieu_kien(cu, moi)
