"""Parser trang audit ID ads + chon trang theo luot + dong tin bot + khoi report."""

from __future__ import annotations

import os
import time
from datetime import date
from pathlib import Path

import pytest

from rcr import audit_tom_tat as at, report_html, sdk_nextgen_report

FIX = Path(__file__).parent / "fixtures" / "audit-artifact-aisong.html"
PKG = "aisong.generator.creatsong.music"


@pytest.fixture
def out(tmp_path):
    d = tmp_path / "out"
    d.mkdir()
    (d / f"{PKG}-artifact.html").write_text(FIX.read_text("utf-8"), "utf-8")
    return d


def test_doc_trang_that():
    tt = at.doc(FIX.read_text("utf-8"))
    assert (tt["khop"], tt["tong"], tt["lech"], tt["ngoai_sheet"]) == (54, 54, 0, 12)
    assert tt["luc"] == "2026-10-28T04:39:45+00:00"
    assert "RemoteConfigRepository" in tt["canh_bao"] and "<" not in tt["canh_bao"]


@pytest.mark.parametrize("txt", ["", "<html>khong co gi</html>", '<div class="bigfrac"><span class="n">x</span>'])
def test_doc_hong_tra_none(txt):
    assert at.doc(txt) is None


def test_tim_theo_mtime(out):
    f = out / f"{PKG}-artifact.html"
    assert at.tim(PKG, tu_luc=time.time() - 60, out=out)["khop"] == 54
    os.utime(f, (time.time() - 3600, time.time() - 3600))      # audit cu, truoc luot bot
    assert at.tim(PKG, tu_luc=time.time() - 60, out=out) is None
    assert at.tim(PKG, out=out)["trang"] == str(f.resolve())


def test_tim_theo_ngay_audit(out):
    assert at.tim(PKG, ngay=date(2026, 10, 28), out=out) is not None
    assert at.tim(PKG, ngay=date(2026, 10, 29), out=out) is None


@pytest.mark.parametrize("pkg", ["../x", "a/b", "", "a b", r"..\x"])
def test_package_ngoai_out_bi_chan(out, pkg):
    (out.parent / "x-artifact.html").write_text(FIX.read_text("utf-8"), "utf-8")
    assert at.trang_audit(pkg, out) is None


def test_tim_khong_co_trang(out):
    assert at.tim("com.khong.co", out=out) is None


def test_dong_tin(out):
    tt = at.tim(PKG, out=out)
    d = at.dong_tin(tt)
    assert "54/54 khớp · 0 lệch · 12 ID ngoài sheet" in d and "RemoteConfigRepository" in d
    assert "ID lệch" not in d
    assert "ID lệch" in at.dong_tin({**tt, "lech": 3})
    assert at.dong_tin(None) == at.CHUA_CHECK


def test_khoi_html_co_va_khong_audit(out):
    co = at.khoi_html(at.tim(PKG, out=out))
    assert "54/54" in co and "ID ngoài sheet" in co and PKG in co
    assert "chưa check ID ads cho build này" in at.khoi_html(None)


def test_report_tc_co_khoi_audit(out):
    data = {"title": "T", "eyebrow": "E", "spec": {}, "cases": []}
    assert "chưa check ID ads cho build này" in report_html.build(data)
    assert "54/54" in report_html.build({**data, "audit": at.tim(PKG, out=out)})


def test_report_nextgen_co_va_khong_audit(out):
    data = {"meta": {"package": PKG, "muc": []}, "ket_qua": []}
    assert "chưa check ID ads cho build này" in sdk_nextgen_report.render(data)
    data["meta"]["audit"] = at.tim(PKG, out=out)
    r = sdk_nextgen_report.render(data)
    assert "54/54" in r and r.index("Check ID ads") < r.index('class="cards"')


def test_xuat_sdk_check_giu_audit_khi_cham_lai(out, tmp_path, monkeypatch):
    """Dung lai report (--cham-tay/--cham-lai) van giu khoi audit da luu du trang audit sau do mat."""
    from rcr import cli_sdk_check as cli, sdk_nextgen_cham
    monkeypatch.setenv("AD_AUDIT_REPO", str(out.parents[0]))
    monkeypatch.setattr(at, "thu_muc_out", lambda: out)
    d = tmp_path / f"sdk-{PKG}-261028-101500"
    d.mkdir()
    data = {"meta": {"package": PKG, "muc": []}, "ket_qua": []}
    assert cli._ngay_chay(d) == date(2026, 10, 28)
    r = cli._xuat(d, data)
    assert "54/54" in Path(r["report"]).read_text("utf-8")
    (out / f"{PKG}-artifact.html").unlink()
    cli._xuat(d, {"meta": {"package": PKG, "muc": []}, "ket_qua": []})
    assert "54/54" in (d / "report.html").read_text("utf-8")
    assert sdk_nextgen_cham.doc(d)["meta"]["audit"]["khop"] == 54
