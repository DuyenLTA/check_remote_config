"""Moi job MOT tin goc o kenh QA: moi buoc (cai, chay, dung, ket qua, bug, Jira) SUA tin do, khong gui tin moi.

User chot 09/11/2026: "co action bam gi hay thay doi gi thi doi luon status cua 1 tin goc thoi, dung tra ra nhieu
tin" - truoc day moi luot ra 4-6 tin (tin da cai, tin ket qua, tin menu bug, tin Jira, tin ephemeral "Dang dung
luot", "Report da publish"...). Thay luat cu "cai duoc build thi gui tin moi (reply)".

Tin goc = `content` (dong dau build + dong trang thai, thay moi buoc) + cac embed dat ten theo phan (ket qua, bug,
tin cho dev) - embed sua theo TEN nen sua phan nay khong xoa phan kia. Content toi da 2000 ky tu, embed 4096.
"""
from __future__ import annotations

import discord

KET_QUA = "Kết quả"
BUG = "Bug cần review"
TIN_DEV = "Tin cho dev"
MAX_EMBED = 4096
MAX_CONTENT = 2000


def embed(ten: str, noi_dung: str, mau: int = 0x5865F2) -> discord.Embed:
    chu = noi_dung if len(noi_dung) <= MAX_EMBED else noi_dung[:MAX_EMBED - 1] + "…"
    return discord.Embed(title=ten, description=chu, color=mau)


def thay(tin, moi: discord.Embed) -> list[discord.Embed]:
    """Danh sach embed cua `tin` (discord.Message), embed cung ten voi `moi` duoc thay (khong co thi them cuoi)."""
    ra, thay_xong = [], False
    for e in getattr(tin, "embeds", None) or ():
        if e.title == moi.title:
            ra.append(moi)
            thay_xong = True
        else:
            ra.append(e)
    return ra if thay_xong else [*ra, moi]


def noi(content: str, dong: str) -> str:
    """Them mot dong trang thai vao cuoi content (cat ve gioi han cua Discord)."""
    chu = f"{content}\n{dong}" if content else dong
    return chu if len(chu) <= MAX_CONTENT else chu[:MAX_CONTENT - 1] + "…"


def view_gop(*views: discord.ui.View | None) -> discord.ui.View:
    """Gop nut/menu cua nhieu view vao mot view (menu bug + nut Verify cung nam tren tin goc)."""
    v = discord.ui.View(timeout=None)
    for x in views:
        for item in (x.children if x else ()):
            v.add_item(item)
    return v
