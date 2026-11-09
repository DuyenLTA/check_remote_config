"""Doi chieu build voi plan tuan: workbook dung tay, khong tai sheet that."""

from __future__ import annotations

import datetime as dt

import openpyxl
import pytest

from rcr import plan_tuan as pt
from rcr import preflight

PKG = "com.aivideogenerator.aiphotoeditor.beautyeditor.imagetoimage"
NGAY = dt.date(2026, 10, 30)


def _plan(tmp_path):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "1910-23102026"
    ws.append([14, "VSL - Inhouse", "Android", "AIP882", "- Apply SDK Next Gen"])
    ws = wb.create_sheet("2610-30102026")
    ws.append([14, "VSL - Inhouse", "Android", "AIP882", "- SDK 3.6.1", 10, "Duyên", "Testing"])
    ws.append([13, "VSL - Inhouse", "Android", "AIP882", "test v4.3.0 doing"])
    ws.append([1, "VSL - Inhouse", "Android", "AIP918", "SDK 3.7.1:\n- SDK Next Gen thêm SDK tiktok\n- Base 3.7.0"])
    ws.append([2, "VSL - Inhouse", "Android", "AIP940", "- Apply SDK Next Gen"])
    ws.append([3, "VSL - Inhouse", "Android", "AIP927", "- Dùng photo picker"])
    f = tmp_path / "plan.xlsx"
    wb.save(f)
    return f


def _kt(tmp_path):
    wb = openpyxl.Workbook()
    wb.active.title = "AIP882"
    wb.active.append(["Package name", PKG])
    f = tmp_path / "kt.xlsx"
    wb.save(f)
    return f


@pytest.mark.parametrize("ten, tuan", [
    ("2610-30102026", (dt.date(2026, 10, 26), dt.date(2026, 10, 30))),
    ("1910 - 23102026", (dt.date(2026, 10, 19), dt.date(2026, 10, 23))),
    ("2912-02012027", (dt.date(2026, 12, 29), dt.date(2027, 1, 2))),
    ("draf", None), ("Root", None),
])
def test_doc_tuan_tu_ten_tab(ten, tuan):
    assert pt.tuan_cua_tab(ten) == tuan


def test_lay_yeu_cau_sdk_tab_tuan_nay_bo_dong_qa(tmp_path):
    yc = pt.yeu_cau(_plan(tmp_path), "AIP882", NGAY)
    assert yc == {"tab": "2610-30102026", "sdk": ["3.6.1"], "next_gen": False, "dong": ["- SDK 3.6.1"],
                  "version": ["4.3.0"], "loai": "", "pham_vi": ["- SDK 3.6.1"]}
    assert pt.yeu_cau(_plan(tmp_path), "AIP882", dt.date(2026, 11, 5)) is None
    assert pt.ma_cua_package(_kt(tmp_path), PKG) == "AIP882"


def test_aip882_app_in_3_7_0_khac_plan_3_6_1(tmp_path):
    yc = pt.yeu_cau(_plan(tmp_path), "AIP882", NGAY)
    assert pt.lech(yc, "3.6.1", "3.7.0") == ["app in log SDK 3.7.0, plan ghi 3.6.1"]
    assert pt.lech(yc, "3.6.1", "3.6.1") == [] and pt.lech(yc, "", "3.6.1-alpha02") == []
    assert len(pt.lech(yc, "3.7.0", "")) == 1


def test_plan_chi_ghi_next_gen_thi_doi_ban_next_gen(tmp_path):
    yc = pt.yeu_cau(_plan(tmp_path), "AIP940", NGAY)
    assert yc["next_gen"] and not yc["sdk"]
    assert pt.lech(yc, "", "3.7.0") == [] and pt.lech(yc, "", "3.6.1") == ["app in log SDK 3.6.1, plan ghi Next-Gen"]
    yc = pt.yeu_cau(_plan(tmp_path), "AIP918", NGAY)
    assert yc["sdk"] == ["3.7.1"] and pt.lech(yc, "3.7.1-alpha01", "3.7.1") == []


def test_preflight_khac_plan_la_loi_khop_la_ok(tmp_path, monkeypatch):
    plan, kt = _plan(tmp_path), _kt(tmp_path)
    monkeypatch.setattr(preflight, "env", lambda ten: "link-plan" if ten == pt.ENV else "")
    monkeypatch.setattr(preflight.tc_source, "tai_ve", lambda link, out: kt)
    monkeypatch.setattr(pt, "tai", lambda link, out: plan)
    m = preflight.muc_plan(PKG, "3.6.1", "3.7.0", tmp_path, NGAY)
    assert m["trang_thai"] == "loi" and "KHÁC plan" in m["chi_tiet"] and "qa-auto" in m["viec_can_lam"]
    assert preflight.muc_plan(PKG, "3.6.1", "3.6.1", tmp_path, NGAY)["trang_thai"] == "ok"
    assert preflight.muc_plan(PKG, "3.6.1", "3.6.1", tmp_path, dt.date(2026, 11, 5))["trang_thai"] == "canh_bao"


def test_chua_cau_hinh_plan_chi_canh_bao(monkeypatch, tmp_path):
    monkeypatch.setattr(preflight, "env", lambda ten: "")
    assert preflight.muc_plan(PKG, "3.6.1", "3.7.0", tmp_path)["trang_thai"] == "canh_bao"


def _plan_0211(tmp_path):
    """Dong that cua plan tuan 02/11-06/11/2026: o Detail ghi scope, dong cong viec ghi version + loai ban."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "0211-06112026"
    ws.append([21, "VSL - Inhouse", "Android", "AIP936", "- SDK 3.6.1", 3, "Duyên", "Released"])
    ws.append([5, "VSL - Inhouse", "Android", "AIP893",
               "- SDK 3.5.4\n- Apply photo picker\n- Apply SDK chống spam service \n- Thay ad ID mới\n", 4])
    ws.append([21, "VSL - Inhouse", "Android", "AIP936", "test v1.9.0 rls "])
    f = tmp_path / "plan0211.xlsx"
    wb.save(f)
    return f


def test_plan_ghi_version_va_loai_ban(tmp_path):
    yc = pt.yeu_cau(_plan_0211(tmp_path), "AIP936", dt.date(2026, 11, 3))
    assert yc["version"] == ["1.9.0"] and yc["loai"] == "release" and yc["sdk"] == ["3.6.1"]
    yc893 = pt.yeu_cau(_plan_0211(tmp_path), "AIP893", dt.date(2026, 11, 3))
    assert yc893["version"] == []                       # "SDK 3.5.4" la ban SDK, khong phai version app
    assert "Apply photo picker" in yc893["pham_vi"][0]


def test_dev_build_nham_version_hoac_loai_ban_la_lech(tmp_path):
    yc = pt.yeu_cau(_plan_0211(tmp_path), "AIP936", dt.date(2026, 11, 3))
    assert pt.lech_ban(yc, "1.9.0 (11)", "release") == []
    assert pt.lech_ban(yc, "1.8.0", "release") == ["máy đang cài version 1.8.0, plan ghi v1.9.0"]
    assert pt.lech_ban(yc, "1.9.0", "debug") == ["máy đang cài bản debug, plan ghi bản release"]


def test_preflight_bao_loi_khi_sai_version_va_in_scope(tmp_path, monkeypatch):
    kt = tmp_path / "kt936.xlsx"
    wb = openpyxl.Workbook()
    wb.active.title = "AIP936"
    wb.active.append(["Package name", "com.aihomedesign.aihomedecor.designidea.aiinterior"])
    wb.save(kt)
    plan = _plan_0211(tmp_path)
    monkeypatch.setattr(preflight, "env", lambda ten: "link-plan" if ten == pt.ENV else "")
    monkeypatch.setattr(preflight.tc_source, "tai_ve", lambda link, out: kt)
    monkeypatch.setattr(pt, "tai", lambda link, out: plan)
    pkg, ngay = "com.aihomedesign.aihomedecor.designidea.aiinterior", dt.date(2026, 11, 3)
    ok = preflight.muc_plan(pkg, "3.6.1", "3.6.1", tmp_path, ngay, ver_app="1.9.0", loai_app="release")
    assert ok["trang_thai"] == "ok" and "v1.9.0" in ok["chi_tiet"] and "scope: - SDK 3.6.1" in ok["chi_tiet"]
    sai = preflight.muc_plan(pkg, "3.6.1", "3.6.1", tmp_path, ngay, ver_app="1.8.0", loai_app="release")
    assert sai["trang_thai"] == "loi" and "version 1.8.0" in sai["chi_tiet"]


def _plan_cot(tmp_path):
    """Dinh dang plan moi user gui 03/11/2026: co cot "App version" rieng, "Detail" la scope."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "0911-13112026"
    ws.append(["Plan "])
    ws.append(["STT", "Loại dự án", "OS", "Tên dự án", "App version ", "Detail ", "Ưu tiên", "PIC", "Trạng thái"])
    ws.append([1, "VSL - IOS", "iOS", "[IIP036] Lensie", None,
               "2.3.0 : - Tích hợp hệ thống credit cho app\n- Studio chat v2 (ghép BE)", 1, "Thảo", "Chưa có build"])
    ws.append([2, "VSL - Inhouse", "Android", "AIP938", "2.2.0 (14) rls", "- SDK 3.6.1\n- Thay ad ID mới", 2])
    ws.append([3, "VSL - Inhouse", "Android", "AIP885", None, None])
    f = tmp_path / "plan_cot.xlsx"
    wb.save(f)
    return f


def test_bang_co_cot_app_version_doc_dung_cot(tmp_path):
    yc = pt.yeu_cau(_plan_cot(tmp_path), "AIP938", dt.date(2026, 11, 10))
    assert yc["version"] == ["2.2.0"] and yc["loai"] == "release" and yc["sdk"] == ["3.6.1"]
    assert yc["pham_vi"] == ["- SDK 3.6.1\n- Thay ad ID mới"]
    assert pt.lech_ban(yc, "2.1.0 (13)", "release") == ["máy đang cài version 2.1.0, plan ghi v2.2.0"]
    trong = pt.yeu_cau(_plan_cot(tmp_path), "AIP885", dt.date(2026, 11, 10))
    assert trong["version"] == [] and trong["sdk"] == [] and trong["pham_vi"] == []
    # so "2.3.0" dau o Detail cua Lensie (iOS) khong bi doc thanh version cua app khac
    assert pt.yeu_cau(_plan_cot(tmp_path), "IIP036", dt.date(2026, 11, 10))["version"] == []


def test_bo_qua_plan_chi_con_canh_bao(tmp_path, monkeypatch):
    # AIP944 1.3.0 09/11/2026: plan ghi v1.4.0, QA bam "Chạy bỏ qua plan" (dev chi nang / ha version).
    plan, kt = _plan(tmp_path), _kt(tmp_path)
    monkeypatch.setattr(preflight, "env", lambda ten: "link-plan" if ten == pt.ENV else "")
    monkeypatch.setattr(preflight.tc_source, "tai_ve", lambda link, out: kt)
    monkeypatch.setattr(pt, "tai", lambda link, out: plan)
    m = preflight.muc_plan(PKG, "3.6.1", "3.7.0", tmp_path, NGAY, bo_qua=True)
    assert m["trang_thai"] == "canh_bao" and "KHÁC plan" in m["chi_tiet"] and "--bo-qua-plan" in m["chi_tiet"]
