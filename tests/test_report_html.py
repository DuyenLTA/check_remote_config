"""Test dung trang report. Thuan du lieu - khong can may, khong can browser.

Diem phai gac:
  - KHONG mang dump XML vao report (vai tram KB mot dump -> report vai chuc MB)
  - anh nhung duoi dang data URI, co danh dau man bi che
  - loc theo verdict: moi case mang data-v de nut loc an/hien dung nhom
"""

from __future__ import annotations

from rcr import report_data, report_html

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
    assert 'class="blocked"' in out and "màn bị quảng cáo che" in out


def test_moi_case_mang_verdict_de_loc():
    _, out = page()
    assert 'data-v="NEEDS_HUMAN"' in out
    assert 'data-f="NEEDS_HUMAN"' in out  # nut loc


def test_moi_case_co_id_de_nhay_toi():
    _, out = page()
    assert 'id="c-6.4.0#1"' in out


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
    assert "<title>Lượt chấm app 3.5.4</title>" in out


def test_cot_trang_thai_tach_rieng_dong_cua_PO():
    """"cần người" va "PO đối soát" la hai viec khac nhau, khong duoc gop."""
    from rcr import report_row

    td = report_row._status({"verdict": "PASS", "pending": 0, "po": 1})
    assert "PO đối soát" in td and "cần người" not in td

    td = report_row._status({"verdict": "PASS", "pending": 2, "po": 1})
    assert "còn 2 dòng cần người" in td and "1 dòng PO đối soát" in td

    td = report_row._status({"verdict": "PASS", "pending": 0, "po": 0})
    assert "cần người" not in td and "PO" not in td
