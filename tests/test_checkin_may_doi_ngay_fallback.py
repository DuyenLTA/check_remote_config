"""checkin_may.sang_ngay_mai: Android 17 khong co chu cong tac gio tu dong -> tat bang settings roi chon ngay."""

import asyncio

from rcr import checkin_may


class MayGia:
    def __init__(self):
        self.auto = "1"
        self.ngay = "2026-11-17"
        self.lenh = []

    async def shell(self, serial, *args):
        self.lenh.append(args)
        if args[:3] == ("settings", "get", "global"):
            return self.auto + "\n", "", 0
        if args[:3] == ("settings", "put", "global"):
            self.auto = args[4]
        if args[:2] == ("date", "+%Y-%m-%d"):
            return self.ngay + "\n", "", 0
        return "", "", 0


def test_khong_thay_cong_tac_thi_tat_bang_settings(monkeypatch):
    may = MayGia()
    da_bam = []

    async def bam(client, serial, mau_re, desc=False):
        da_bam.append(mau_re)
        if mau_re == checkin_may.TU_DONG_RE.pattern:
            return False                                  # man Date & time Android 17: khong co chu cong tac cu
        if mau_re == checkin_may.NUT_XONG_RE:
            may.ngay = "2026-11-18"
        return True

    async def nodes(client, serial):
        return []

    async def ngu(*_):
        return None

    monkeypatch.setattr(checkin_may, "_bam_chu", bam)
    monkeypatch.setattr(checkin_may, "_nodes_all", nodes)
    monkeypatch.setattr(checkin_may.asyncio, "sleep", ngu)
    kq = asyncio.run(checkin_may.sang_ngay_mai(may, "s"))
    assert kq["ok"] and kq["sau"] == "2026-11-18"
    assert ("settings", "put", "global", "auto_time", "0") in may.lenh


def test_lich_samsung_chon_ngay_theo_content_desc_va_bam_done(monkeypatch):
    """Samsung One UI (A13 17/11/2026): dong 'Set date', o ngay chi co content-desc, nut 'Done'."""
    import datetime
    import re
    may = MayGia()
    da_bam = []

    async def bam(client, serial, mau_re, desc=False):
        da_bam.append((mau_re, desc))
        if mau_re == checkin_may.TU_DONG_RE.pattern:
            return True
        if mau_re == checkin_may.NGAY_RE:
            return re.search(mau_re, "Set date") is not None
        if not desc and re.fullmatch(r"\^\d+\$", mau_re):
            return False                                  # lich Samsung: o ngay khong co chu so
        if desc and re.search(mau_re, "Wednesday, 18 November 2026"):
            return True
        if mau_re == checkin_may.NUT_XONG_RE and re.search(mau_re, "Done"):
            may.ngay = "2026-11-18"
            return True
        return False

    async def nodes(client, serial):
        return []

    async def ngu(*_):
        return None

    monkeypatch.setattr(checkin_may, "_bam_chu", bam)
    monkeypatch.setattr(checkin_may, "_nodes_all", nodes)
    monkeypatch.setattr(checkin_may.asyncio, "sleep", ngu)
    kq = asyncio.run(checkin_may.sang_ngay_mai(may, "s"))
    assert kq["ok"] and kq["sau"] == "2026-11-18"
    assert checkin_may.mo_ta_ngay(datetime.date(2026, 11, 18)) == r"\b18 November 2026$"
