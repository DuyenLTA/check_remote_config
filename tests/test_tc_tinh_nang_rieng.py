"""Bo TC tinh nang dung tu sheet goc: IAA (muc 3 ID ads inapp, sheet KT) va gen ngam (checklist rieng)."""

import pytest

from rcr import tc_iaa_tu_sheet_kt as iaa
from rcr import tc_loader, tc_tinh_nang_rieng as rieng
from rcr.models import RcError

ID = "ca-app-pub-1/{}"
DONG_KT = [
    ["Package name", "p.ai"],
    ["2. ID ads FO"],
    ["101_spl_a_banner", ID.format(1)],
    ["3. ID ads inapp"],
    ["1.0", "Loading", "native_loading_high", "1.0", "Native ad ở màn loading\n- Reload mỗi 5 giây\n* Tắt remote thì không preload",
     "Native", ID.format(11), "show_native_loading_high"],
    ["native_loading", "2.0", ID.format(12), "show_native_loading"],
    ["7.0", "Home", "501_home_banner_high", "1.0", "Hiển thị dưới chân màn Home, reload mỗi 10s", "Banner", ID.format(21)],
    ["Uninstall", "inter_uninstall", "2.0", "Hiển thị khi user click Uninstall ở màn Why", "Intersitial", ID.format(31)],
    ["4. ID ads resume"],
    [ID.format(41), "resume_high"],
]


def test_iaa_doc_muc_3_theo_noi_dung_o():
    ds = iaa.doc_muc_inapp(DONG_KT)
    assert [v.goc for v in ds] == ["native_loading", "501_home_banner", "inter_uninstall"]
    load = ds[0]
    assert load.man == "Loading" and load.loai == "Native"          # o STT "1.0" khong la ten man
    assert load.high.id == ID.format(11) and load.thuong.key == "show_native_loading"
    assert ds[1].high.key == "show_501_home_banner_high"           # thieu cot key -> show_<ten>
    assert ds[2].loai == "Interstitial" and ds[2].high is None       # sheet go sai "Intersitial"


def test_iaa_moi_vi_tri_bon_bien_the_tang_thieu_thi_bo():
    cases = iaa.tao_case(iaa.doc_muc_inapp(DONG_KT))
    assert [c.n for c in cases[:4]] == ["IAA-01-01", "IAA-01-02", "IAA-01-03", "IAA-01-04"]
    bat = cases[0]
    assert bat.test_data == "show_native_loading_high=true\nshow_native_loading=true"
    # Expected = nguyen van cot Ad description, khong them cau tu viet; cuoi cung la dong ID
    assert bat.expects[:3] == ("Native ad ở màn loading", "- Reload mỗi 5 giây", "* Tắt remote thì không preload")
    assert len(bat.expects) == 4
    assert ID.format(11) in bat.expects[-1] and ID.format(12) in bat.expects[-1]
    assert cases[3].test_data.endswith("show_native_loading=false") and "Không request" in cases[3].expects[0]
    # banner chi co tang high -> chi bat + tat
    assert [c.n for c in cases if c.n.startswith("IAA-02")] == ["IAA-02-01", "IAA-02-04"]


def test_iaa_tab_chua_dan_muc_3_bao_ro(tmp_path):
    import openpyxl
    wb = openpyxl.Workbook()
    for r in (["Package name", "p.ai"], ["3. ID ads inapp"], ["4. ID ads resume"]):
        wb.active.append(r)
    f = tmp_path / "kt.xlsx"
    wb.save(f)
    with pytest.raises(RcError, match="3. ID ads inapp"):
        iaa.tu_workbook(f, "p.ai")
    with pytest.raises(RcError, match="p.khac"):
        iaa.tu_workbook(f, "p.khac")


def test_gen_ngam_doc_tab_khuon_bo_tc_bo_qua_tab_checklist(tmp_path, monkeypatch):
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "TC Gen ngầm"
    ws.append(["Spec: gen ngầm"])
    ws.append(["TC ID", "Feature", "Test Description", "User State", "Test Data", "Precondition", "Action",
               "Expected Result"])
    ws.append(["GEN-R01-01", "R01", "Ảnh xong nhanh", "free", "generating_wait_image_seconds=15", "1. Clear data.",
               "1. Tạo ảnh.", "1. Vào thẳng Kết quả."])
    ws.append(["GEN-R01-02", "Màn chờ", "", "free", "", "1. Tiếp nối GEN-R01-01 (cùng lượt, không clear data).",
               "1. Ở yên.", "1. Không popup."])
    cl = wb.create_sheet("Checklist gen ngầm")
    cl.append(["Mục", "Nhóm", "Test data gợi ý", "Thao tác", "Expected"])
    goc = tmp_path / "gn.xlsx"
    wb.save(goc)
    monkeypatch.setattr(rieng.tc_source, "tai_ve", lambda link, out: str(goc))
    path, _, link = rieng.dung("gen-ngam", "p.ai", tmp_path)
    cases = tc_loader.load(path)
    assert link == rieng.LINK_GEN_NGAM and [c.n for c in cases] == ["GEN-R01-01", "GEN-R01-02"]
    assert cases[1].test_data == "generating_wait_image_seconds=15"      # Tiep noi ke thua Test Data


def test_dung_ra_xlsx_dung_khuon_va_bao_khi_noi_dung_doi(tmp_path, monkeypatch):
    import openpyxl
    wb = openpyxl.Workbook()
    for r in DONG_KT:
        wb.active.append(r)
    goc = tmp_path / "kt.xlsx"
    wb.save(goc)
    monkeypatch.setattr(rieng.tc_source, "tai_ve", lambda link, out: str(goc))
    assert rieng.la_nguon("IAA") and rieng.la_nguon("gen-ngam") and not rieng.la_nguon("rating")
    path, doi, _ = rieng.dung("iaa", "p.ai", tmp_path)
    assert not doi and [c.n for c in tc_loader.load(path)][:2] == ["IAA-01-01", "IAA-01-02"]
    assert rieng.dung("iaa", "p.ai", tmp_path)[1] is False             # dung lai, noi dung y het
    DONG_KT[6][4] = "Hiển thị dưới chân màn Home, reload mỗi 15s"
    try:
        wb = openpyxl.Workbook()
        for r in DONG_KT:
            wb.active.append(r)
        wb.save(goc)
        assert rieng.dung("iaa", "p.ai", tmp_path)[1] is True
    finally:
        DONG_KT[6][4] = "Hiển thị dưới chân màn Home, reload mỗi 10s"
