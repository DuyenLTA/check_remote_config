"""Case "mo app khi mat mang": mang phai tat TRUOC luc app khoi dong.

Truoc day buoc "Mo app khong mang" khop LAUNCH_RE va thanh NoOp - ve "khong
mang" bi bo im, case chay voi mang day du roi bao PASS. Cac test duoi gac dung
cho do: thu tu lenh (svc truoc am start), va viec tra mang ve cuoi luot.
"""

from __future__ import annotations

import asyncio

from rcr import act_resolver, case_run, net_ctl

from test_cli_check import _adb_lai_duoc, adb_ui, baseline_of  # noqa: F401 - adb_ui la fixture

PRE_18 = """1. Cai build SDK visionlab:tutorial:3.5.0.
3. show_102_spl_n_inter_high1 = false (da fetch RC tu phien truoc).
4. Tat mang truoc khi mo app.
5. Trang thai user: new user."""


def test_doc_duoc_cau_tat_va_bat_lai_mang():
    assert act_resolver.resolve("Bật lại mạng khi vẫn đang trong luồng FO.", []).summary == {
        "kind": "net", "on": True, "reason": "bước bảo bật lại mạng"}
    assert act_resolver.resolve("Tắt mạng.", []).summary["on"] is False


def test_mo_app_khong_mang_khong_bi_nuot_thanh_mo_app_thuong():
    """Ve "khong mang" phai duoc nhac trong ly do, khong duoc bien mat."""
    ra = act_resolver.resolve("Mở app không mạng, chờ ở Splash.", []).summary
    assert ra["kind"] == "noop" and "mạng đang tắt" in ra["reason"]


def test_cau_co_internet_on_dinh_khong_bi_hieu_thanh_tat_mang():
    assert not net_ctl.tat_truoc_khi_mo("2. Thiet bi Android co internet on dinh.")


def test_tat_mang_doc_duoc_tu_precondition_lan_tu_buoc_action():
    assert net_ctl.tat_truoc_khi_mo(PRE_18)
    assert net_ctl.tat_truoc_khi_mo("", ["Mở app không mạng, chờ ở Splash."])
    assert not net_ctl.tat_truoc_khi_mo("", ["Mở app.", "Bật lại mạng."])


def test_ngat_mang_TRUOC_am_start_roi_tra_ve_cuoi_luot(adb_ui, tmp_path):
    """Ngat sau `am start` la app da fetch xong - do mot thu khac han."""
    bl = baseline_of(adb_ui)
    out = asyncio.run(case_run.apply_case(
        adb_ui, bl, {"enable_onb3_screen": "false"}, True, tmp_path,
        precondition=PRE_18,
    ))
    moc = [c for c in adb_ui.calls if "svc wifi" in c or "am start" in c]
    assert "svc wifi disable" in moc[0]
    assert "am start" in moc[1]
    # Luot sau chay tren may mat mang la hong het ma khong ai biet vi sao.
    assert "svc wifi enable" in moc[-1]
    assert out["net"]["mang"] == "tat"
    assert out["net_cuoi"]["thong"] is True


def test_khong_dong_toi_mang_khi_case_khong_yeu_cau(adb_ui, tmp_path):
    bl = baseline_of(adb_ui)
    asyncio.run(case_run.apply_case(
        adb_ui, bl, {"enable_onb3_screen": "false"}, True, tmp_path,
        precondition="2. Thiet bi co internet on dinh.",
    ))
    assert not [c for c in adb_ui.calls if "svc wifi" in c]


def test_precondition_di_qua_du_ba_tang_run_case(adb_ui, tmp_path):
    """run_case -> _apply_runs -> apply_case: thieu mot tang la mat ca ve mang."""
    adb_ui = _adb_lai_duoc(adb_ui)
    bl = baseline_of(adb_ui)
    asyncio.run(case_run.run_case(
        adb_ui, bl, [{"enable_onb3_screen": "false"}], PRE_18,
        steps=("Mở app không mạng, chờ ở Splash.",), out_dir=tmp_path,
        keep=True, dex=False, man_can="",
    ))
    assert [c for c in adb_ui.calls if "svc wifi disable" in c]


def test_dung_o_man_SAU_CUNG_ma_case_dong_toi_chu_khong_di_het():
    """Case tat mot loat unit truoc day khong ra vi tri nao -> di het toi Home.

    Case 17 tat 10 unit tu 102 (splash) den 303 (OB3): xa nhat la OB3, bon man
    sau do khong co unit nao cua case.
    """
    from rcr import assert_ads, fo_flow

    keys = {"show_102_spl_n_inter_high1", "show_201_lfo1_n_native_high1",
            "show_303_onb3_n_native_high2"}
    assert fo_flow.man_sau_cung(assert_ads.vi_tri_cua_case(keys)) == "OnboardingActivity#3"
    # Chi unit splash -> dung ngay o splash.
    assert fo_flow.man_sau_cung(
        assert_ads.vi_tri_cua_case({"show_102_spl_n_inter_high1"})) == ""
    # Ma khong biet -> di het, dung doan roi dung som.
    assert fo_flow.man_sau_cung(("999_gi_do",)) is None
    assert fo_flow.man_sau_cung(()) is None


def test_ngat_mang_KHONG_dung_de_gia_lap_no_fill():
    """Do tren may that 2026-09-28: ngat mang thi log KHONG CO unit nao - SDK
    khong gui noi request. No-fill that la "co request, kho khong tra ad".
    Lay ngat mang lam no-fill la cham mot trang thai khac han cai TC mo ta."""
    import inspect

    from rcr import case_run

    assert "ep_ad_fail" not in inspect.signature(case_run.apply_case).parameters
    # Mang chi duoc ngat khi CHINH precondition bao ngat, khong phai de gia lap
    # mot trang thai khac.
    nguon = inspect.getsource(case_run.apply_case)
    assert "net_ctl.tat_truoc_khi_mo(precondition, steps)" in nguon


def test_da_khong_fill_doc_tu_log_chu_khong_mac_dinh():
    from rcr import ad_positions, precond_guards as g

    vi_tri = ("302_onb2_n_native",)
    xin = [{"loaded": 0, "shown": 0, "rc_keys": ["id_302_onb2_n_native"]}]
    fill = [{"loaded": 1, "shown": 0, "rc_keys": ["id_302_onb2_n_native"]}]
    assert g.da_khong_fill(xin, vi_tri, ad_positions._khop_vi_tri)
    assert not g.da_khong_fill(fill, vi_tri, ad_positions._khop_vi_tri)
    # Khong co unit nao cua vi tri do trong log -> chua chung minh duoc gi.
    assert not g.da_khong_fill([], vi_tri, ad_positions._khop_vi_tri)
