"""Keo bug auto-qa tu backlog vao sprint active: urlopen gia, khong cham mang that."""

from __future__ import annotations

import io
import json
import urllib.parse

import pytest

from rcr import bot_jira_rest as jr
from rcr import bot_keo_sprint as ks

URL, TOKEN = "https://jira.example", "SECRET-PAT-123"


class _Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


@pytest.fixture
def fake(monkeypatch):
    """Tra loi theo duong dan (bo query) -> danh sach phan hoi; ghi lai moi request."""
    st = {"req": [], "tra": {}}

    def urlopen(req, timeout):
        st["req"].append(req)
        r = st["tra"][urllib.parse.urlsplit(req.full_url).path].pop(0)
        if isinstance(r, Exception):
            raise r
        return _Resp(json.dumps(r).encode() if r is not None else b"")

    monkeypatch.setattr(jr._MO, "open", urlopen)
    monkeypatch.setattr(jr, "CHO_THU_LAI", 0)
    return st


def _tim(*keys):
    return {"issues": [{"key": k} for k in keys]}


def test_jql_chi_bug_auto_qa_ngoai_sprint_chua_xong(fake):
    fake["tra"]["/rest/api/2/search"] = [_tim("AIP882-110", "AIP882-111", "AIP920-5", "bad key")]
    assert ks.bug_ngoai_sprint(URL, TOKEN) == {"AIP882": ["AIP882-110", "AIP882-111"], "AIP920": ["AIP920-5"]}
    jql = urllib.parse.parse_qs(urllib.parse.urlsplit(fake["req"][0].full_url).query)["jql"][0]
    assert jql == 'labels = "auto-qa" AND sprint is EMPTY AND statusCategory != Done ORDER BY key'


def test_keo_vao_sprint_active_bo_qua_project_chua_co_sprint(fake):
    fake["tra"] = {
        "/rest/api/2/search": [_tim("AIP882-110", "AIP882-111", "AIP920-5")],
        "/rest/agile/1.0/board": [{"values": [{"id": 9, "type": "kanban"}, {"id": 351, "type": "scrum"}]},
                                  {"values": [{"id": 400, "type": "scrum"}]}],
        "/rest/agile/1.0/board/351/sprint": [{"values": [{"id": 77, "name": "Sprint 5"}]}],
        "/rest/agile/1.0/board/400/sprint": [{"values": []}],
        "/rest/agile/1.0/sprint/77/issue": [None],
    }
    dong = ks.keo(URL, TOKEN)
    assert len(dong) == 1 and "AIP882" in dong[0] and "Sprint 5" in dong[0] and "AIP882-111" in dong[0]
    post = [r for r in fake["req"] if r.get_method() == "POST"]
    assert len(post) == 1 and json.loads(post[0].data) == {"issues": ["AIP882-110", "AIP882-111"]}
    assert not any("/board/9/" in r.full_url for r in fake["req"])   # kanban khong hoi sprint


def test_loi_mot_project_khong_chan_project_khac(fake):
    fake["tra"] = {
        "/rest/api/2/search": [_tim("AIP882-110", "AIP920-5")],
        "/rest/agile/1.0/board": [jr.urllib.error.HTTPError(URL, 500, "x", {}, io.BytesIO(b"loi")),
                                  {"values": [{"id": 400, "type": "scrum"}]}],
        "/rest/agile/1.0/board/400/sprint": [{"values": [{"id": 8, "name": "S1"}]}],
        "/rest/agile/1.0/sprint/8/issue": [None],
    }
    dong = ks.keo(URL, TOKEN)
    assert len(dong) == 1 and "AIP920" in dong[0]


def test_khong_co_bug_khong_goi_board(fake):
    fake["tra"]["/rest/api/2/search"] = [{"issues": []}]
    assert ks.keo(URL, TOKEN) == []
    assert len(fake["req"]) == 1
