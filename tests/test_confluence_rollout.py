"""Tra link Rollout + Checklist cua app tren Confluence (lenh /rollout) - phan thuan, khong goi mang."""

from rcr import confluence_rollout as c

SHEET_A = "https://docs.google.com/spreadsheets/d/AAA111/edit?gid=0#gid=0"
SHEET_B = "https://docs.google.com/spreadsheets/d/BBB222/edit?gid=5#gid=5"
SHEET_TEST = "https://docs.google.com/spreadsheets/d/TEST999/edit?gid=0#gid=0"


def _trang(title):
    return {"title": title, "_links": {"webui": "/x"}}


def test_chon_trang_rollout_dung_ma_app():
    ket_qua = [_trang("AIP9310 - Rollout"), _trang("AIP931 Ver 1.0.0"), _trang("AIP931 - Rollout")]
    assert c.chon_trang_rollout(ket_qua, "AIP931")["title"] == "AIP931 - Rollout"


def test_chon_trang_rollout_ten_dinh_lien_va_ngoac():
    assert c.chon_trang_rollout([_trang("AIP885-Rollout")], "AIP885")
    assert c.chon_trang_rollout([_trang("[AAP871] Rollout - AI Learn")], "AAP871")
    assert c.chon_trang_rollout([_trang("AIP959 - Rollout History")], "AIP959")
    assert c.chon_trang_rollout([_trang("AIP922: Rollout History")], "AIP922")
    assert c.chon_trang_rollout([_trang("AIP885 Ver 2.0")], "AIP885") is None


def test_link_checklist_bo_checklist_test_va_link_khong_nhan():
    body = (f'<p>Ads Script: <a href="{SHEET_B}">x</a></p>'
            f'<p>Checklist: <a href="{SHEET_A}">x</a></p>'
            f'<p>Checklist test <a href="{SHEET_TEST}">x</a></p>')
    assert c.link_checklist(body) == [SHEET_A]


def test_link_checklist_nhan_bi_tach_the():
    body = f'<p>Ch<span>ecklist</span></p><p><a href="{SHEET_A}">x</a></p>'
    assert c.link_checklist(body) == [SHEET_A]


def test_chon_checklist_bo_file_cua_app_khac():
    ten = {"AAA111": "AIP918 - Linguza - Checklist", "BBB222": "AIP924 - LingoSpeak - Checklist"}
    ung_vien = [(SHEET_A, {"trang": "v1"}), (SHEET_B, {"trang": "v2"})]
    chon, bo = c.chon_checklist(ung_vien, "AIP924", doc_ten=lambda l: ten[c.sheet_id(l)])
    assert chon["url"] == SHEET_B and chon["trang"] == "v2"
    assert bo == ["AIP918 - Linguza - Checklist"]


def test_chon_checklist_khong_doc_duoc_ten_thi_giu_du_phong():
    chon, bo = c.chon_checklist([(SHEET_A, {"trang": "v1"})], "AIP893", doc_ten=lambda l: None)
    assert chon["url"] == SHEET_A and chon["ten"] is None and bo == []


def test_chon_checklist_chi_co_file_app_khac_thi_khong_chon():
    chon, bo = c.chon_checklist([(SHEET_A, {"trang": "v1"})], "AIP924", doc_ten=lambda l: "AIP918 - Checklist")
    assert chon is None and bo == ["AIP918 - Checklist"]


def test_dung_lai_cau_hinh_trong_bashrc(monkeypatch, tmp_path):
    (tmp_path / ".bashrc").write_text("export CONFLUENCE_BASE_URL=https://conf.vn/\nexport CONFLUENCE_TOKEN='abc'\n",
                                      encoding="utf-8")
    monkeypatch.setattr(c, "env", lambda ten: "")
    monkeypatch.setattr(c.Path, "home", lambda: tmp_path)
    assert c._cau_hinh() == ("https://conf.vn", "abc")


def test_thieu_cau_hinh_bao_loi(monkeypatch, tmp_path):
    monkeypatch.setattr(c, "env", lambda ten: "")
    monkeypatch.setattr(c.Path, "home", lambda: tmp_path)
    try:
        c.tim("AIP924")
    except c.ConfluenceLoi as exc:
        assert "CONFLUENCE_TOKEN" in str(exc)
    else:
        raise AssertionError("phai bao thieu cau hinh")


def test_tin_tra_loi_du_hai_link():
    kq = {"ma": "AIP918", "app": "AIP918", "rollout": {"title": "AIP918 - Rollout", "url": "https://r"},
          "checklist": {"url": SHEET_A, "ten": "AIP918 - Checklist", "trang": "Ver 2.1.0", "trang_url": "https://v"},
          "bo": []}
    tin = c.tin_tra_loi(kq)
    assert "[AIP918 - Rollout](https://r)" in tin and SHEET_A in tin and "AIP918 - Checklist" in tin
