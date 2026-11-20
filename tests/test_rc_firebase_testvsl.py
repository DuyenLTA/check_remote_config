"""Tao / xoa condition testvsl: Firebase gia trong bo nho (template theo version + PUT), khong goi mang that."""

from __future__ import annotations

import copy

import pytest

from rcr import bot_testvsl, rc_firebase as rc, rc_firebase_testvsl as tv
from rcr.models import RcError

TOI, KHAC = "qa@vd.vn", "nguoi-khac@vd.vn"
APP = "1:1:android:ab"


class Firebase:
    """versions[n] = (template, email nguoi publish); moi PUT them mot version."""

    def __init__(self, dau: dict, ai: str):
        self.versions = {1: (copy.deepcopy(dau), ai)}
        self.put = []

    @property
    def moi_nhat(self) -> int:
        return max(self.versions)

    def get(self, url: str, tok: str) -> dict:
        if ":listVersions" in url:
            return {"versions": [{"versionNumber": str(n), "updateUser": {"email": e}}
                                 for n, (_, e) in self.versions.items()]}
        n = int(url.split("versionNumber=")[1])
        return copy.deepcopy(self.versions[n][0])

    def them(self, t: dict, ai: str) -> None:
        self.versions[self.moi_nhat + 1] = (copy.deepcopy(t), ai)


@pytest.fixture
def fb(monkeypatch):
    goc = {"conditions": [{"name": "language Chinese", "expression": "device.country in ['CN']"}],
           "parameters": {"enable_resume": {"defaultValue": {"value": "true"},
                                            "conditionalValues": {"language Chinese": {"value": "false"}}}}}
    f = Firebase(goc, KHAC)
    monkeypatch.setattr(tv, "email_dang_nhap", lambda: TOI)
    monkeypatch.setattr(tv, "_get", f.get)
    monkeypatch.setattr(rc, "token", lambda: "tok")
    monkeypatch.setattr(rc, "doc", lambda p, tok: (copy.deepcopy(f.versions[f.moi_nhat][0]), str(f.moi_nhat)))

    def put(project, tok, method, t, etag):
        assert method == "PUT" and etag == str(f.moi_nhat)
        f.put.append(copy.deepcopy(t))
        f.them(t, TOI)
        return {"version": {"versionNumber": str(f.moi_nhat)}}, str(f.moi_nhat)
    monkeypatch.setattr(rc, "_goi", put)
    return f


def _cac_dk(f: Firebase) -> list[str]:
    return [c["name"] for c in f.versions[f.moi_nhat][0].get("conditions") or []]


def test_tao_dung_version_dung_thu_1_khong_dong_dieu_kien_khac(fb):
    assert "Đã tạo" in tv.tao("p", APP, "1.1.0 (3)")
    t = fb.versions[fb.moi_nhat][0]
    assert _cac_dk(fb) == ["testvsl", "language Chinese"]
    assert t["conditions"][0]["expression"] == f"app.id == '{APP}' && app.version.contains(['1.1.0'])"
    assert t["parameters"] == fb.versions[1][0]["parameters"]
    assert "không cần sửa" in tv.tao("p", APP, "1.1.0")            # goi lai: khong publish them
    assert len(fb.put) == 1


def test_xoa_condition_minh_tao_kem_gia_tri_gan_theo_no(fb):
    tv.tao("p", APP, "1.1.0 (3)")
    t = copy.deepcopy(fb.versions[fb.moi_nhat][0])
    fb.them(rc.gan(t, {"enable_resume": "false", "key_tam": "1"}), TOI)   # luot test gan gia tri
    assert tv.trang_thai("p")["cua_toi"] is True
    assert "Đã xoá" in tv.xoa("p")
    t = fb.versions[fb.moi_nhat][0]
    assert _cac_dk(fb) == ["language Chinese"]
    assert t["parameters"] == fb.versions[1][0]["parameters"]            # gia tri testvsl + key tool tao da go


def test_khong_xoa_khong_sua_condition_nguoi_khac_tao(fb):
    t = copy.deepcopy(fb.versions[1][0])
    t["conditions"].insert(0, {"name": "testvsl", "expression": "app.version.contains(['2.0.0'])"})
    fb.them(t, KHAC)                                  # nguoi khac tao
    fb.them(rc.gan(copy.deepcopy(t), {"enable_resume": "false"}), TOI)   # bot gan gia tri sau do: van cua nguoi khac
    tt = tv.trang_thai("p")
    assert tt["nguoi_tao"] == KHAC and tt["cua_toi"] is False
    with pytest.raises(RcError, match="người khác tạo"):
        tv.xoa("p")
    with pytest.raises(RcError, match="người khác tạo"):
        tv.tao("p", APP, "2.1.0")
    assert fb.put == []


def test_condition_co_tu_truoc_lich_su_thi_khong_xac_dinh_khong_xoa(fb):
    t = copy.deepcopy(fb.versions[1][0])
    t["conditions"].insert(0, {"name": "testvsl", "expression": "x"})
    fb.versions = {1: (t, TOI)}                       # version cu nhat con giu da co testvsl
    assert tv.nguoi_tao("p") == ""
    with pytest.raises(RcError, match="không xác định"):
        tv.xoa("p")


def test_doi_version_condition_cua_minh_nhung_khong_khi_dang_gan_key(fb):
    tv.tao("p", APP, "1.0.1")
    assert "Đã sửa" in tv.tao("p", APP, "1.1.0 (3)")
    assert "['1.1.0']" in fb.versions[fb.moi_nhat][0]["conditions"][0]["expression"]
    fb.them(rc.gan(copy.deepcopy(fb.versions[fb.moi_nhat][0]), {"enable_resume": "false"}), TOI)
    with pytest.raises(RcError, match="đang gán 1 key"):
        tv.tao("p", APP, "1.2.0")


def test_chot_chan_khong_publish_khi_sua_ngoai_testvsl(fb, monkeypatch):
    def hong(t):
        t["parameters"]["enable_resume"]["defaultValue"] = {"value": "false"}
        return t
    with pytest.raises(RcError, match="ngoài điều kiện"):
        tv._publish("p", hong, "testvsl")
    assert fb.put == []


@pytest.mark.parametrize("chu, pass_", [
    ("test pass v1.4.0(14) rls", True), ("AIP508 1.1.0 (3) pass nhé", True), ("Test Passed", True),
    ("chưa pass case IAA", False), ("not pass", False), ("fail 2 case, pass còn lại", False),
    ("đổi password", False), ("bypass splash", False), ("build mới v1.2.0 (3)", False),
])
def test_nhan_dien_tin_test_pass(chu, pass_):
    assert bot_testvsl.la_tin_pass(chu) is pass_


def test_ten_version_va_doc_version_trong_dieu_kien():
    assert tv.ten_version("1.1.0 (3)") == "1.1.0" and tv.ten_version("v2.0.1") == "2.0.1"
    assert tv.versions_trong("app.version.contains(['1.0.1', '1.1.0'])") == ["1.0.1", "1.1.0"]



def test_luot_check_tu_tao_testvsl_theo_version_tin_build(monkeypatch):
    import asyncio

    from rcr import bot_kiem_testvsl as k, rc_firebase_app as fa
    goi = []

    async def info(client, serial, package):
        return {"project": "p", "app_id": APP}
    monkeypatch.setattr(rc, "da_dang_nhap", lambda: True)
    monkeypatch.setattr(fa, "thong_tin_tren_may", info)
    monkeypatch.setattr(tv, "tao", lambda p, a, v: goi.append((p, a, v)) or "Đã tạo `testvsl`")
    assert asyncio.run(k.THAT_TAO("S1", "pkg", "1.1.0 (3)")) == "🧪 Đã tạo `testvsl`"
    assert goi == [("p", APP, ["1.1.0 (3)"])]
    monkeypatch.setattr(tv, "tao", lambda p, a, v: "`testvsl` đã đúng version 1.1.0 và đang đứng thứ 1 — không cần sửa.")
    assert asyncio.run(k.THAT_TAO("S1", "pkg", "1.1.0 (3)")) == ""

    def nguoi_khac(p, a, v):
        raise RcError("`testvsl` của project p do người khác tạo — bot không sửa")
    monkeypatch.setattr(tv, "tao", nguoi_khac)
    assert "người khác tạo" in asyncio.run(k.THAT_TAO("S1", "pkg", "1.1.0 (3)"))


@pytest.fixture
def plan(monkeypatch):
    from rcr import plan_tuan
    ghi = {}
    monkeypatch.setenv(plan_tuan.ENV, "https://sheet")
    monkeypatch.setattr(plan_tuan, "tai", lambda link, out: "plan.xlsx")
    monkeypatch.setattr(plan_tuan, "yeu_cau", lambda path, ma, ngay: ghi.get(ma))
    return ghi


def test_tin_build_lech_plan_thi_condition_chua_ca_hai_version(plan, fb):
    plan["AIP508"] = {"version": ["1.1.0"]}
    assert bot_testvsl.versions_can_tao("AIP508", "1.0.1 (3)") == ["1.0.1", "1.1.0"]
    assert bot_testvsl.versions_can_tao("AIP508", "1.1.0 (3)") == ["1.1.0"]          # khop plan: chi version build
    assert bot_testvsl.versions_can_tao("AIP999", "2.0.0 (1)") == ["2.0.0"]          # plan khong ghi: chi build
    tv.tao("p", APP, bot_testvsl.versions_can_tao("AIP508", "1.0.1 (3)"))
    assert fb.versions[fb.moi_nhat][0]["conditions"][0]["expression"].endswith("contains(['1.0.1', '1.1.0'])")
    assert "không cần sửa" in tv.tao("p", APP, ["1.0.1 (3)", "1.1.0"])


def test_plan_hong_van_tao_theo_version_build(monkeypatch):
    from rcr import plan_tuan
    monkeypatch.setenv(plan_tuan.ENV, "https://sheet")

    def hong(link, out):
        raise RcError("không tải được plan tuần")
    monkeypatch.setattr(plan_tuan, "tai", hong)
    assert bot_testvsl.versions_can_tao("AIP508", "1.0.1 (3)") == ["1.0.1"]
