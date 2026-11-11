"""Cau ghep chon ngon ngu cua TC 3.6.2: "Chon Francais o LFO1, sang LFO2, bam tick." / "Chon Francais, di den OB3."."""

from __future__ import annotations

from rcr import act_resolver, fo_ngon_ngu


def test_tim_ngon_ngu_o_ve_dau_cau_ghep():
    assert fo_ngon_ngu.tim("", ["Chọn Français ở LFO1, sang LFO2, bấm tick."]) == ("Français", "Français")
    assert fo_ngon_ngu.tim("", ["Chọn English (United States) ở LFO1, sang LFO2, bấm tick."]) == \
        ("English", "English (United States)")
    assert fo_ngon_ngu.tim("", ["Chọn 'FR - Fun'.", "Chọn 1 style, bấm Go."]) is None


def test_ve_sau_chi_lai_qua_lfo_thi_la_chon_ngon_ngu():
    a = act_resolver.resolve("Chọn Français ở LFO1, sang LFO2, bấm tick.", [])
    assert a.summary == {"kind": "chon_ngon_ngu", "language": "Français", "reason": "chọn Français khi lái qua LFO"}


def test_ve_sau_duoc_dich_tiep():
    assert act_resolver.resolve("Chọn Français, đi đến OB3.", []).summary["target"] == "OnboardingActivity#3"
    assert act_resolver.resolve("Chọn Français, đi hết OB1 → OB4.", []).summary["target"] == "OnboardingActivity#4"
    assert act_resolver.resolve("Chọn Français, bấm giờ Skip ở OB1.", []).summary["kind"] == "watch"
