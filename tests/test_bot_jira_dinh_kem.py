import base64
import json

from rcr import bot_cong_viec, bot_jira_dinh_kem as dk, bot_jira_rest as jr

PNG = b"\x89PNG\r\n\x1a\nfake"
JPG = b"\xff\xd8\xff\xe0fake"


def _uri(b: bytes, loai: str = "jpeg") -> str:
    return f"data:image/{loai};base64," + base64.b64encode(b).decode()


def _luot(out, ten, records, package="com.a.b"):
    out.mkdir(exist_ok=True)
    (out / f"run-{package}-S-{ten}.luot.json").write_text(json.dumps({"package": package, "records": records}))


def test_anh_tay_truoc_roi_cac_buoc_cuoi_co_anh(tmp_path):
    r = {"key": "rating#RATING-R01-02", "verdict": "FAIL",
         "anh_tay": [{"ten": "popup sai", "src": _uri(PNG, "png")}],
         "steps": [{"n": i, "k": "chup_man", "shot": _uri(JPG)} for i in range(1, 9)] + [{"n": 9, "k": "kill"}]}
    _luot(tmp_path, "1", [r])
    anh = dk.anh_cua_case(tmp_path, "com.a.b", "RATING-R01-02", toi_da=3)   # Claude tra TC ID khong co tab
    assert [t for t, _ in anh] == ["RATING-R01-02_popup_sai.png", "RATING-R01-02_buoc7_chup_man.jpg",
                                   "RATING-R01-02_buoc8_chup_man.jpg"]
    assert anh[0][1] == PNG and anh[1][1] == JPG


def test_uu_tien_record_fail_moi_nhat_va_dung_package(tmp_path):
    import os
    import time
    _luot(tmp_path, "cu", [{"key": "X-01", "verdict": "FAIL", "anh_tay": [{"ten": "cu", "src": _uri(JPG)}]}])
    _luot(tmp_path, "khac", [{"key": "X-01", "verdict": "FAIL", "anh_tay": [{"ten": "khac", "src": _uri(JPG)}]}],
          package="com.khac")
    _luot(tmp_path, "moi", [{"key": "X-01", "verdict": "PASS", "anh_tay": [{"ten": "pass", "src": _uri(JPG)}]}])
    t = time.time()
    os.utime(tmp_path / "run-com.a.b-S-cu.luot.json", (t - 100, t - 100))
    assert [n for n, _ in dk.anh_cua_case(tmp_path, "com.a.b", "X-01")] == ["X-01_cu.jpg"]


def test_case_khong_co_anh_hoac_khong_thay(tmp_path):
    _luot(tmp_path, "1", [{"key": "IAA-04-01", "verdict": "FAIL", "steps": [], "anh_tay": None}])
    assert dk.anh_cua_case(tmp_path, "com.a.b", "IAA-04-01") == []
    assert dk.anh_cua_case(tmp_path, "com.a.b", "KHONG-CO") == []


def test_dinh_kem_issues_dem_anh_va_loi(tmp_path, monkeypatch):
    _luot(tmp_path, "1", [{"key": "A-1", "verdict": "FAIL", "anh_tay": [{"ten": "x", "src": _uri(JPG)}]},
                          {"key": "A-2", "verdict": "FAIL"},
                          {"key": "A-3", "verdict": "FAIL", "anh_tay": [{"ten": "y", "src": _uri(JPG)}]}])
    goi = []

    def gia(url, token, key, files):
        if key == "P-3":
            raise jr.JiraLoi("HTTP 413")
        goi.append((key, [t for t, _ in files]))
    monkeypatch.setattr(jr, "dinh_kem", gia)
    issues = [{"case": "A-1", "key": "P-1"}, {"case": "A-2", "key": "P-2"}, {"case": "A-3", "key": "P-3"},
              {"case": "A-4", "key": ""}]
    gan = dk.dinh_kem_issues("https://j", "t", tmp_path, "com.a.b", issues)
    assert gan == {"P-1": 1, "P-2": 0, "P-3": -1} and goi == [("P-1", ["A-1_x.jpg"])]
    dong = bot_cong_viec.tom_tat_dinh_kem(gan)
    assert "1/3" in dong and "P-2" in dong and "Jira từ chối: P-3" in dong


def test_rest_dinh_kem_gui_multipart_kem_no_check(monkeypatch):
    bat = {}

    class R:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self): return b"[]"

    def mo(req, timeout):
        bat["req"] = req
        return R()
    monkeypatch.setattr(jr._MO, "open", mo)
    jr.dinh_kem("https://jira.x", "PAT", "AIP921-5", [("a b.png", PNG)])
    req = bat["req"]
    assert req.full_url == "https://jira.x/rest/api/2/issue/AIP921-5/attachments"
    assert req.get_header("X-atlassian-token") == "no-check"
    assert req.get_header("Content-type").startswith("multipart/form-data; boundary=")
    assert b'filename="a_b.png"' in req.data and PNG in req.data


def test_rest_dinh_kem_chan_key_la():
    import pytest
    with pytest.raises(jr.JiraLoi):
        jr.dinh_kem("https://jira.x", "PAT", "../x", [("a.png", PNG)])


def test_mac_dinh_chi_mot_anh_man_loi(tmp_path):
    shot = [{"n": i, "k": "chup_man", "shot": _uri(JPG)} for i in (1, 2, 3)]
    _luot(tmp_path, "1", [{"key": "A-1", "verdict": "FAIL", "steps": shot,
                           "anh_tay": [{"ten": "tien_dk", "src": _uri(JPG)}, {"ten": "loi", "src": _uri(PNG, "png")}]},
                          {"key": "A-2", "verdict": "FAIL", "steps": shot}])
    assert [t for t, _ in dk.anh_cua_case(tmp_path, "com.a.b", "A-1")] == ["A-1_loi.png"]
    assert [t for t, _ in dk.anh_cua_case(tmp_path, "com.a.b", "A-2")] == ["A-2_buoc3_chup_man.jpg"]
