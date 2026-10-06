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
    assert isinstance(act, act_resolver.NeedsHuman) and "không thấy phần tử" in act.reason


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
    assert isinstance(act, act_resolver.NoOp) and "đã được mở lại" in act.reason


@pytest.mark.parametrize("step", ["Config RC", "Cấu hình remote config", "Đặt RC"])
def test_buoc_dat_config_la_viec_tool_da_lam(step):
    assert isinstance(kind(step), act_resolver.NoOp)


def test_bam_ten_nut_khong_ngoac_kep_van_ra_tap():
    act = kind("Bấm Moment.")
    assert isinstance(act, act_resolver.Tap) and (act.x, act.y) == (540, 2300)


def test_bam_ten_nut_van_phai_khop_duy_nhat():
    """Khong ngoac kep khong co nghia la duoc doan - van phai duy nhat."""
    assert isinstance(kind("Nhấn See All"), act_resolver.NeedsHuman)


@pytest.mark.parametrize("step,target", [
    ("Hoàn thành luồng FO đến Home.", "MainActivity"),
    ("Vào màn Onboarding 2.", "OnboardingActivity#2"),
    ("Chạy luồng FO đến OB3.", "OnboardingActivity#3"),
])
def test_buoc_di_toi_mot_man_hinh_giao_cho_bo_lai_FO(step, target):
    """Ca mot chuoi man hinh thi `fo_flow` lai, khong bo cho nguoi.

    Bo luat `data/fo_flow.yaml` biet duong di san - de nguyen NEEDS_HUMAN la
    case chet o buoc 2 trong khi tool thua suc di tiep.
    """
    act = kind(step)
    assert isinstance(act, act_resolver.GoTo) and act.target == target


@pytest.mark.parametrize("step", [
    # Khong man nao trong bo luat khop.
    "Trigger popup Rating.",
])
def test_cau_khong_thuan_di_chuyen_van_la_viec_cua_nguoi(step):
    assert isinstance(kind(step), act_resolver.NeedsHuman)


@pytest.mark.parametrize("step,target", [
    ("Chạy luồng FO đến OB3, quan sát banner.", "OnboardingActivity#3"),
    ("Vào màn Home; kiểm tra native ad.", "MainActivity"),
])
def test_ve_quan_sat_sau_dau_phay_khong_chan_buoc_di_chuyen(step, target):
    """Quan sat la viec cua buoc CHAM, khong phai mot thao tac phai lam.

    Chan ca cau chi vi co dau phay la bo cho nguoi mot buoc ma tool di duoc.
    """
    act = kind(step)
    assert isinstance(act, act_resolver.GoTo) and act.target == target


@pytest.mark.parametrize("step,direction", [
    ("Vuốt sang trái để qua màn tiếp theo.", "left"),
    # VUOT tai OB2, khong phai di toi OB2 - nhac ten man o giua cau khong tinh.
    ("Vuốt phải tại Onboarding 2.", "right"),
    ("Vuốt lên.", "up"),
    ("Swipe down", "down"),
])
def test_buoc_vuot_doc_duoc_huong_tu_cau(step, direction):
    act = kind(step)
    assert isinstance(act, act_resolver.Swipe) and act.direction == direction


def test_vuot_khong_neu_huong_thi_lay_huong_sang_trang_ke():
    """Doan sai huong vuot chi lam man khong doi - khac han mot cu tap sai cho.

    OB1/2/3 sang man bang vuot trai, va do cung la huong `fo_flow` dung.
    """
    act = kind("Vuốt theo đúng hướng icon gợi ý.")
    assert isinstance(act, act_resolver.Swipe) and act.direction == "left"


# --- buoc doi soat tren console ngoai ---------------------------------------
# Do that 2026-09-28: bo TC SDK 3.5.0 ban key ro, buoc 3 va 4 cua moi case ads.

@pytest.mark.parametrize("step", [
    "4. Mở AdMob console → tìm ad unit 106-spl-o-native-high1.",
    "3. Chờ AdMob console sync số liệu (theo chu kỳ báo cáo).",
    "Kiểm tra dashboard Firebase console.",
])
def test_buoc_doi_soat_console_ngoai_khong_chan_case(step):
    """Buoc nay khong dong gi den app - dung lai la bo luon cac buoc sau.

    Tool cham ads bang log cua may chu khong qua console, nen day la buoc cua
    nguoi doi soat tay. Dong Expected tuong ung van ra NOT_VERIFIABLE.
    """
    assert isinstance(kind(step), act_resolver.NoOp)


def test_nut_trong_app_ten_console_van_la_buoc_tap():
    """Chuoi trong ngoac kep la ten node trong app, khong phai console ngoai."""
    act = kind('Nhấn nút "Moment"')
    assert isinstance(act, act_resolver.Tap)
