"""Lenh slash /xoa-bai: xoa bai build cu trong Forum `qa-builds` (moi app moi version mot bai -> cang ngay cang nhieu).

Loc bai theo ma app, version (go `2.6.0` khop ca `2.6.0 (23)`) va/hoac so ngay khong hoat dong. Chi xoa bai do bot
tao, bo qua bai cua build con trong hang doi / dang chay. Xoa khong hoan tac duoc -> tin tra loi liet ke bai se xoa
kem nut xac nhan, bam moi xoa. Chi QA duoc duyet. Bot can quyen Manage Threads trong kenh Forum (thieu -> bao loi).
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import discord
from discord import app_commands

log = logging.getLogger("rcr-bot")
HIEN_TOI_DA = 30                   # so dong bai liet ke trong tin xac nhan
CHO_XAC_NHAN_GIAY = 300


def dang_ky(bot, goi_y_ma) -> None:
    """Gan /xoa-bai vao `bot.tree`; `goi_y_ma` la autocomplete ma app dung chung voi /check."""

    @bot.tree.command(name="xoa-bai", description="Xoá bài build cũ trong Forum qa-builds (theo app, version, số ngày)")
    @app_commands.describe(ma_app="Mã app, vd AIP893 — bỏ trống thì xoá mọi app (phải có cu_hon_ngay)",
                           version="Chỉ xoá bài của version này, vd 2.6.0 hoặc 2.6.0 (23)",
                           cu_hon_ngay="Chỉ xoá bài không có tin mới quá số ngày này")
    @app_commands.autocomplete(ma_app=goi_y_ma)
    async def xoa_bai(it: discord.Interaction, ma_app: str | None = None, version: str | None = None,
                      cu_hon_ngay: app_commands.Range[int, 0, 3650] | None = None):
        await lenh_xoa_bai(bot, it, ma_app, version, cu_hon_ngay)


def _ma_ver(ten: str) -> tuple[str, str]:
    """'AIP893 · 2.6.0 (23) · AI Photo' -> ('AIP893', '2.6.0 (23)')."""
    phan = [p.strip() for p in (ten or "").split("·")]
    return phan[0].upper(), (phan[1] if len(phan) > 1 else "")


def _lan_cuoi(t) -> datetime:
    return discord.utils.snowflake_time(getattr(t, "last_message_id", None) or t.id)


def bai_dang_dung(bot) -> set[int]:
    """Id bai cua build con trong hang doi / dang chay (id tin goc dau bai == id bai)."""
    ids = set()
    for j in bot.q.jobs:
        kid = j.get("kenh_id") or (bot.q.tin_cua(j["msg_id"]) or {}).get("kenh_id")
        ids.update(int(x) for x in (kid, j.get("msg_id")) if x)
    return ids


def chon_bai(bai: list, chu_bot: int, ma: str, version: str, cu_hon_ngay: int | None, dang_dung: set[int],
             bay_gio: datetime | None = None) -> list:
    """Bai bot tao khop dieu kien, tru bai dang dung; cu nhat truoc."""
    bay_gio = bay_gio or datetime.now(timezone.utc)
    ra = []
    for t in bai:
        m, v = _ma_ver(t.name)
        if getattr(t, "owner_id", None) != chu_bot or t.id in dang_dung:
            continue
        if ma and m != ma:
            continue
        if version and not (v == version or v.startswith(version + " ")):
            continue
        if cu_hon_ngay is not None and bay_gio - _lan_cuoi(t) < timedelta(days=cu_hon_ngay):
            continue
        ra.append(t)
    return sorted(ra, key=_lan_cuoi)


async def tat_ca_bai(forum) -> list:
    """Bai dang mo + bai da archive cua kenh Forum (khong trung)."""
    bai = {t.id: t for t in forum.threads}
    async for t in forum.archived_threads(limit=None):
        bai.setdefault(t.id, t)
    return list(bai.values())


def tin_xac_nhan(bai: list, bo_qua: int) -> str:
    dong = [f"🗑️ Sẽ xoá **{len(bai)}** bài (không hoàn tác được):"]
    for t in bai[:HIEN_TOI_DA]:
        dong.append(f"• {t.name} — tin cuối {_lan_cuoi(t).astimezone().strftime('%d/%m/%Y')}")
    if len(bai) > HIEN_TOI_DA:
        dong.append(f"… và {len(bai) - HIEN_TOI_DA} bài nữa")
    if bo_qua:
        dong.append(f"Bỏ qua {bo_qua} bài của build còn trong hàng đợi / đang chạy.")
    return "\n".join(dong)[:1900]


async def xoa(bai: list) -> tuple[int, list[str]]:
    """Xoa tung bai; tra (so da xoa, loi). Thieu quyen thi dung som, khong lap lai 403 cho moi bai."""
    da, loi = 0, []
    for t in bai:
        try:
            await t.delete()
            da += 1
        except discord.Forbidden:
            loi.append("Bot thiếu quyền **Manage Threads** trong kênh Forum — nhờ admin cấp quyền rồi gõ lại.")
            break
        except discord.HTTPException as exc:
            loi.append(f"{t.name}: {exc}")
    return da, loi


async def lenh_xoa_bai(bot, it: discord.Interaction, ma_app: str | None, version: str | None,
                       cu_hon_ngay: int | None) -> None:
    if not bot._duoc_duyet(it.user):
        await it.response.send_message("Chỉ QA được duyệt mới dùng được /xoa-bai.", ephemeral=True)
        return
    if not getattr(bot, "kenh_forum", 0):
        await it.response.send_message("Bot chưa bật Forum (DISCORD_FORUM_CHANNEL_ID trống).", ephemeral=True)
        return
    ma, ver = (ma_app or "").strip().upper(), (version or "").strip()
    if not ma and cu_hon_ngay is None:
        await it.response.send_message("Gõ `ma_app` hoặc `cu_hon_ngay` — không xoá cả kênh một lần.", ephemeral=True)
        return
    await it.response.defer(ephemeral=True, thinking=True)
    try:
        forum = bot.get_channel(bot.kenh_forum) or await bot.fetch_channel(bot.kenh_forum)
        tat_ca = await tat_ca_bai(forum)
    except Exception as exc:              # noqa: BLE001 - loi Discord tra ve cho nguoi go
        log.exception("/xoa-bai: khong doc duoc Forum")
        await it.followup.send(f"⛔ Không đọc được kênh Forum: {exc}", ephemeral=True)
        return
    dang_dung = bai_dang_dung(bot)
    bai = chon_bai(tat_ca, bot.user.id, ma, ver, cu_hon_ngay, set())
    chon = [t for t in bai if t.id not in dang_dung]
    if not chon:
        await it.followup.send("Không có bài nào khớp để xoá.", ephemeral=True)
        return
    view = discord.ui.View(timeout=CHO_XAC_NHAN_GIAY)
    nut = discord.ui.Button(label=f"Xoá {len(chon)} bài", style=discord.ButtonStyle.danger)

    async def bam(bam_it: discord.Interaction):
        if bam_it.user.id != it.user.id:
            await bam_it.response.send_message("Chỉ người gõ lệnh mới xác nhận được.", ephemeral=True)
            return
        await bam_it.response.edit_message(content=f"⏳ Đang xoá {len(chon)} bài…", view=None)
        da, loi = await xoa(chon)
        log.info("/xoa-bai: %s xoa %d/%d bai", it.user, da, len(chon))
        chu = f"✅ Đã xoá {da}/{len(chon)} bài." + ("\n" + "\n".join(loi[:10]) if loi else "")
        await bam_it.edit_original_response(content=chu[:2000])

    nut.callback = bam
    view.add_item(nut)
    await it.followup.send(tin_xac_nhan(chon, len(bai) - len(chon)), view=view, ephemeral=True)
