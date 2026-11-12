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


def _http(code):
    import io
    import urllib.error
    return urllib.error.HTTPError("u", code, "x", {}, io.BytesIO(b"{}"))


def test_loi_tam_cua_firebase_thi_thu_lai(monkeypatch):
    """09/11/2026: RC tra 503 bon lan trong mot buoi, moi lan dung ca luot."""
    monkeypatch.setattr(f.time, "sleep", lambda s: None)
    lan = []

    def goi():
        lan.append(1)
        if len(lan) < 3:
            raise _http(503)
        return "ok"
    assert f._mang(goi) == "ok" and len(lan) == 3


def test_loi_khong_tam_thi_nem_ngay(monkeypatch):
    import urllib.error
    monkeypatch.setattr(f.time, "sleep", lambda s: None)
    lan = []

    def goi():
        lan.append(1)
        raise _http(412)
    with pytest.raises(urllib.error.HTTPError):
        f._mang(goi)
    assert len(lan) == 1


def test_503_mai_thi_het_luot_thu_moi_nem(monkeypatch):
    import urllib.error
    monkeypatch.setattr(f.time, "sleep", lambda s: None)
    lan = []

    def goi():
        lan.append(1)
        raise _http(503)
    with pytest.raises(urllib.error.HTTPError):
        f._mang(goi)
    assert len(lan) == f.THU_MANG


def _goi_gia(monkeypatch, mau, put_tra=None):
    """Thay `_goi` bang server gia: GET tra `mau`, PUT tra template vua gui + ETag moi (hoac loi `put_tra`)."""
    goi = []
    server = {"t": copy.deepcopy(mau), "etag": "e1"}

    def _goi(project, tok, method="GET", template=None, etag=""):
        goi.append(method)
        if method == "GET":
            return copy.deepcopy(server["t"]), server["etag"]
        loi = put_tra(len(goi)) if put_tra else None
        if loi:
            raise loi
        if etag != server["etag"]:
            raise _http(412)
        server["t"], server["etag"] = copy.deepcopy(template), f"e{len(goi)}"
        return copy.deepcopy(template) | {"version": {"versionNumber": str(len(goi))}}, server["etag"]
    monkeypatch.setattr(f, "_goi", _goi)
    monkeypatch.setattr(f, "token", lambda: "tok")
    monkeypatch.setattr(f.time, "sleep", lambda s: None)
    return goi, server


def test_patch_roi_restore_dung_template_vua_publish_khong_doc_lai(monkeypatch):
    goi, server = _goi_gia(monkeypatch, _t())
    f.dat("proj", {"enable_resume": "false"})
    assert goi == ["GET", "PUT"]
    f.tra_het("proj")
    assert goi == ["GET", "PUT", "PUT"]                  # restore: PUT thang voi ETag cua lan publish truoc
    assert "testvsl" not in server["t"]["parameters"]["enable_resume"]["conditionalValues"]
    f.dat("proj", {"show_101": "false"})                 # case sau: cung khong GET
    assert goi == ["GET", "PUT", "PUT", "PUT"]


def test_template_nho_da_cu_thi_412_roi_doc_lai_khong_ghi_de_nguoi_khac(monkeypatch):
    goi, server = _goi_gia(monkeypatch, _t())
    f.dat("proj", {"enable_resume": "false"})
    # may kia vua publish: them gia tri testvsl cua no
    server["t"]["parameters"]["enable_resume"]["conditionalValues"]["language Chinese"] = {"value": "x"}
    server["etag"] = "khac"
    f.tra_het("proj")
    assert goi == ["GET", "PUT", "PUT", "GET", "PUT"]
    assert server["t"]["parameters"]["enable_resume"]["conditionalValues"] == {"language Chinese": {"value": "x"}}


def test_tra_het_khi_nho_khong_con_key_van_doc_that(monkeypatch):
    """Nho 'khong con gi' khong du: may khac / luot chet co the da gan testvsl -> GET that roi moi bo qua."""
    goi, server = _goi_gia(monkeypatch, _t())
    f.dat("proj", {"enable_resume": "false"})
    f.tra_het("proj")
    goi.clear()
    assert f.tra_het("proj") == 0 and goi == ["GET"]
    server["t"]["parameters"]["enable_resume"]["conditionalValues"]["testvsl"] = {"value": "1"}
    server["etag"] = "e9"
    f.tra_het("proj")
    assert goi == ["GET", "GET", "PUT"]
    assert "testvsl" not in server["t"]["parameters"]["enable_resume"]["conditionalValues"]


def test_429_luc_publish_thi_cho_roi_thu_lai(monkeypatch):
    """12/11/2026: Firebase tra 429 (vuot han muc) - truoc day LOI_TAM bi khai lai thieu 429, ca luot dung."""
    lan = []
    goi, server = _goi_gia(monkeypatch, _t(), put_tra=lambda n: (lan.append(n) or _http(429)) if len(lan) < 2 else None)
    f.dat("proj", {"enable_resume": "false"})
    assert len(lan) == 2 and goi == ["GET", "PUT", "GET", "PUT", "GET", "PUT"]
    assert server["t"]["parameters"]["enable_resume"]["conditionalValues"]["testvsl"] == {"value": "false"}


def test_429_trong_mang_thi_thu_lai_theo_retry_after(monkeypatch):
    import io
    import urllib.error
    cho = []
    monkeypatch.setattr(f.time, "sleep", cho.append)
    lan = []

    def goi():
        lan.append(1)
        if len(lan) == 1:
            raise urllib.error.HTTPError("u", 429, "x", {"Retry-After": "7"}, io.BytesIO(b""))
        if len(lan) == 2:
            raise _http(429)
        return "ok"
    assert f._mang(goi) == "ok" and cho == [7.0, f.CHO_LOI_TAM * 2]


def test_token_nho_khong_doi_lai_moi_lan(monkeypatch):
    lay = []
    monkeypatch.setattr(f, "_token_moi", lambda: lay.append(1) or "tok")
    assert f.token() == f.token() == "tok" and lay == [1]


def test_template_nho_qua_lau_thi_doc_lai_truoc_khi_put(monkeypatch):
    """PUT voi ETag cua lan PUT ~60s truoc hay treo 10s roi 5xx (vivo 12/11/2026) -> qua MAU_SONG thi GET lai."""
    from rcr import rc_firebase_http as h
    goi, server = _goi_gia(monkeypatch, _t())
    gio = [1000.0]
    monkeypatch.setattr(h.time, "monotonic", lambda: gio[0])
    f.dat("proj", {"enable_resume": "false"})
    gio[0] += h.MAU_SONG + 1
    f.tra_het("proj")
    assert goi == ["GET", "PUT", "GET", "PUT"]
    f.dat("proj", {"show_101": "false"})          # ngay sau restore: dung template vua publish
    assert goi == ["GET", "PUT", "GET", "PUT", "PUT"]
