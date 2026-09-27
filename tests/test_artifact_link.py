"""Test luu/doc link artifact. Khong can device.

Diem phai gac:
  - chua publish lan nao -> {} , khong no
  - file hong / khong phai dict -> {} , vi link chi la tien nghi
  - url khong phai https -> bo, khong tra ve chuoi rac cho nguoi dung bam
  - ghi roi doc lai phai ra dung url + generated_at cua luot do
  - co --url ma thieu --generated-at -> CLI bao loi, khong ghi nua voi
"""

from __future__ import annotations

from rcr import artifact_link
from rcr.cli_artifact import main


def test_chua_publish_lan_nao(tmp_path):
    assert artifact_link.doc(tmp_path) == {}


def test_ghi_roi_doc_lai(tmp_path):
    artifact_link.ghi("https://claude.ai/artifact/abc", "2026-09-25T21:40:00+0700", tmp_path)
    assert artifact_link.doc(tmp_path) == {
        "url": "https://claude.ai/artifact/abc",
        "generated_at": "2026-09-25T21:40:00+0700",
    }


def test_file_hong_khong_lam_no(tmp_path):
    artifact_link.duong_dan(tmp_path).write_text("{khong phai json", encoding="utf-8")
    assert artifact_link.doc(tmp_path) == {}


def test_khong_phai_dict(tmp_path):
    artifact_link.duong_dan(tmp_path).write_text('["mot list"]', encoding="utf-8")
    assert artifact_link.doc(tmp_path) == {}


def test_url_khong_phai_https_thi_bo(tmp_path):
    artifact_link.ghi("file:///tmp/run.html", "2026-09-25T21:40:00+0700", tmp_path)
    assert artifact_link.doc(tmp_path) == {}


def test_cli_thieu_generated_at_thi_bao_loi(tmp_path, capsys):
    ma = main(["--url", "https://claude.ai/artifact/abc", "--out", str(tmp_path)])
    assert ma == 1
    assert "generated-at" in capsys.readouterr().err
    # Khong duoc ghi nua voi: file van phai trong.
    assert artifact_link.doc(tmp_path) == {}


def test_cli_khong_tham_so_thi_in_link_da_luu(tmp_path, capsys):
    artifact_link.ghi("https://claude.ai/artifact/abc", "moc-cu", tmp_path)
    assert main(["--out", str(tmp_path)]) == 0
    assert "https://claude.ai/artifact/abc" in capsys.readouterr().out
