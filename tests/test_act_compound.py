"""Test cau Action dang ghep (bo TC 3.5.0) va cach lai may cho chung.

Diem phai gac - moi cau duoi day truoc kia bi lam SAI IM LANG, khong dung:
  - "vuot nhanh lien tuc 3-4 lan" phai vuot 4 lan, khong phai 1
  - "vuot phai ve OB2, roi vuot trai" phai vuot PHAI truoc
  - "cho qua 10s" phai cho QUA 10s, khong phai 3s mac dinh
  - "bam gio" la do thoi gian, khong phai di tim nut ten "gio"
  - xoay man xong phai tra che do xoay cua may ve nhu cu
  - "Mo lai app" sau khi nhan Home phai dua app len that
"""

from __future__ import annotations

import asyncio

import pytest
from conftest import PKG
from test_case_drive import fake

from rcr import act_compound, act_exec, act_resolver, case_drive, device_app


def kind(step):
    return act_resolver.resolve(step, [])


@pytest.fixture
def khong_cho(monkeypatch):
    """Bo cac cu sleep that, ghi lai so giay da xin cho."""
    xin: list[float] = []
    that = asyncio.sleep

    async def gia(s, *a, **k):
        xin.append(s)
        await that(0)

    monkeypatch.setattr(asyncio, "sleep", gia)
    return xin


def test_vuot_lien_tuc_lay_so_lan_lon_nhat():
    act = kind("Vuốt trái nhanh liên tục 3-4 lần trong <1s.")
    assert isinstance(act, act_resolver.Swipe) and (act.direction, act.lan) == ("left", 4)


def test_vuot_phai_roi_vuot_trai_giu_dung_thu_tu():
    act = kind("Vuốt phải về OB2, rồi vuốt trái quay lại OB3.")
    assert isinstance(act, act_resolver.Seq)
    assert [a.direction for a in act.actions] == ["right", "left"]


@pytest.mark.parametrize("step,giay", [
    ("Ở màn OB4, chờ thêm 5s quan sát.", 5.0),
    ("Ở OB3 chờ X hiện (5s).", 5.0),
    ("Ở OB3, chờ 3s (countdown đang chạy).", 3.0),
    ("Ở màn kế, chờ thêm 10s quan sát.", 10.0),
])
def test_o_man_nao_do_roi_cho(step, giay):
    act = kind(step)
    assert isinstance(act, act_resolver.Wait) and act.seconds == giay


def test_cho_qua_moc_thi_cho_hon_moc():
    """Cho dung 3s mac dinh la cham "khong tu chuyen man" khi timer chua het: PASS gia."""
    act = kind("Vào OB3, chờ quá 10s không thao tác.")
    assert isinstance(act, act_resolver.GoTo) and act.cho > 10


@pytest.mark.parametrize("step", ["Bấm giờ từ t0.", "Không thao tác gì, bấm giờ.",
                                  "Vào OB3, ad show tại t0, bấm giờ."])
def test_bam_gio_la_do_thoi_gian_khong_phai_tap(step):
    act = kind(step)
    assert isinstance(act, act_resolver.NeedsHuman) and "thời gian" in act.reason


def test_sau_do_chi_la_chu_noi():
    act = kind("Sau đó vuốt trái thủ công.")
    assert isinstance(act, act_resolver.Swipe) and act.direction == "left"


@pytest.mark.parametrize("step,giay", [("Nhấn Home đưa app xuống background 10s.", 10.0),
                                       ("nhấn Home (background 8s)", 8.0)])
def test_nhan_home(step, giay):
    act = kind(step)
    assert isinstance(act, act_resolver.Background) and act.seconds == giay


def test_xoay_luon_ket_thuc_o_man_doc():
    assert kind("Xoay ngang rồi xoay dọc thiết bị tại OB2.").orientations == ("ngang", "doc")
    assert kind("Xoay ngang thiết bị.").orientations == ("ngang", "doc")


def test_moc_t0_tach_ra_so_giay_va_ve_sau():
    assert act_compound.moc_t0("Tại t0+2s: vuốt trái thủ công.") == (2.0, "vuốt trái thủ công.")
    assert act_compound.moc_t0("Vuốt trái") is None


def test_hoan_thanh_splash_la_cho_het_splash():
    assert isinstance(kind("Hoàn thành Splash, quan sát màn inter_splash."), act_resolver.Wait)


def test_drive_vuot_lien_tuc_vuot_dung_so_lan(khong_cho):
    adb = fake()
    asyncio.run(case_drive.drive(adb, "29301FDH2006K7", PKG, ["Vuốt trái nhanh liên tục 3-4 lần"]))
    assert len(adb.cmds_with("input swipe")) == 4


def test_drive_xoay_xong_tra_che_do_xoay_ve_nhu_cu(khong_cho):
    adb = fake()
    adb.fails["settings get system accelerometer_rotation"] = ("1\n", "", 0)
    adb.fails["settings get system user_rotation"] = ("0\n", "", 0)
    asyncio.run(case_drive.drive(adb, "29301FDH2006K7", PKG, ["Xoay ngang rồi xoay dọc"]))
    put = [c for c in adb.cmds_with("settings put system")]
    assert put[-1].endswith("accelerometer_rotation 1")
    assert any(c.endswith("user_rotation 1") for c in put)


def test_drive_home_roi_mo_lai_app_thi_dua_app_len_that(khong_cho, monkeypatch):
    mo: list[str] = []

    async def launch(client, serial, package):
        mo.append(package)
        return package

    async def len_truoc(*a, **k):
        return 0.5

    monkeypatch.setattr(device_app, "launch", launch)
    monkeypatch.setattr(device_app, "wait_foreground", len_truoc)
    adb = fake()
    out = asyncio.run(case_drive.drive(adb, "29301FDH2006K7", PKG,
                                       ["Nhấn Home đưa app xuống background 10s.", "Mở lại app."]))
    assert adb.cmds_with("KEYCODE_HOME") and mo == [PKG]
    assert out["steps"][1]["action"]["kind"] == "resume"


def test_mo_lai_app_khi_khong_o_nen_thi_khong_mo_gi(khong_cho, monkeypatch):
    async def cam(*a, **k):
        raise AssertionError("khong duoc mo lai app")

    monkeypatch.setattr(device_app, "launch", cam)
    asyncio.run(case_drive.drive(fake(), "29301FDH2006K7", PKG, ["Mở lại app."]))


def test_drive_moc_t0_cho_toi_moc_va_ghi_lai_luc_lam(khong_cho):
    out = asyncio.run(case_drive.drive(fake(), "29301FDH2006K7", PKG,
                                       ["Tại t0+2s: vuốt trái thủ công."]))
    assert any(1.5 < s <= 2.0 for s in khong_cho)
    assert out["steps"][0]["moc"]["t0_cong"] == 2.0


def test_ctx_vuot_phai_lui_mot_trang(khong_cho):
    ctx = act_exec.ctx_moi()
    asyncio.run(act_exec.lam(fake(), "29301FDH2006K7", kind("Vuốt phải"), {}, ctx))
    assert ctx["vuot_sau"] == -1
