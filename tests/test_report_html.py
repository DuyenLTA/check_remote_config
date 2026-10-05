"""Test dung trang report. Thuan du lieu - khong can may, khong can browser.

Diem phai gac:
  - KHONG mang dump XML vao report (vai tram KB mot dump -> report vai chuc MB)
  - anh nhung duoi dang data URI, co danh dau man bi che
  - loc theo nhan: verdict cua tool duoc dich sang 4 o PASS/FAIL/BLOCKED/N-A
  - moi dong Expected di kem ket qua cua CHINH dong do, khong phai hai cot song song
"""

from __future__ import annotations

from rcr import report_data, report_html, report_row

RESULT = {
    "verdict": "NEEDS_HUMAN",
    "reset": {"mode": "soft", "matched": "first open"},
    "runs": [{
        "overrides": {"splash_banner_change": "false"},
        "verdict": "NEEDS_HUMAN",
        "assert": {"verdict": "NEEDS_HUMAN", "lines": [
            {"n": 1, "verdict": "PASS", "expected": "Không crash", "reason": "khong thay crash"},
            {"n": 2, "verdict": "NEEDS_HUMAN", "expected": "Banner hiển thị",
             "reason": "chua lai toi man nao khac"},
        ]},
        "ads": {"units": {"banner:*****825": {"type": "banner", "unit": "*****825", "requested": 1,
                                              "loaded": 0, "shown": 0, "rc_keys": []}},
                "banner_states": [{"state": "None"}, {"state": "Loading"}]},
        "drive": {"status": "DONE", "steps": [
            {"n": 1, "step": "Mở app", "action": {"kind": "noop"}, "activity": "SplashActivity",
             "dump": "<hierarchy>" + "x" * 5000 + "</hierarchy>",
             "shot": "data:image/jpeg;base64,AAAA", "shot_warning": ""},
            {"n": 2, "step": "Quan sát banner", "action": {"kind": "noop"},
             "dump": "<hierarchy/>", "shot": "data:image/jpeg;base64,BBBB",
             "shot_warning": "", "screen_blocked": "quang cao dang che man hinh"},
        ]},
    }],
}
ROW = {"key": "6.4.0#1", "tab": "TC SDK 6.4.0", "label": "#1 bật cả 2 banner"}


class FakeBaseline:
    serial = "29301FDH2006K7"
    package = "com.ai.app"
    configs = {"a": "1", "b": "2"}
    mirrored_keys = frozenset({"a"})


def page():
    rec = report_data.case_record("6.4.0#1", ROW, RESULT)
    data = report_data.page_data(FakeBaseline(), {"total": 538, "runnable": 347, "sdk": "3.5.4"}, [rec])
    return rec, report_html.build(data)


def test_khong_mang_dump_xml_vao_report():
    rec, out = page()
    assert all("dump" not in s for s in rec["steps"])
    assert "xxxxxxxxxx" not in out


def test_anh_tung_buoc_va_danh_dau_man_bi_che():
    _, out = page()
    assert out.count("data:image/jpeg;base64,") == 2
    # Man bi quang cao che: danh dau o DU LIEU cua buoc, renderer doc ra chu.
    assert '"blocked": true' in out


def test_moi_case_mang_verdict_de_loc():
    """Nhan tren bang tong ket chi co 4 o - verdict goc van di kem de tra."""
    _, out = page()
    assert '"status": "BLOCKED"' in out and '"verdict": "NEEDS_HUMAN"' in out
    for f in ("ALL", "FAIL", "BLOCKED", "PASS", "NA"):
        assert f'data-f="{f}"' in out


def test_moi_case_co_id_de_nhay_toi():
    """Renderer dung id `c<so case>`; so case phai ra dung tu khoa co tab."""
    rec, out = page()
    assert report_row.build(rec)["n"] == "1"


def test_nhom_theo_tinh_nang_cua_file_TC():
    rec = report_data.case_record("6.4.0#1", dict(ROW, feature="Splash UI mới"), RESULT)
    assert rec["group"] == "Splash UI mới"
    data = report_data.page_data(FakeBaseline(), {"total": 1, "runnable": 1, "sdk": "3.5.4"}, [rec])
    assert "Splash UI mới" in report_html.build(data)


def test_cau_ta_lai_luot_chay_dem_chu_khong_liet_ke_tung_unit():
    """Bang ads ngay duoi da co `req/load/show` tung unit.

    Chep lai bang chu la doc hai lan cung mot thu, va lam troi mat nhung y chi
    co o dong nay: lai may buoc, config co song qua lan mo app khong.
    """
    rec, out = page()
    assert "unit được request" in rec["actual"]
    assert "*****825" not in rec["actual"]
    assert "adBannerState None → Loading" in rec["actual"]


def test_tung_dong_expected_len_bang():
    _, out = page()
    assert "Không crash" in out and "chua lai toi man nao khac" in out


def test_tieu_de_theo_app_va_ban_sdk():
    _, out = page()
    assert "<title>Lượt chấm app · SDK FO 3.5.4</title>" in out


def test_dich_verdict_sang_bon_o_cua_bang_tong_ket():
    """Tool phan biet 7 verdict; bang tong ket cua tester chi co 4 o.

    BLOCKED = chay lai thi ra ket qua (viec cua tester).
    N/A = ngoai pham vi tester (console cua PO, dong phai nhin mat).
    """
    assert report_row.nhan_cua("PASS") == "PASS"
    assert report_row.nhan_cua("FAIL") == "FAIL"
    assert report_row.nhan_cua("NEEDS_HUMAN") == "BLOCKED"
    assert report_row.nhan_cua("BLOCKED") == "BLOCKED"
    assert report_row.nhan_cua("KEY_NOT_USED") == "BLOCKED"
    assert report_row.nhan_cua("NOT_VERIFIABLE") == "NA"
    # Verdict la chua ai dich -> BLOCKED de nguoi doc nhin thay, khong lan vao
    # o "ngoai pham vi" roi khong ai dong toi.
    assert report_row.nhan_cua("MOT_TRANG_THAI_MOI") == "BLOCKED"


def test_moi_dong_Expected_di_kem_ket_qua_cua_chinh_no():
    """Truoc day Expected va Actual la hai cot danh so song song - phai doi
    chieu bang mat. Gio moi dong mang nhan + ly do cua chinh dong do."""
    rec, _ = page()
    d = report_row.build(rec)
    assert len(d["expects"]) == len(d["lines"])
    assert {"s", "r", "v"} <= set(d["lines"][0])


def test_tieu_de_khong_de_dau_gach_cut_khi_chua_biet_ban_SDK():
    """"—" la cho HIEN o o trong bang, ghep vao tieu de thanh dau gach cut duoi.

    Do 2026-09-28: workbook mot sheet khong kich hoat buoc do SDK, tieu de ra
    "Luot cham Piclux · SDK FO 3.5.0 —".
    """
    data = report_data.page_data(FakeBaseline(), {"total": 2, "runnable": 2, "sdk": ""},
                                 [], app_label="Piclux 2.8.0")
    assert data["title"] == "Lượt chấm Piclux 2.8.0"
    assert not data["title"].rstrip().endswith("—")
    assert data["eyebrow"] == "Remote Config Case Runner"
    # O trong BANG van hien "—": cho trong khong noi duoc la chua do hay bang 0.
    assert data["spec"]["SDK First Open"] == "—"


def test_tieu_de_co_ban_SDK_thi_ghep_vao():
    data = report_data.page_data(FakeBaseline(), {"total": 2, "runnable": 2, "sdk": "3.5.0"},
                                 [], app_label="Piclux 2.8.0")
    assert data["title"] == "Lượt chấm Piclux 2.8.0 · SDK FO 3.5.0"


def test_buoc_khong_thao_tac_phai_noi_duoc_VI_SAO():
    """"noop" tren report khong noi duoc gi, va no la nhan hay gap nhat.

    Te hon: buoc da lai toi man roi dung dung cho cung ra "noop" - doc vao
    tuong tool khong lam gi ca (do 2026-09-28, case 17 buoc 1).
    """
    rec, _ = page()
    d = report_row.build(rec)
    assert all("r" in s for s in d["steps"]), "buoc phai mang theo ly do"


def test_report_khong_ro_ma_thao_tac_noi_bo_ra_ngoai():
    """Tester doc `noop`/`goto`/`net` thi khong hieu gi - phai dich sang chu."""
    from rcr.report_js import JS

    for ma, chu in (("noop", "không cần thao tác"), ("goto", "lái qua luồng FO"),
                    ("net", "đổi trạng thái mạng"), ("tap", "bấm")):
        assert f"{ma}: \"{chu}\"" in JS


def test_moi_loai_thao_tac_deu_co_nhan_tieng_viet():
    """Them loai thao tac moi ma quen nhan la ma noi bo lai lot ra report."""
    import re

    from rcr import act_types
    from rcr.report_js import JS

    kinds = set(re.findall(r'"kind": "(\w+)"', open(act_types.__file__, encoding="utf-8").read()))
    kinds |= {"resume"}          # case_drive gan khi dua app tu nen len
    thieu = [k for k in kinds if not re.search(rf"\b{k}: \"", JS)]
    assert not thieu, f"thieu nhan cho: {thieu}"
