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
        if mau_re == r"^OK$":
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
