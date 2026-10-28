"""Tab "Check ID ads" nhung trang audit vao report: markup, escape srcdoc, ban sao khi dung lai, bot dinh kem 1 file."""

from __future__ import annotations

import asyncio
import html
import os
import time
import re
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest

from rcr import audit_tom_tat as at, discord_bot, report_html, report_tab_audit as tab, sdk_nextgen_report

FIX = Path(__file__).parent / "fixtures" / "audit-artifact-aisong.html"
PKG = "aisong.generator.creatsong.music"


@pytest.fixture
def out(tmp_path, monkeypatch):
    d = tmp_path / "out"
    d.mkdir()
    (d / f"{PKG}-artifact.html").write_text(FIX.read_text("utf-8"), "utf-8")
    monkeypatch.setattr(at, "thu_muc_out", lambda: d)
    return d


def _srcdoc(page: str) -> str:
    m = re.search(r'srcdoc="([^"]*)"', page)
    assert m, "khong co srcdoc"
    return html.unescape(m.group(1))


def _nextgen(audit):
    return sdk_nextgen_report.render({"meta": {"package": PKG, "muc": [], "audit": audit}, "ket_qua": []})


def _tc(audit):
    return report_html.build({"title": "T", "eyebrow": "E", "spec": {}, "cases": [], "audit": audit})


@pytest.mark.parametrize("render,nhan", [(_nextgen, "Checklist"), (_tc, "Bộ TC")])
def test_hai_tab_co_audit_nhung_day_du(out, render, nhan):
    page = render(at.tim(PKG, out=out))
    assert page.count('role="tab"') == 2 and f">{nhan}</button>" in page and ">Check ID ads</button>" in page
    assert 'aria-selected="true"' in page and 'role="tablist"' in page and 'id="rt-p2"' in page
    assert 'sandbox="allow-scripts"' in page and "allow-same-origin" not in page
    assert _srcdoc(page) == FIX.read_text("utf-8")        # nguyen van, escape/unescape khop
    assert "54/54" in page                                  # khoi tom tat van thay o tab 1


@pytest.mark.parametrize("render", [_nextgen, _tc])
def test_khong_audit_van_co_tab_bao_chua_check(out, render):
    page = render(None)
    assert page.count('role="tab"') == 2 and "<iframe" not in page
    assert "Chưa check ID ads cho build này" in page


def test_srcdoc_escape_dau_nhay_va_and(out):
    f = out / f"{PKG}-artifact.html"
    f.write_text(FIX.read_text("utf-8") + '<p title="x" data-a=\'1\'>a & b "</iframe><script>1</script></p>', "utf-8")
    page = _tc(at.tim(PKG, out=out))
    attr = re.search(r'srcdoc="([^"]*)"', page).group(1)
    assert "</iframe>" not in attr and "<" not in attr and '"' not in attr
    assert "a & b" in _srcdoc(page)


def test_khong_nhung_file_ngoai_thu_muc_audit(out, tmp_path):
    x = tmp_path / "bi-mat.html"
    x.write_text("SECRET", "utf-8")
    tt = {**at.tim(PKG, out=out), "trang": str(x)}
    page = _tc(tt)
    assert "SECRET" not in page and "<iframe" not in page and "54/54" in page


def test_qua_lon_thi_chi_giu_tom_tat(out, monkeypatch):
    monkeypatch.setattr(tab, "MAX_BAO", 1000)
    page = _nextgen(at.tim(PKG, out=out))
    assert "<iframe" not in page and "quá lớn" in page and "54/54" in page


def test_ban_sao_giu_noi_dung_khi_dung_lai_report(out, tmp_path):
    from rcr import cli_sdk_check as cli
    d = tmp_path / f"sdk-{PKG}-261028-101500"
    d.mkdir()
    meta = lambda: {"meta": {"package": PKG, "muc": []}, "ket_qua": []}   # noqa: E731
    cli._xuat(d, meta())
    assert (d / tab.BAN_SAO).read_text("utf-8") == FIX.read_text("utf-8")
    # audit goc bi ghi de bang noi dung khac (build khac) va roi mat han -> report van la ban da luu
    (out / f"{PKG}-artifact.html").write_text(FIX.read_text("utf-8").replace("54", "55"), "utf-8")
    cli._xuat(d, meta())
    assert _srcdoc((d / "report.html").read_text("utf-8")) == FIX.read_text("utf-8")
    (out / f"{PKG}-artifact.html").unlink()
    cli._xuat(d, meta())
    assert _srcdoc((d / "report.html").read_text("utf-8")) == FIX.read_text("utf-8")


def test_bot_chi_dinh_kem_mot_file_report(out, tmp_path, monkeypatch):
    rp = tmp_path / "out" / "report.html"
    rp.write_text("<html>r</html>", "utf-8")
    sent = {}

    class Qa:
        async def edit(self, **kw): pass
        async def reply(self, text, files=None, view=None, **kw): sent.update(text=text, files=files)

    async def _tin_qa(_id): return Qa()

    bot = object.__new__(discord_bot.BuildBot)
    bot._tin_qa = _tin_qa
    bot.q = SimpleNamespace(tin_cua=lambda _i: None, nho_tin=lambda _c: None)
    monkeypatch.setattr(discord_bot.bot_cong_viec, "cai", lambda *a: {})
    monkeypatch.setattr(discord_bot.bot_chay_claude, "chay",
                        lambda *a: {"trang_thai": "xong", "link": str(rp)})
    monkeypatch.setattr(discord_bot, "OUT", rp.parent)
    job = {"msg_id": 1, "ma": "AIP", "ten": "Ai Song", "package": PKG, "version": "1", "loai_ban": "release"}
    f = out / f"{PKG}-artifact.html"
    os.utime(f, (time.time() + 60, time.time() + 60))   # audit ghi trong luot bot
    asyncio.run(bot._chay(job, "S1", "May"))
    assert [Path(x.fp.name).name for x in sent["files"]] == ["report.html"]
    assert "54/54 khớp" in sent["text"]
