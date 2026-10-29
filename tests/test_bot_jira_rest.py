"""Jira REST cua bot verify: urlopen gia, khong cham mang that."""

from __future__ import annotations

import io
import json
import urllib.error
import urllib.parse

import pytest

from rcr import bot_jira_rest as jr

URL, TOKEN = "https://jira.example", "SECRET-PAT-123"


class _Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


@pytest.fixture
def fake(monkeypatch):
    """Ghi lai request; `tra` la danh sach phan hoi (dict -> JSON, Exception -> raise)."""
    st = {"req": [], "tra": []}

    def urlopen(req, timeout):
        st["req"].append(req)
        r = st["tra"].pop(0)
        if isinstance(r, Exception):
            raise r
        return _Resp(json.dumps(r).encode() if r is not None else b"")

    monkeypatch.setattr(jr._MO, "open", urlopen)
    monkeypatch.setattr(jr, "CHO_THU_LAI", 0)
    return st


def _jql(req) -> str:
    return urllib.parse.parse_qs(urllib.parse.urlsplit(req.full_url).query)["jql"][0]


def test_bat_can_token_va_https():
    assert jr.bat(URL, TOKEN)
    assert not jr.bat(URL, "")
    assert not jr.bat("http://jira.example", TOKEN)


def test_keys_rong_khong_goi_mang(fake):
    assert jr.dang_reviewing(URL, TOKEN, []) == []
    assert fake["req"] == []


def test_key_ban_bi_loai_khoi_jql(fake):
    fake["tra"].append({"issues": []})
    jr.dang_reviewing(URL, TOKEN, ["AIP920-13", "AIP920-13) OR 1=1", "aip-1"])
    assert _jql(fake["req"][0]) == "key in (AIP920-13) AND status = Reviewing"


def test_key_ban_het_thi_khong_goi(fake):
    assert jr.dang_reviewing(URL, TOKEN, ["x) OR 1=1"]) == []
    assert fake["req"] == []


def test_search_tra_mot_phan(fake):
    fake["tra"].append({"issues": [{"key": "AIP920-13"}, {"key": "AIP920-15"}]})
    assert jr.dang_reviewing(URL, TOKEN, ["AIP920-13", "AIP920-14", "AIP920-15"]) == ["AIP920-13", "AIP920-15"]
    q = urllib.parse.parse_qs(urllib.parse.urlsplit(fake["req"][0].full_url).query)
    assert q["validateQuery"] == ["warn"] and q["maxResults"] == ["3"]
    assert fake["req"][0].get_header("Authorization") == f"Bearer {TOKEN}"


def test_chuyen_theo_ten_khong_phan_biet_hoa_thuong(fake):
    fake["tra"] += [{"transitions": [{"id": "11", "name": "To Do"}, {"id": "31", "name": "Done"}]}, None]
    jr.chuyen(URL, TOKEN, "AIP920-13", "done")
    post = fake["req"][1]
    assert post.get_method() == "POST" and post.full_url.endswith("/issue/AIP920-13/transitions")
    assert json.loads(post.data) == {"transition": {"id": "31"}}


def test_khong_co_transition_thi_loi(fake):
    fake["tra"].append({"transitions": [{"id": "11", "name": "To Do"}]})
    with pytest.raises(jr.JiraLoi, match=r"khong co transition 'Done'.*To Do -> \?"):
        jr.chuyen(URL, TOKEN, "AIP920-13", "Done")
    assert len(fake["req"]) == 1


def test_comment_gui_body(fake):
    fake["tra"].append({"id": "1"})
    jr.comment(URL, TOKEN, "AIP920-13", "Bot verify: PASS")
    assert json.loads(fake["req"][0].data) == {"body": "Bot verify: PASS"}


def test_key_sai_mau_khong_goi(fake):
    with pytest.raises(jr.JiraLoi):
        jr.comment(URL, TOKEN, "../AIP920-13", "x")
    with pytest.raises(jr.JiraLoi):
        jr.chuyen(URL, TOKEN, "AIP920-13/x", "Done")
    assert fake["req"] == []


@pytest.mark.parametrize("ma", [400, 401])
def test_loi_http_khong_lo_token(fake, ma):
    fake["tra"].append(urllib.error.HTTPError(URL, ma, "loi", {}, io.BytesIO(b'{"errorMessages":["x"]}')))
    with pytest.raises(jr.JiraLoi) as e:
        jr.dang_reviewing(URL, TOKEN, ["AIP920-13"])
    assert f"HTTP {ma}" in str(e.value) and TOKEN not in str(e.value) and "jql" not in str(e.value)


def test_mat_mang(fake):
    fake["tra"] += [urllib.error.URLError("timed out")] * jr.SO_LAN_THU
    with pytest.raises(jr.JiraLoi, match="khong ket noi"):
        jr.comment(URL, TOKEN, "AIP920-13", "x")


def test_trang_html_200_cung_thanh_jira_loi(monkeypatch):
    monkeypatch.setattr(jr._MO, "open", lambda req, timeout: _Resp(b"<html>SSO login</html>"))
    with pytest.raises(jr.JiraLoi, match="JSONDecodeError") as e:
        jr.dang_reviewing(URL, TOKEN, ["AIP920-13"])
    assert TOKEN not in str(e.value)


def test_khong_theo_redirect_de_khong_lo_token():
    assert jr._KhongRedirect().redirect_request(None, None, 302, "Found", {}, "http://sso.evil/") is None


def test_key_co_xuong_dong_bi_loai(fake):
    assert jr.dang_reviewing(URL, TOKEN, ["AIP920-13\n"]) == [] and fake["req"] == []


# Workflow bug that tren jira.apero.vn (AIP922-106, 29/10/2026): tu Reviewing chi co 2 transition nay.
REVIEWING = {"transitions": [{"id": "91", "name": "Reject Issue", "to": {"name": "Reopened"}},
                             {"id": "101", "name": "Close Issue", "to": {"name": "Closed"}}]}


@pytest.mark.parametrize("dich, tid", [(jr.DICH_FAIL, "91"), (jr.DICH_PASS, "101")])
def test_reviewing_chon_theo_trang_thai_dich(fake, dich, tid):
    fake["tra"] += [REVIEWING, None]
    jr.chuyen(URL, TOKEN, "AIP922-106", dich)
    assert json.loads(fake["req"][1].data) == {"transition": {"id": tid}}


def test_ten_transition_uu_tien_theo_thu_tu(fake):
    fake["tra"] += [{"transitions": [{"id": "5", "name": "Reject Issue", "to": {"name": "Reopened"}},
                                     {"id": "11", "name": "To Do", "to": {"name": "To Do"}}]}, None]
    jr.chuyen(URL, TOKEN, "AIP920-13", jr.DICH_FAIL)
    assert json.loads(fake["req"][1].data) == {"transition": {"id": "11"}}


def test_mat_ket_noi_thi_thu_lai(fake):
    rot = urllib.error.URLError(TimeoutError("10060"))
    fake["tra"] += [rot, rot, {"id": "1"}]
    jr.comment(URL, TOKEN, "AIP922-106", "x")
    assert len(fake["req"]) == 3


def test_mat_ket_noi_mai_thi_loi_sau_so_lan_thu(fake):
    fake["tra"] += [urllib.error.URLError(TimeoutError("10060"))] * jr.SO_LAN_THU
    with pytest.raises(jr.JiraLoi, match="khong ket noi duoc"):
        jr.dang_reviewing(URL, TOKEN, ["AIP920-13"])
    assert len(fake["req"]) == jr.SO_LAN_THU


def test_timeout_doc_phan_hoi_khong_gui_lai(fake):
    fake["tra"] += [TimeoutError("read"), {"id": "1"}]
    with pytest.raises(jr.JiraLoi):
        jr.comment(URL, TOKEN, "AIP920-13", "x")
    assert len(fake["req"]) == 1                 # POST co the da ghi -> gui lai la comment trung


def test_da_comment_theo_dong_dau(fake):
    fake["tra"].append({"comments": [{"body": "[Bot auto verify] FAIL tren build 1\nchi tiet"}]})
    assert jr.da_comment(URL, TOKEN, "AIP920-13", "[Bot auto verify] FAIL tren build 1")
    fake["tra"].append({"comments": [{"body": "khac"}]})
    assert not jr.da_comment(URL, TOKEN, "AIP920-13", "[Bot auto verify] FAIL tren build 1")
