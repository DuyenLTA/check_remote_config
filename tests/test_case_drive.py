"""Test lai app qua cac buoc Action. Khong can may that.

Diem phai gac:
  - quang cao che man hinh -> DUNG, tuyet doi khong tu tim nut dong
  - buoc khong dich duoc -> dung ngay, khong lam tiep cac buoc sau
  - buoc dich duoc -> tap dung toa do tam node
  - buoc "di toi man X" -> giao cho fo_flow lai, khong bo cho nguoi
"""

from __future__ import annotations

import asyncio

from conftest import PKG, FakeAdb
from test_ui_dump import DUMP_XML

from rcr import case_drive, fo_flow

APP_XML = DUMP_XML.replace("com.ai.app", PKG)
COMPONENT = f"{PKG}/.MainActivity"
AD_COMPONENT = f"{PKG}/com.google.android.gms.ads.AdActivity"


def fake(activity=COMPONENT):
    return FakeAdb(fails={
        "dumpsys window": (f"  mCurrentFocus=Window{{4a2 u0 {activity}}}\n", "", 0),
        "uiautomator dump": ("UI hierchary dumped to: /data/local/tmp/rcr_uidump.xml\n", "", 0),
        "rcr_uidump.xml": (APP_XML, "", 0),
    })


def drive(adb, steps, man_can=None):
    """man_can=None = khong biet case noi ve man nao -> di het nhu TC bao."""
    return asyncio.run(case_drive.drive(adb, "29301FDH2006K7", PKG, steps, man_can=man_can))


def test_quang_cao_che_man_hinh_thi_dung_va_khong_tap():
    adb = fake(AD_COMPONENT)
    out = drive(adb, ["Mở tab Moment"])
    assert out["status"] == "NEEDS_HUMAN" and out["stopped_at"] == 1
    assert "quang cao" in out["steps"][0]["action"]["reason"]
    assert not adb.cmds_with("input tap")


def test_app_khac_bung_len_thi_dung():
    adb = fake("com.other.app/.Main")
    out = drive(adb, ["Mở tab Moment"])
    assert out["status"] == "NEEDS_HUMAN"
    assert "khong phai" in out["steps"][0]["action"]["reason"]


def test_lai_duoc_thi_tap_dung_tam_node():
    adb = fake()
    out = drive(adb, ["Mở tab Moment", "Quan sát màn hình"])
    assert out["status"] == "DONE"
    assert adb.cmds_with("input tap 540 2300")
    # Ban ghi cuoi la anh chup SAU khi lam xong, khong phai buoc cua TC.
    assert [s["action"]["kind"] for s in out["steps"][:-1]] == ["tap", "noop"]
    assert out["final"]["step"] == "(sau bước cuối)"
    # dump giu lai de phase 5 cham, khong phai chup lai
    assert "<hierarchy" in out["steps"][0]["dump"]


def test_buoc_khong_dich_duoc_thi_dung_ngay_khong_lam_tiep():
    adb = fake()
    out = drive(adb, ['Nhấn nút "See All"', "Mở tab Moment"])
    assert out["status"] == "NEEDS_HUMAN" and out["stopped_at"] == 1
    assert len(out["steps"]) == 1
    assert not adb.cmds_with("input tap")


def test_quang_cao_che_man_hinh_van_cho_buoc_QUAN_SAT_di_tiep():
    """Case ads cham bang log - inter de len truoc khi kip nhin banner la binh thuong."""
    adb = fake(AD_COMPONENT)
    out = drive(adb, ["Chờ Splash load", "Quan sát bottom banner"])
    assert out["status"] == "DONE"
    assert out["blocked_steps"] == [1, 2]
    # danh dau de phase 5 biet dump nay khong phai UI app
    assert all("screen_blocked" in s for s in out["steps"][:-1])
    assert not adb.cmds_with("input tap")


def test_quang_cao_van_chan_buoc_phai_bam():
    adb = fake(AD_COMPONENT)
    out = drive(adb, ["Quan sát màn hình", "Mở tab Moment"])
    assert out["status"] == "NEEDS_HUMAN" and out["stopped_at"] == 2
    assert "quang cao" in out["steps"][1]["action"]["reason"]
    assert not adb.cmds_with("input tap")


def test_buoc_di_toi_home_duoc_bo_lai_FO_lam_thay_vi_bo_cho_nguoi():
    """App dang o MainActivity roi -> `walk_to` toi ngay, buoc tinh la da chay."""
    adb = fake()
    out = drive(adb, ["Hoàn thành luồng FO đến Home."])
    assert out["status"] == "DONE" and out["stopped_at"] == 0
    assert out["steps"][0]["action"]["kind"] == "goto"
    assert out["steps"][0]["action"]["target"] == "MainActivity"


def test_lai_hut_thi_noi_ket_o_dau_chu_khong_noi_khong_dich_duoc_buoc(monkeypatch):
    """Loi nam o bo luat fo_flow, khong phai o cau chu trong file TC.

    Man `SettingsActivity` khong co luat nao khop -> `walk_to` khong lam duoc
    buoc nao, ket sau STUCK_POLLS vong. Rut poll ve 0s de test khong ngoi cho
    that 20 giay.
    """
    monkeypatch.setattr(fo_flow, "POLL_SECONDS", 0)
    monkeypatch.setattr(fo_flow, "STUCK_POLLS", 2)
    adb = fake(f"{PKG}/.SettingsActivity")
    out = drive(adb, ["Hoàn thành luồng FO đến Home."])
    assert out["status"] == "NEEDS_HUMAN" and out["stopped_at"] == 1
    assert "không lái tới được MainActivity" in out["steps"][0]["action"]["reason"]


def test_buoc_vuot_vuot_that_tren_may():
    adb = fake()
    out = drive(adb, ["Vuốt sang trái."])
    assert out["status"] == "DONE"
    assert [s["action"]["kind"] for s in out["steps"][:-1]] == ["swipe"]
    # Man mac dinh 1080x2400 -> vuot doc dai giua man, tu 80% ve 20% chieu ngang.
    assert adb.cmds_with("input swipe 864 1200 216 1200 300")


def test_quang_cao_che_man_khong_chan_buoc_vuot():
    """Vuot khong bam trung gi nen khong the bam nham vao quang cao.

    Va dung cai dang duoc test - icon SWIPE thay cho vung ad - nam o man co
    quang cao, chan o day la khong bao gio cham duoc case do.
    """
    adb = fake(AD_COMPONENT)
    out = drive(adb, ["Vuốt sang trái."])
    assert out["status"] == "DONE"
    assert adb.cmds_with("input swipe")


def test_buoc_di_toi_Home_bi_bo_khi_key_cua_case_nam_o_man_som_hon():
    """Ma vi tri noi san man: 102 o splash thi doc log o splash la du.

    Buoc Action cua TC van ghi "Hoan thanh luong FO den Home" - di het mat 16
    thao tac (~90 giay) ma khong them mot so do nao cho case nay.
    """
    adb = fake()
    out = drive(adb, ["Hoàn thành luồng FO đến Home."], man_can="")   # "" = splash
    assert out["status"] == "DONE"
    assert out["steps"][0]["action"]["kind"] == "noop"
    assert "không cần đi tiếp" in out["steps"][0]["action"]["reason"]


def test_van_di_toi_Home_khi_khong_biet_case_noi_ve_man_nao():
    """man_can=None (case khong co ma vi tri) -> di het nhu TC bao."""
    adb = fake()
    out = asyncio.run(case_drive.drive(
        adb, "29301FDH2006K7", PKG, ["Hoàn thành luồng FO đến Home."], man_can=None))
    assert out["steps"][0]["action"]["kind"] in ("goto", "needs_human")


def test_van_di_tiep_khi_man_cua_case_nam_sau(monkeypatch):
    """Case ve 303 (OB3) thi buoc di toi OB3 khong bi bo."""
    adb = fake()
    out = asyncio.run(case_drive.drive(
        adb, "29301FDH2006K7", PKG, ["Vào màn Onboarding 2."],
        man_can="OnboardingActivity#3"))
    assert out["steps"][0]["action"]["kind"] != "noop"


def test_trang_OB_suy_ra_khi_man_do_khong_co_cham_chi_trang():
    """OB3 la trang quang cao native toan man, khong cham nao de dem.

    Tool van biet: no DO duoc trang truoc do va chinh no vuot. Chi suy khi man
    that su doi - mot cu vuot khong an thi dump giong het, khong duoc tinh.
    """
    adb = fake()
    out = drive(adb, ["Vuốt sang trái."], man_can=None)
    cuoi = out["final"]
    assert cuoi["step"] == "(sau bước cuối)"
    # DUMP_XML khong co node `dot` -> khong doc duoc trang, va dump khong doi
    # (FakeAdb tra cung mot xml) -> KHONG suy bua.
    assert cuoi["page"] == 0 and cuoi["page_nguon"] == ""


def test_khong_suy_trang_khi_man_khong_doi():
    """Man khong doi = cu vuot khong an -> khong duoc tinh la da sang trang."""
    from rcr import drive_probes

    cuoi = asyncio.run(drive_probes._chup_ket(fake(), "29301FDH2006K7", PKG, 9,
                                    trang_cu=2, vuot=1, dump_cu=APP_XML))
    assert cuoi["page"] == 0
