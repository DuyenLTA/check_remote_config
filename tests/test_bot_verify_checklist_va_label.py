"""Verify: search label auto-qa (REST), prompt checklist Next-Gen, luot verify gop Jira + state."""

from __future__ import annotations

import asyncio
import io
import json
import urllib.error
import urllib.parse
from pathlib import Path

import pytest

from rcr import bot_chay_claude as c
from rcr import bot_job_verify as bj
from rcr import bot_jira_rest as jr
from rcr import bot_jira_rest as jira
from test_bot_job_verify import BUILD, _bot, _jira, _Kenh

URL, TOKEN = "https://jira.example", "SECRET-PAT-123"


class _Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


@pytest.fixture
def fake(monkeypatch):
    st = {"req": [], "tra": []}

    def urlopen(req, timeout):
        st["req"].append(req)
        r = st["tra"].pop(0)
        if isinstance(r, Exception):
            raise r
        return _Resp(json.dumps(r).encode())

    monkeypatch.setattr(jr._MO, "open", urlopen)
    return st


def _issue(key, desc, summary="tieu de"):
    return {"key": key, "fields": {"summary": summary, "description": desc}}


def test_tim_auto_qa_jql_va_marker(fake):
    fake["tra"] = [{"issues": [
        _issue("AIP920-1", "mo ta\nAUTOQA case=EV-07 ban=release pkg=com.a.b"),
        _issue("AIP920-2", "khong co marker"),
        _issue("../evil", "x")]}]
    ra = jr.tim_auto_qa(URL, TOKEN, "AIP920")
    q = urllib.parse.parse_qs(urllib.parse.urlsplit(fake["req"][0].full_url).query)
    assert q["jql"][0].startswith('project = AIP920 AND labels = "auto-qa" AND status = Reviewing')
    assert q["fields"] == ["summary,description"] and q["validateQuery"] == ["warn"]
    assert q["maxResults"] == [str(jr.MAX_AUTO_QA)]
    assert [i["key"] for i in ra] == ["AIP920-1", "AIP920-2"]               # key sai mau bi loai
    assert ra[0]["link"] == "https://jira.example/browse/AIP920-1"
    assert ra[0]["marker"] == {"case": "EV-07", "loai_ban": "release", "package": "com.a.b"}
    assert ra[1]["marker"] is None


@pytest.mark.parametrize("project", ["aip920", 'AIP920" OR 1=1', "A", "", "AIP920 AND x"])
def test_tim_auto_qa_chan_project_sai_mau(fake, project):
    with pytest.raises(jr.JiraLoi):
        jr.tim_auto_qa(URL, TOKEN, project)
    assert fake["req"] == []


def test_tim_auto_qa_loi_khong_lo_token(fake):
    fake["tra"] = [urllib.error.HTTPError(URL, 401, "x", {}, io.BytesIO(b"nope"))]
    with pytest.raises(jr.JiraLoi) as e:
        jr.tim_auto_qa(URL, TOKEN, "AIP920")
    assert TOKEN not in str(e.value) and "401" in str(e.value)


def test_luot_verify_checklist_prompt_va_khong_lan_tc():
    cmd, prompt = c.lenh("pkg.a", "S1", ["EV-07", "HT-03", "1.7"])
    assert prompt.startswith("/rc-check pkg.a --serial S1\n\n") and "--case" not in prompt.split("\n")[0]
    assert "rcr-sdk-check" in prompt and "EV-07, HT-03, 1.7" in prompt and "KHOP -> PASS" in prompt
    assert "KHONG doc/sua/log Jira" in prompt and '"cases"' in prompt
    assert not any("\n" in a for a in cmd)                 # prompt di qua stdin
    assert c.TIMEOUT_VERIFY_CHECKLIST == 70 * 60 > c.TIMEOUT_VERIFY
    with pytest.raises(ValueError):                        # TC lan checklist -> tu choi, khong doan
        c.lenh("pkg.a", "S1", ["EV-07", "a#1"])


def _item(key, marker):
    return {"key": key, "link": f"u-{key}", "summary": "s", "marker": marker}


MK = {"case": "EV-07", "loai_ban": "debug", "package": "pkg.a"}


def test_ung_vien_gop_label_jira_voi_state_chi_giu_bug_dang_reviewing(tmp_path, monkeypatch):
    # AIP920-30: chi co tren Jira (log tu terminal); AIP920-13: co label + state -> khong trung;
    # AIP920-14: chi o state, khong Reviewing -> bo
    _jira(monkeypatch, {"AIP920-13"}, tu_jira=[_item("AIP920-30", MK), _item("AIP920-13", None), _item("AIP920-31", None)])
    uv = asyncio.run(bj._ung_vien(_bot(tmp_path), "AIP920"))
    assert {u["key"]: u["case"] for u in uv} == {"AIP920-30": "EV-07", "AIP920-13": "3.6.1#1", "AIP920-31": ""}


def test_xep_bug_chi_co_tren_jira_va_thieu_marker(tmp_path, monkeypatch):
    _jira(monkeypatch, set(), tu_jira=[_item("AIP920-30", MK), _item("AIP920-31", None),
                                       _item("AIP920-32", {**MK, "package": "pkg.b"})])
    bot, kenh = _bot(tmp_path), _Kenh()
    bot.q.tin = {}
    asyncio.run(bj.xep(bot, BUILD, kenh))
    j = bot.q.jobs[0]
    assert [u["key"] for u in j["verify"]] == ["AIP920-30"]
    ly = {u["key"]: u["ly_do"] for u in j["bo_qua"]}
    assert ly["AIP920-31"] == "thiếu marker auto-qa — cần verify tay" and "pkg.b" in ly["AIP920-32"]


def test_verify_checklist_chay_prompt_checklist_timeout_dai_va_map_verdict(tmp_path, monkeypatch):
    goi = _jira(monkeypatch, set(), tu_jira=[_item("AIP920-30", MK), _item("AIP920-33", {**MK, "case": "HT-03"})])
    bot = _bot(tmp_path)
    bot.q.tin = {}
    asyncio.run(bj.xep(bot, BUILD, _Kenh()))
    job = bot.q.jobs[0]
    monkeypatch.setattr(bj.bot_cong_viec, "cai", lambda *a: {"ok": True})
    da_chay = []
    kq = {"trang_thai": "XONG", "tom_tat": "t", "cases": [
        {"case": "EV-07", "verdict": "KHOP", "thuc_te": "ok"}, {"case": "HT-03", "verdict": "DO_TAY", "thuc_te": "chua do"}]}
    monkeypatch.setattr(bj.bot_chay_claude, "chay", lambda *a: da_chay.append((a[3], a[-1])) or kq)
    monkeypatch.setattr(bj.bot_cong_viec, "file_report", lambda kq, out: None)
    monkeypatch.setattr(jira, "dang_reviewing", lambda u, t, keys: list(keys))
    asyncio.run(bj.chay(bot, job, "S1", "Pixel", Path("."), tmp_path))
    assert da_chay == [(c.TIMEOUT_VERIFY_CHECKLIST, ["EV-07", "HT-03"])]
    assert [g for g in goi if g[0] == "chuyen"] == [("chuyen", "AIP920-30", "Done")]   # KHOP -> Done; DO_TAY giu Reviewing
    assert "Giữ Reviewing" in bot.msg.edits[-1]["content"]
