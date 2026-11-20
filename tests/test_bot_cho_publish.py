"""Hang cho publish: bot khong dinh kem HTML, phien Claude Code publish roi bot thay link vao tin (11/11/2026)."""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path

import pytest

from rcr import bot_cho_publish as cp
from rcr import bot_cong_viec


def test_them_khong_trung_va_xong_ghi_link(tmp_path):
    f = tmp_path / "report.html"
    f.write_text("<title>x</title>", encoding="utf-8")
    a = cp.them(tmp_path, f, 11, 22, "AIP893 2.5.0")
    assert cp.them(tmp_path, f, 11, 22, "AIP893 2.5.0") == a          # bao ket qua goi lai -> khong them lan hai
    assert [m["id"] for m in cp.chua_publish(tmp_path)] == [a]
    cp.xong(tmp_path, a, "https://claude.ai/artifact/abc")
    assert cp.chua_publish(tmp_path) == []
    with pytest.raises(ValueError):
        cp.xong(tmp_path, a, "file:///tmp/report.html")               # chi nhan link artifact
    with pytest.raises(KeyError):
        cp.xong(tmp_path, "khong-co", "https://claude.ai/artifact/abc")


def test_tin_ket_qua_khong_noi_dinh_kem_ma_ghi_dang_publish(tmp_path):
    kq = {"trang_thai": "XONG", "tom_tat": "xong", "link": str(tmp_path / "r.html")}
    chu = bot_cong_viec.tin_ket_qua({"ma": "AIP893", "version": "2.5.0", "ten": "Slideshow", "package": "a.b"}, kq, tmp_path / "r.html")
    assert cp.CHO in chu and "đính kèm" not in chu
    assert cp.thay_link(chu, "https://claude.ai/artifact/abc").count("Report: https://claude.ai/artifact/abc") == 1


class _Embed:
    def __init__(self, title, description, color=None):
        self.title, self.description, self.color = title, description, color


class _Tin:
    def __init__(self, content, embeds):
        self.content, self.embeds, self.sua = content, embeds, None

    async def edit(self, content=None, embeds=None):
        self.sua = {"content": content, "embeds": embeds}


class _Kenh:
    def __init__(self, tin):
        self.tin = tin

    async def fetch_message(self, _id):
        return self.tin


class _Bot:
    def __init__(self, tin):
        self.kenh = _Kenh(tin)

    def get_channel(self, _id):
        return self.kenh


def test_vong_thay_link_vao_tin_va_canh_bao_mot_lan(tmp_path, monkeypatch):
    discord = pytest.importorskip("discord")
    monkeypatch.setattr(discord, "Embed", _Embed)
    f = tmp_path / "r.html"
    f.write_text("x", encoding="utf-8")
    tin = _Tin("AIP893", [_Embed("Kết quả", f"tóm tắt\n{cp.CHO}")])
    a = cp.them(tmp_path, f, 1, 2, "AIP893")
    cp.them(tmp_path, tmp_path / "cu.html", 1, 3, "AIP872")
    ds = cp.doc(tmp_path)
    ds[1]["luc"] = time.time() - cp.CANH_BAO_SAU - 5                   # report cho qua lau
    cp._ghi(tmp_path, ds)
    cp.xong(tmp_path, a, "https://claude.ai/artifact/abc")
    bao = []

    async def gui(chu):
        bao.append(chu)

    monkeypatch.setattr(cp, "_mo_lai_luc", 0.0)
    mo = []
    asyncio.run(cp.mot_vong(_Bot(tin), tmp_path, gui, mo_lai=lambda: mo.append(1) or True))
    asyncio.run(cp.mot_vong(_Bot(tin), tmp_path, gui, mo_lai=lambda: mo.append(1) or True))
    assert mo == [1]                                                     # mo lai phien publish mot lan (con cach)
    assert "tự mở lại" in bao[0]
    assert "Report: https://claude.ai/artifact/abc" in tin.sua["embeds"][0].description
    assert cp.CHO not in tin.sua["embeds"][0].description
    assert len(bao) == 1 and "cu.html" in bao[0]                         # canh bao dung mot lan
    assert all(m["da_sua"] for m in cp.doc(tmp_path) if m["url"])


def test_cli_ds_va_xong(tmp_path, capsys):
    f = tmp_path / "r.html"
    f.write_text("x", encoding="utf-8")
    a = cp.them(tmp_path, f, 1, 2, "AIP893")
    assert cp.main(["--out-dir", str(tmp_path), "ds"]) == 0
    assert json.loads(capsys.readouterr().out)[0]["id"] == a
    assert cp.main(["--out-dir", str(tmp_path), "xong", a, "https://claude.ai/artifact/abc"]) == 0
    assert cp.main(["--out-dir", str(tmp_path), "xong", a, "khong-phai-link"]) == 1


def test_khong_co_report_ket_thi_khong_mo_lai_phien(tmp_path, monkeypatch):
    monkeypatch.setattr(cp, "_mo_lai_luc", 0.0)
    cp.them(tmp_path, tmp_path / "moi.html", 1, 2, "AIP924")            # vua vao hang cho, chua qua han
    mo = []

    async def gui(_chu):
        raise AssertionError("khong duoc canh bao")

    asyncio.run(cp.mot_vong(None, tmp_path, gui, mo_lai=lambda: mo.append(1) or True))
    assert mo == []


def test_mo_lai_phien_bo_qua_khi_may_khong_cai_service(monkeypatch):
    class _Kq:
        returncode = 1
    goi = []
    monkeypatch.setattr(cp.subprocess, "run", lambda args, **_k: goi.append(args) or _Kq())
    assert cp.mo_lai_phien_publish() is False
    assert goi == [["systemctl", "--user", "cat", cp.SERVICE]]          # khong goi restart
