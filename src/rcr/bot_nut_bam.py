"""Xu ly nut bam / menu cua bot chinh: Check (xep hang), Bo qua, Huy, Dung, Verify, tick bug + Log Jira.

Goi tu `BuildBot.on_interaction` (bot chinh; may phu bo qua nut bam). custom_id `rcr:<hanh_dong>:<msg_id>`
(bot_giao_dien). Chi QA duoc duyet (DISCORD_DUYET_USER_IDS / role) moi bam duoc.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import discord

from . import bot_cong_viec, bot_dung_luot, bot_job_verify, bot_kenh_project, bot_log_jira, bot_verify_jira
from . import build_ma_app
from .bot_giao_dien import NUT_HOI, NUT_HUY, XAM, nut, view_bug

log = logging.getLogger("rcr-bot")


async def xu_ly(bot, it: discord.Interaction) -> None:
    cid = (it.data or {}).get("custom_id", "")
    if not cid.startswith("rcr:"):
        return
    _, hanh_dong, msg_id = cid.split(":")
    if not bot._duoc_duyet(it.user):
        await it.response.send_message("Chỉ QA được duyệt mới bấm được.", ephemeral=True)
        return
    c = bot.q.tin_cua(int(msg_id))
    if c is None:
        await it.response.send_message("Bot không còn nhớ build này.", ephemeral=True)
        return
    if hanh_dong == "bo":
        await it.response.edit_message(content=f"{bot_cong_viec.dau_tin(c)}\nBỏ qua — {it.user.mention}", view=None)
        return
    if hanh_dong in ("chon", "jira", "khongbug"):
        await bot._review_bug(it, hanh_dong, c)
        return
    if hanh_dong == "huy":
        await bot._huy(it, c)
        return
    if hanh_dong == "huyhd":             # nut Huy trong bang /hang-doi: tin bang khong phai tin cua luot
        await huy_tu_hang_doi(bot, it, c)
        return
    if hanh_dong == "dung":
        await bot_dung_luot.bam_dung(bot, it, c)
        return
    if hanh_dong == "verify":
        await it.response.defer(ephemeral=True, thinking=True)
        try:
            tom_tat = await bot_job_verify.xep(bot, c, bot.get_channel(bot.kenh_qa))
        except Exception as exc:         # noqa: BLE001 - loi Jira tra ve cho nguoi bam
            log.exception("verify lai loi")
            tom_tat = f"⛔ Lỗi: {exc}"
        await it.followup.send(tom_tat[:2000], ephemeral=True)
        return
    c = {**c, "loai_ban": build_ma_app.loai_ban(c)}   # tin hoi tu truoc 31/10/2026 con ghi "debug" -> ban release
    vi_tri = bot.q.them({**c, "nguoi_duyet": it.user.id})   # check | thu lai
    if vi_tri is None:
        await it.response.send_message("Build này đã trong hàng đợi.", ephemeral=True)
        return
    await it.response.edit_message(view=nut(*NUT_HUY, msg_id=c["msg_id"]), content=f"{bot_cong_viec.dau_tin(c)}\n"
                                   f"Đã duyệt bởi {it.user.mention} — bản {c['loai_ban']}, vị trí {vi_tri} trong hàng đợi.")


async def huy(bot, it: discord.Interaction, c: dict) -> None:
    """Bo job DANG CHO khoi hang (bam nham Check, dev bao day nham ban). Job dang chay: nut Dung (bot_dung_luot)."""
    kq = bot.q.huy(c["msg_id"])
    if kq != "da_huy":
        await it.response.send_message(
            "Lượt này đang chạy trên máy — bấm **Dừng** ở tin của lượt nếu cần." if kq == "dang_chay"
            else "Build này không còn trong hàng đợi.", ephemeral=True)
        return
    await it.response.edit_message(**tin_sau_huy(c, it.user.mention))


async def huy_tu_hang_doi(bot, it: discord.Interaction, c: dict) -> None:
    """Huy tu bang /hang-doi (tin rieng cua nguoi go lenh): bo khoi hang roi sua TIN CUA LUOT o kenh QA
    giong bam Huy tai cho, tra loi rieng cho nguoi bam."""
    kq = bot.q.huy(c["msg_id"])
    if kq != "da_huy":
        await it.response.send_message(
            "Lượt này đang chạy trên máy — bấm **Dừng** nếu cần." if kq == "dang_chay"
            else "Build này không còn trong hàng đợi.", ephemeral=True)
        return
    await it.response.send_message(f"🚫 Đã huỷ {bot_cong_viec.dau_tin(c)} khỏi hàng đợi.", ephemeral=True)
    try:
        await (await bot._tin_qa(c["msg_id"])).edit(**tin_sau_huy(c, it.user.mention))
    except discord.HTTPException as exc:      # tin luot da xoa: job van da bo khoi hang
        log.warning("khong sua duoc tin luot sau khi huy: %s", exc)


def tin_sau_huy(c: dict, nguoi: str) -> dict:
    """Noi dung + nut cua tin luot sau khi bi huy khoi hang (nut Huy o tin do hoac o /hang-doi)."""
    ghi = f"🚫 Đã huỷ khỏi hàng đợi — {nguoi}"
    if c.get("loai_job") == "verify":   # bam Verify lai de xep lai
        return {"content": f"{bot_verify_jira.tin_ket_qua(c, [])}\n{ghi}",
                "view": nut(("verify", "Verify lại", XAM), msg_id=c["msg_id"])}
    # tra lai nut Check de chay lai khi can
    return {"content": f"{bot_cong_viec.dau_tin(c)}\n{ghi}", "view": nut(*NUT_HOI, msg_id=c["msg_id"])}


async def review_bug(bot, it: discord.Interaction, hanh_dong: str, c: dict, repo: Path, out: Path) -> None:
    """QA tick bug that trong menu roi bam Log Jira / Khong co bug that."""
    bugs, msg_id = c.get("bugs") or [], c["msg_id"]
    if not bugs or c.get("jira") is not None or msg_id in bot.dang_log:
        await it.response.send_message("Danh sách bug này đã xử lý xong hoặc đang log.", ephemeral=True)
        return
    if hanh_dong == "chon":
        c["bug_chon"] = sorted(int(x) for x in (it.data or {}).get("values", [])
                               if x.isdigit() and int(x) < len(bugs))
        bot.q.nho_tin(c)
        await it.response.edit_message(content=bot_cong_viec.tin_bug(bugs, c["bug_chon"], c),
                                       view=view_bug(bugs, c["bug_chon"], msg_id))
        return
    if hanh_dong == "khongbug":
        c["jira"] = {"issues": [], "loi": ""}
        bot.q.nho_tin(c)
        await it.response.edit_message(content=f"{bot_cong_viec.tin_bug(bugs, None, c)}\n"
                                       f"Không log — {it.user.mention} xác nhận không có bug thật.", view=None)
        return
    chon = c.get("bug_chon") or []
    if not chon:
        await it.response.send_message("Chưa tick bug nào trong menu.", ephemeral=True)
        return
    if not bot.reviewer:
        await it.response.send_message("Bot thiếu DISCORD_JIRA_REVIEWER trong bot.env.", ephemeral=True)
        return
    bot.dang_log.add(msg_id)
    await it.response.edit_message(content=f"{bot_cong_viec.tin_bug(bugs, chon, c)}\n"
                                   f"Đang log {len(chon)} bug lên Jira ({c['ma']}) — {it.user.mention}", view=None)
    try:
        # Gan bug cho dev gui build, khong de Jira tu gan nguoi mac dinh cua project (user chot 30/10/2026)
        dev = await bot_kenh_project.login_jira_gui_build(bot, c)
        kq = await asyncio.to_thread(bot_log_jira.chay, [bugs[i] for i in chon], {**c, "dev_jira": dev},
                                     c.get("link_report", ""), bot.reviewer, repo, out)
    except Exception as exc:             # noqa: BLE001 - loi luot log khong duoc giet bot
        log.exception("log jira loi")
        await it.message.edit(view=view_bug(bugs, chon, msg_id))   # tra menu lai de bam thu lai
        await it.message.reply(f"⛔ Log Jira lỗi: {exc}")
        return
    finally:
        bot.dang_log.discard(msg_id)
    so = len([i for i in kq.get("issues") or [] if i.get("key")])
    if not so:
        # Khong tao duoc issue nao (Jira / MCP loi) -> chua tinh la da log: tra menu de bam thu lai.
        await it.message.reply(bot_cong_viec.tin_jira(kq, len(chon)))
        await it.message.edit(view=view_bug(bugs, chon, msg_id))
        return
    c["jira"] = kq
    bot.q.nho_tin(c)
    tin_dev = bot_cong_viec.tin_bao_dev(c, kq, [bugs[i] for i in chon])
    keys = [i["key"] for i in kq.get("issues") or [] if i.get("key")]
    kenh_dev = await bot._bao_dev(c, tin_dev, it.message, keys) if tin_dev else None
    # Log du + bao duoc dev o kenh project -> khong dang them tin o kenh QA (user chot 28/10/2026),
    # chi sua dong trang thai cua tin menu. Thieu issue / Jira bao loi / khong bao duoc dev -> bao o QA.
    if kenh_dev is not None and so == len(chon) and not kq.get("loi"):
        await it.message.edit(content=f"{bot_cong_viec.tin_bug(bugs, chon, c)}\n"
                                      f"✅ Đã log {so} bug, đã báo dev ở {kenh_dev.mention} — {it.user.mention}")
    else:
        await it.message.reply(bot_cong_viec.tin_jira(kq, len(chon)))
