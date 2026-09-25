"""Test dich buoc Action. Thuan ham tren cay node - khong can may.

Diem phai gac (nguyen tac: THA NEEDS_HUMAN CON HON DOAN):
  - nhieu node cung khop -> NeedsHuman, KHONG lay node dau tien
  - khong node nao khop -> NeedsHuman, khong tap bua
  - cau la -> NeedsHuman kem nguyen van, khong doan y
"""

from __future__ import annotations

import pytest
from test_ui_dump import DUMP_XML

from rcr import act_resolver, ui_dump

NODES = ui_dump.parse_dump(DUMP_XML)


def kind(step):
    return act_resolver.resolve(step, NODES)


@pytest.mark.parametrize("step", ["Quan sát màn hình", "Kiểm tra banner", "Observe the screen"])
def test_buoc_quan_sat_khong_thao_tac(step):
    assert isinstance(kind(step), act_resolver.NoOp)


def test_mo_tab_ra_dung_node_nav_bar():
    act = kind("Mở tab Moment")
    assert isinstance(act, act_resolver.Tap)
    assert (act.x, act.y) == (540, 2300)


def test_chuoi_trong_ngoac_kep_ra_tap():
    act = kind('Nhấn nút "Home"')
    assert isinstance(act, act_resolver.Tap) and (act.x, act.y) == (180, 2300)


def test_hai_node_cung_khop_thi_khong_doan():
    """2 hang deu co nut 'See All' - tap bua la vao nham hang."""
    act = kind('Nhấn nút "See All"')
    assert isinstance(act, act_resolver.NeedsHuman)
    assert "2 node" in act.reason


def test_khong_thay_node_thi_khong_tap_bua():
    act = kind('Nhấn nút "Khong Co Nut Nay"')
    assert isinstance(act, act_resolver.NeedsHuman) and "khong thay node" in act.reason


def test_cau_khong_dich_duoc_giu_nguyen_van():
    act = kind("Nhấn thẳng vào 1 thẻ style bất kỳ trong hàng AI Video")
    assert isinstance(act, act_resolver.NeedsHuman) and "thẻ style" in act.reason


@pytest.mark.parametrize("step,secs", [("Chờ 5 giây", 5.0), ("Đợi", 3.0), ("wait 2", 2.0)])
def test_buoc_cho(step, secs):
    act = kind(step)
    assert isinstance(act, act_resolver.Wait) and act.seconds == secs


def test_cho_qua_lau_la_TC_viet_nham():
    act = kind("Chờ 600 giây")
    assert isinstance(act, act_resolver.NeedsHuman)


def test_node_long_nhau_cung_khop_chi_tinh_node_ngoai():
    """Chu nam trong nut bam - cung mot cho, dung dem thanh 2 node."""
    xml = DUMP_XML.replace('text="AI Album"', 'text="AI Album Row"').replace(
        'resource-id="com.ai.app:id/rowAiAlbum"\n          text="" content-desc=""',
        'resource-id="com.ai.app:id/rowAiAlbum"\n          text="AI Album Row" content-desc=""',
    )
    act = act_resolver.resolve('Nhấn "AI Album Row"', ui_dump.parse_dump(xml))
    assert isinstance(act, act_resolver.Tap)


# --- buoc tool da lam roi ----------------------------------------------------

@pytest.mark.parametrize("step", [
    "Mở app", "Cold start app.", "Mở lại app", "Mở app → LFO1", "Khởi động app",
])
def test_buoc_mo_app_la_viec_tool_da_lam(step):
    """Tool tu mo app sau khi patch - buoc nay khong con gi de lam."""
    act = kind(step)
    assert isinstance(act, act_resolver.NoOp) and "da mo app" in act.reason


@pytest.mark.parametrize("step", ["Config RC", "Cấu hình remote config", "Đặt RC"])
def test_buoc_dat_config_la_viec_tool_da_lam(step):
    assert isinstance(kind(step), act_resolver.NoOp)


def test_bam_ten_nut_khong_ngoac_kep_van_ra_tap():
    act = kind("Bấm Moment.")
    assert isinstance(act, act_resolver.Tap) and (act.x, act.y) == (540, 2300)


def test_bam_ten_nut_van_phai_khop_duy_nhat():
    """Khong ngoac kep khong co nghia la duoc doan - van phai duy nhat."""
    assert isinstance(kind("Nhấn See All"), act_resolver.NeedsHuman)


@pytest.mark.parametrize("step", [
    "Hoàn thành luồng FO đến Home.", "Vào màn Onboarding 2.", "Trigger popup Rating.",
])
def test_di_ca_mot_chuoi_man_hinh_van_la_viec_cua_nguoi(step):
    """Ca mot chuoi man hinh, khong phai mot thao tac - doan la lac ngay buoc dau."""
    assert isinstance(kind(step), act_resolver.NeedsHuman)
