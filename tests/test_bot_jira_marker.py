"""Marker AUTOQA trong description bug + hop nhat ung vien Jira / state."""

from __future__ import annotations

import pytest

from rcr import bot_jira_marker as m
from rcr import bot_log_jira as lj


@pytest.mark.parametrize("case", ["3.6.1#SDK361-SPL-001", "daily checkin#4", "SDK350-OB3X-013", "EV-07", "1.7"])
def test_dong_marker_roi_doc_lai_dung_gia_tri(case):
    dong = m.dong_marker(case, "debug", "com.apero.app_x")
    assert dong == f"AUTOQA case={case} ban=debug pkg=com.apero.app_x"
    mo_ta = f"Mo ta bug\n\nReport: https://x\n{dong}\n"
    assert m.doc_marker(mo_ta) == {"case": case, "loai_ban": "debug", "package": "com.apero.app_x"}


def test_dong_marker_tu_choi_gia_tri_sai():
    for args in (("x y z", "debug", "p.a"), ("EV-07", "beta", "p.a"), ("EV-07", "debug", "p a"),
                 ("EV-07\nx", "debug", "p.a")):
        with pytest.raises(ValueError):
            m.dong_marker(*args)


def test_doc_marker_nghiem_va_chiu_escape_wiki():
    assert m.doc_marker("AUTOQA case=EV-07 ban=release pkg=p.a   ")["loai_ban"] == "release"
    assert m.doc_marker("AUTOQA case=EV\\-07 ban=debug pkg=p.a")["case"] == "EV-07"     # Jira escape
    for xau in (None, "", "khong co", "AUTOQA case=EV-07 ban=beta pkg=p.a", "AUTOQA case=zzz ban=debug pkg=p.a",
                "AUTOQA case=EV-07 ban=debug pkg=p a", "x AUTOQA case=EV-07 ban=debug pkg=p.a", 123):
        assert m.doc_marker(xau) is None, xau
    # dong dau hong, dong sau hop le -> lay dong hop le
    assert m.doc_marker("AUTOQA case=zzz ban=debug pkg=p.a\nAUTOQA case=a#1 ban=debug pkg=p.a")["case"] == "a#1"


def test_gop_jira_chinh_state_du_phong_khong_trung_key():
    mk = {"case": "EV-07", "loai_ban": "release", "package": "p.a"}
    jira_items = [
        {"key": "A-1", "link": "https://j/A-1", "summary": "s1", "marker": mk},
        {"key": "A-2", "link": "https://j/A-2", "summary": "s2", "marker": None},       # co trong state
        {"key": "A-3", "link": "https://j/A-3", "summary": "s3", "marker": None},       # khong ai biet case
    ]
    state = [{"key": "A-1", "link": "u", "case": "a#1", "bug": {}, "loai_ban_goc": "debug"},
             {"key": "A-2", "link": "u2", "case": "a#2", "bug": {"expected": "e"}, "loai_ban_goc": "debug"},
             {"key": "A-9", "link": "u9", "case": "a#9", "bug": {}, "loai_ban_goc": "debug"}]
    ra = {u["key"]: u for u in m.gop(jira_items, state)}
    assert sorted(ra) == ["A-1", "A-2", "A-3", "A-9"]
    assert (ra["A-1"]["case"], ra["A-1"]["loai_ban_goc"], ra["A-1"]["package"]) == ("EV-07", "release", "p.a")
    assert ra["A-2"]["case"] == "a#2" and ra["A-3"]["case"] == "" and ra["A-9"]["case"] == "a#9"


def test_log_jira_them_marker_vao_file_bug():
    bugs = lj.them_marker([{"case": "EV-07"}, {"case": "khong hop le"}], "debug", "p.a")
    assert bugs[0]["marker"] == "AUTOQA case=EV-07 ban=debug pkg=p.a" and "marker" not in bugs[1]
    assert "auto-qa" in lj.PROMPT and "marker" in lj.PROMPT
