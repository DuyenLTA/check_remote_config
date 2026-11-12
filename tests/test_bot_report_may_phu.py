"""Report cua luot o may phu -> hang cho publish cua bot chinh: kenh / bot gia, khong cham Discord that."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

import aiohttp
import discord
import pytest

from rcr import bot_cho_publish as cp, bot_may_phu as mp, bot_report_may_phu as rp


class _Kenh:
    """Kenh dieu phoi gia: ghi lai cac tin gui (giong Discord: rcr.json + file HTML)."""

    def __init__(self, gioi_han=10 * 1024 * 1024, loi=None):
        self.guild = SimpleNamespace(filesize_limit=gioi_han)
        self.tin, self.loi = [], loi

    async def send(self, chu, file=None, files=None):
        if self.loi:
            raise self.loi
        cac = [file] if file is not None else files
        self.tin.append(SimpleNamespace(content=chu, attachments=[
            SimpleNamespace(filename=f.filename, read=_doc(f.fp.read())) for f in cac]))


def _doc(raw):
    async def read():
        return raw
    return read


def _bot_phu(tmp_path, kenh):
    async def kenh_dp():
        return kenh
    return SimpleNamespace(la_phu=True, dieu_phoi=1, ten_may="laptop", out=tmp_path / "phu", _kenh_dieu_phoi=kenh_dp)


def _report(tmp_path, noi_dung=b"<html>AIP892</html>"):
    f = tmp_path / "phu" / "sdk-AIP892" / "report.html"
    f.parent.mkdir(parents=True)
    f.write_bytes(noi_dung)
    return f


def test_may_phu_gui_report_sang_bot_chinh_bot_chinh_xep_hang_va_vong_lap_canh_bao(tmp_path, monkeypatch):
    kenh = _Kenh()
    bot = _bot_phu(tmp_path, kenh)
    f = _report(tmp_path)
    asyncio.run(rp.them(bot, bot.out, f, 111, 222, "AIP892 1.0", "AIP892 1.0"))
    assert cp.doc(bot.out) == []                                  # khong xep hang cuc bo o may phu
    m = kenh.tin[0]
    assert m.content == "RCR report laptop" and [a.filename for a in m.attachments] == ["rcr.json", "report.html"]

    chinh = SimpleNamespace(out=tmp_path / "chinh")
    loai, d = asyncio.run(mp.doc(m))
    assert loai == rp.LOAI and d["kenh_id"] == 111 and d["msg_id"] == 222
    p = asyncio.run(rp.nhan_o_may_chinh(chinh, m, d))
    assert p.parent == chinh.out / rp.THU_MUC and p.read_bytes() == b"<html>AIP892</html>"
    asyncio.run(rp.nhan_o_may_chinh(chinh, m, d))                 # tin phat lai -> khong them lan hai
    cho = cp.chua_publish(chinh.out)
    assert len(cho) == 1 and cho[0]["kenh_id"] == 111 and cho[0]["msg_id"] == 222 and cho[0]["file"] == str(p)

    # vong_lap cua bot chinh canh bao sau 15 phut nhu luot chay o may chinh
    canh_bao = []

    async def bao(chu):
        canh_bao.append(chu)
    monkeypatch.setattr(cp.time, "time", lambda: cho[0]["luc"] + cp.CANH_BAO_SAU + 1)
    asyncio.run(cp.mot_vong(SimpleNamespace(), chinh.out, bao))
    assert len(canh_bao) == 1 and "AIP892 1.0" in canh_bao[0]


def test_ten_file_an_toan_khong_thoat_thu_muc(tmp_path):
    ten = rp.ten_an_toan("../lap top", 5, "../../etc/passwd", b"x")
    assert "/" not in ten and not ten.startswith(".") and ten.endswith(".html")
    m = SimpleNamespace(attachments=[SimpleNamespace(filename="rcr.json", read=_doc(b"{}")),
                                     SimpleNamespace(filename="x.html", read=_doc(b"<p>"))])
    p = asyncio.run(rp.nhan_o_may_chinh(SimpleNamespace(out=tmp_path), m,
                                        {"may": "../..", "msg_id": 5, "kenh_id": 1, "file": "..\\..\\a.html"}))
    assert p.resolve().parent == (tmp_path / rp.THU_MUC).resolve()


def test_report_qua_gioi_han_hoac_discord_tu_choi_thi_giu_hang_cho_may_phu(tmp_path):
    f = _report(tmp_path, b"x" * 200_000)
    kenh = _Kenh(gioi_han=100_000)
    bot = _bot_phu(tmp_path, kenh)
    asyncio.run(rp.them(bot, bot.out, f, 1, 2, "a"))
    assert kenh.tin == [] and [m["msg_id"] for m in cp.chua_publish(bot.out)] == [2]

    loi = discord.HTTPException(SimpleNamespace(status=413, reason="Payload Too Large"), "too large")
    bot2 = _bot_phu(tmp_path, _Kenh(loi=loi))
    asyncio.run(rp.them(bot2, bot2.out, f, 1, 3, "a"))
    assert [m["msg_id"] for m in cp.chua_publish(bot2.out)] == [2, 3]


def test_loi_mang_nem_ra_de_bot_gui_lai(tmp_path):
    bot = _bot_phu(tmp_path, _Kenh(loi=aiohttp.ClientConnectionError("mat mang")))
    f = _report(tmp_path)
    with pytest.raises(aiohttp.ClientError):
        asyncio.run(rp.them(bot, bot.out, f, 1, 2, "a"))
    assert cp.doc(bot.out) == []


def test_bot_chinh_giu_hang_cho_cuc_bo_nhu_cu(tmp_path):
    f = tmp_path / "r.html"
    f.write_text("<p>")
    bot = SimpleNamespace(la_phu=False, dieu_phoi=1, out=tmp_path)
    asyncio.run(rp.them(bot, tmp_path, f, 1, 2, "a"))
    assert [Path(m["file"]).name for m in cp.chua_publish(tmp_path)] == ["r.html"]


def test_doc_lay_dung_file_json_khi_co_hai_file():
    m = SimpleNamespace(content="RCR report laptop", attachments=[
        SimpleNamespace(filename="report.html", read=_doc(b"<html>")),
        SimpleNamespace(filename="rcr.json", read=_doc(json.dumps({"msg_id": 1}).encode()))])
    assert asyncio.run(mp.doc(m)) == ("report", {"msg_id": 1})
