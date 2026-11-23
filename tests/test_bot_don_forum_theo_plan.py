"""Don Forum qa-builds theo plan tuan: app co trang thai Released -> xoa bai version <= version da release."""

from __future__ import annotations

import asyncio
from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock

import openpyxl

from rcr import bot_don_forum_theo_plan as d

BOT = 42
TIEU_DE = ["STT", "Loại dự án", "OS", "Tên dự án", "App version", "Detail", "Ưu tiên", "PIC", "Trạng thái"]


def _plan(tmp_path, tabs: dict) -> str:
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for ten, dong in tabs.items():
        ws = wb.create_sheet(ten)
        for r in dong:
            ws.append(r)
    f = tmp_path / "plan.xlsx"
    wb.save(f)
    return str(f)


def _dong(ma, ver, tt):
    return [1, "VSL - Inhouse", "Android", ma, ver, "- Apply IAA", 1, "Duyên", tt]


def _bai(tid, ten, owner=BOT):
    return SimpleNamespace(id=tid, name=ten, owner_id=owner, last_message_id=tid, delete=AsyncMock())


def test_doc_released_lay_version_cao_nhat_o_tab_moi_nhat(tmp_path):
    f = _plan(tmp_path, {
        "0911-13112026": [TIEU_DE, _dong("AIP919", "2.0.0", "Released")],          # tab cu: khong doc
        "1611-20112026": [
            TIEU_DE,
            _dong("AIP944", "1.4.0", "Released"), _dong("AIP944", "1.5.0", "Released"),
            _dong("AIP919", "2.1.0", "Testing"), _dong("ADA895", "3.2.0", "Fixing"),
            _dong("AIP506", None, "Released"),                                        # khong ghi version: bo
            _dong("AIP893 (từ 2.0.0)", "2.6.0", " released "),
            # bang cong viec theo ngay ben duoi: khong co cot Trang thai, o cung vi tri ghi "test ... rls"
            ["STT", "Loại dự án", "OS", "Tên dự án", "App version", "Detail", "T4", "T5", "T6"],
            _dong("AIP933", "2.3.0", "Released"),
        ],
    })
    assert d.da_release(f, date(2026, 11, 23)) == {"AIP944": (1, 5, 0), "AIP893": (2, 6, 0)}
    assert d.da_release(f, date(2026, 11, 10)) == {"AIP919": (2, 0, 0)}
    assert d.da_release(f, date(2026, 11, 1)) == {}                                  # chua co tab nao bat dau


def test_chi_xoa_bai_bot_tao_version_khong_moi_hon_ban_release():
    cu, dung, moi = _bai(1, "AIP882 · 4.3.0 (40)"), _bai(2, "AIP882 · 4.4.0 (41) · AI-Video"), _bai(3, "AIP882 · 4.5.0 (42)")
    khac, nguoi, chay = _bai(4, "AIP919 · 2.1.0 (18)"), _bai(5, "AIP882 · 4.4.0 (41)", owner=7), _bai(6, "AIP882 · 4.4.0 (41)")
    la = _bai(7, "AIP882 · hỏi đáp")
    forum = SimpleNamespace(threads=[cu, dung, moi, khac, nguoi, chay, la], archived_threads=lambda limit=None: _rong())
    bot = SimpleNamespace(kenh_forum=99, get_channel=lambda i: forum, user=SimpleNamespace(id=BOT),
                          q=SimpleNamespace(jobs=[{"msg_id": 6}], tin_cua=lambda m: None))
    assert asyncio.run(d.don(bot, {"AIP882": (4, 4, 0)})) == (2, 2, [])
    for t in (cu, dung):
        t.delete.assert_awaited_once()
    for t in (moi, khac, nguoi, chay, la):
        t.delete.assert_not_awaited()


async def _rong():
    for t in ():
        yield t
