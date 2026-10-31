"""Lai luong theo cau Action / precondition cua bo TC 3.6.1 (AIP886 2.7.0, 31/10/2026)."""

from __future__ import annotations

from rcr import act_resolver as r
from rcr import assert_check as a
from rcr import case_cham_them, fo_ngon_ngu, fo_steps, ui_dump

PKG = "com.ai.app"


def _row(i, text, left, top, rid="titleLanguageItem"):
    return (f'<node index="{i}" class="android.widget.TextView" package="{PKG}" resource-id="{PKG}:id/{rid}" '
            f'text="{text}" content-desc="" clickable="false" enabled="true" visible-to-user="true" '
            f'bounds="[{left},{top}][982,{top + 95}]" />')


def _lfo(*hang, rid="titleLanguageItem"):
    rows = "".join(_row(i, t, l, top, rid) for i, (t, l, top) in enumerate(hang))
    xml = (f"<?xml version='1.0' encoding='UTF-8'?><hierarchy rotation='0'><node index='0' "
           f"class='android.view.ViewGroup' package='{PKG}' resource-id='{PKG}:id/root' text='' content-desc='' "
           f"clickable='false' enabled='true' visible-to-user='true' bounds='[0,0][1080,2400]'>{rows}</node></hierarchy>")
    return ui_dump.app_nodes(ui_dump.parse_dump(xml))


ENGLISH_BUNG = _lfo(("Français", 202, 372), ("English", 202, 563), ("English (US)", 274, 754),
                    ("English (UK)", 274, 945), ("English (Canada)", 274, 1136), ("हिन्दी", 202, 1327))


def test_doc_ngon_ngu_tu_cau_action_va_precondition():
    assert fo_ngon_ngu.doc_cau("Chọn Français ở LFO1.") == ("Français", "Français")
    assert fo_ngon_ngu.doc_cau("Chọn English (United States) ở LFO1.") == ("English", "English (United States)")
    assert fo_ngon_ngu.doc_cau("Chọn 1 item.") is None
    pre = "1. Đã chạy xong R01 (đã complete_lfo_flow, ngôn ngữ đã chọn = Français).  2. Đổi remote"
    assert fo_ngon_ngu.tim(pre) == ("Français", "Français")


def test_chon_dung_bien_the_theo_ten_nuoc_viet_tat():
    ra = fo_steps.language_targets(ENGLISH_BUNG, "English", "English (United Kingdom)")
    assert [n.text for n in ra] == ["English (UK)"]
    assert [n.text for n in fo_steps.language_targets(ENGLISH_BUNG, "English")] == ["English (US)"]
    # bien the khong co tren man -> khong bam bua
    assert fo_steps.language_targets(ENGLISH_BUNG, "English", "English (Australia)") == []


def test_bien_the_trung_ten_goc_duoc_uu_tien():
    fr = _lfo(("Français", 202, 372), ("Français (Canada)", 274, 563), ("Français", 274, 754),
              ("English", 202, 945))
    assert [n.text for n in fo_steps.language_targets(fr, "Français", "Français")] == ["Français"]
    assert fo_steps.language_targets(fr, "Français", "Français")[0].bounds.top == 754


def test_cau_luong_fo_cua_tc361():
    assert r.resolve("Chọn Français ở LFO1.", []).summary["kind"] == "chon_ngon_ngu"
    assert r.resolve("Đi tiếp qua OB2.", []).summary == {
        "kind": "goto", "target": "OnboardingActivity#3", "reason": "đi tiếp qua OB2 (chụp mọi trang đi qua)"}
    assert r.resolve("Hoàn thành OB4.", []).summary["target"] == r.RA_KHOI_OB
    assert r.resolve("Đi hết luồng.", []).summary["target"] == "MainActivity"
    assert r.resolve("Mở lại từ Recent.", []).summary["kind"] == "resume"
    home = r.resolve("Bấm Home hệ thống → mở lại từ Recent.", []).summary
    assert [x["kind"] for x in home["actions"]] == ["background", "resume"]


def test_chon_1_item_bam_o_dau_tien():
    o = _lfo(("FR - Style 2", 578, 642), ("FR - Style 1", 57, 642), rid="tvQuestionTitle")
    ra = r.resolve("Chọn 1 item.", o)
    assert ra.summary["kind"] == "tap" and "Style 1" in ra.summary["node"]


def test_man_xa_nhat_trong_expected():
    assert case_cham_them.man_xa(["OB2: 'FR - OB2 title'", "OB4: 'FR - OB4 title'"]) == "OnboardingActivity#4"


def test_khong_hien_man_question_vao_thang_home():
    line = "Không hiển thị màn Question dù onboard_config_content_new có khối question, vào thẳng Home."
    ok = {"steps": [{"activity": ".VslTemplate4OnboardingActivity"}, {"activity": ".VslBillingActivity"}],
          "final": {"activity": ".AIP886MainActivity"}}
    assert a.check(line, {"units": {}}, ok, {"crashed": False})["verdict"] == a.PASS
    con_o_ob = {"steps": [{"activity": ".VslTemplate4OnboardingActivity"}],
                "final": {"activity": ".VslTemplate4OnboardingActivity"}}
    assert a.check(line, {"units": {}}, con_o_ob, {"crashed": False})["verdict"] == a.FAIL
    ad = {"steps": [], "final": {"activity": "com.google.android.gms.ads.AdActivity"}}
    assert a.check("Không hiển thị màn Question old user, vào thẳng Home.", {"units": {}}, ad,
                   {"crashed": False})["verdict"] == a.NEEDS_HUMAN
    hien = {"steps": [{"activity": ".VslTemplate4QuestionActivity"}], "final": {"activity": ".MainActivity"}}
    assert a.check(line, {"units": {}}, hien, {"crashed": False})["verdict"] == a.FAIL


def test_can_lai_tiep_toi_home_khi_ket_o_inter():
    drive = {"final": {"activity": "com.google.android.gms.ads.AdActivity"}}
    assert case_cham_them.can_ve_home(["Không hiển thị màn Question old user, vào thẳng Home."], drive)
    assert not case_cham_them.can_ve_home(["Splash UI theo splash_ui_config"], drive)


def test_ban_dich_khong_phan_biet_hoa_thuong():
    tai = {"ban_dich": {"Swipe to Next": ["Balayez pour continuer"]}}
    assert case_cham_them.ban_dich_cho(["text 'Swipe to next' đúng màu"], tai) == {
        "Swipe to next": ["Balayez pour continuer"]}


def test_indicator_dem_cham_khong_id_tren_dump_that():
    import pathlib
    xml = pathlib.Path(__file__).with_name("data_ob1_aip886.xml").read_text(encoding="utf-8")
    drive = {"steps": [{"n": 5, "activity": ".VslTemplate4OnboardingActivity", "dump": xml}]}
    ket = a.check("Indicator trang hiển thị đầy đủ, active ở trang 1 (fix bug mất indicator).", {"units": {}}, drive,
                  {"crashed": False})
    assert ket["verdict"] == a.PASS and "4 chấm" in ket["reason"]


def test_vao_home_binh_thuong_cham_bang_man_cuoi():
    ok = {"steps": [{"n": 1, "dump": "<node/>"}], "final": {"activity": "x.AIP886AIPhotoVideoMakerMainActivity"}}
    assert a.check("Vào Home bình thường.", {"units": {}}, ok, {"crashed": False})["verdict"] == a.PASS
    con = {"steps": [{"n": 1, "dump": "<node/>"}], "final": {"activity": "x.VslBillingActivity"}}
    assert a.check("Vào Home bình thường.", {"units": {}}, con, {"crashed": False})["verdict"] == a.FAIL


def test_ngon_ngu_lan_theo_chuoi_tiep_noi():
    cases = {"3.6.1#SDK361-R01-03": {"precondition": "1. Tiếp nối SDK361-R01-02", "actions": ["Chọn Français ở LFO1."]},
             "3.6.1#SDK361-R01-04": {"precondition": "1. Tiếp nối SDK361-R01-03 (cùng lượt, không clear data).",
                                     "actions": ["Đi tiếp qua OB2."]}}
    assert fo_ngon_ngu.tim_theo_chuoi("3.6.1#SDK361-R01-04", cases) == ("Français", "Français")
