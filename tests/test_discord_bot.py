"""Phan cua bot Discord khong can ket noi: nut, quyen bam."""

from __future__ import annotations

from types import SimpleNamespace

from rcr import discord_bot as d


def test_nut_mang_hanh_dong_va_msg_id():
    v = d._nut(("check", "Check", d.XANH), ("bo", "Bỏ qua", d.XAM), msg_id=42)
    assert [b.custom_id for b in v.children] == ["rcr:check:42", "rcr:bo:42"]
    assert v.timeout is None                      # bot khoi dong lai nut van bam duoc


def test_chi_nguoi_duoc_duyet_hoac_co_role_moi_bam_duoc():
    bot = object.__new__(d.BuildBot)
    bot.duyet, bot.role = {1476079991161880668}, 0
    assert bot._duoc_duyet(SimpleNamespace(id=1476079991161880668, roles=[]))
    assert not bot._duoc_duyet(SimpleNamespace(id=7, roles=[]))
    bot.role = 99
    assert bot._duoc_duyet(SimpleNamespace(id=7, roles=[SimpleNamespace(id=99)]))


def test_tin_chuyen_tiep_lay_chu_trong_snapshot():
    fwd = SimpleNamespace(content="", message_snapshots=[
        SimpleNamespace(content="Bản build AIP920 v1.6.0 (7) đã được hoàn thiện.\napply next-gen")])
    assert "AIP920 v1.6.0 (7)" in d.noi_dung(fwd)
    assert d.noi_dung(SimpleNamespace(content="abc", message_snapshots=[])) == "abc"
