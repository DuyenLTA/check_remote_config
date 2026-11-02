"""Bot chinh nhan tin bao build: tach ma app + version, tra package, hoi QA o kenh QA (nut Check), xep luot
verify bug Reviewing; QA gui lai tin build / tra loi kem link Drive.

Goi tu `BuildBot.on_message` (sau khi da loai tin dieu phoi, may phu, hoi dap). Ham nhan `bot` (BuildBot) va goi
lai cac method mong cua no (`bot._hoi_lai`, `bot._xep_verify`) de test thay duoc tung buoc.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import discord

from . import bot_cong_viec, bot_jira_rest, bot_job_verify, bot_kenh_project, build_ma_app, cai_apk_tu_drive
from .bot_giao_dien import GIU_KHI_HOI_LAI, NUT_HOI, noi_dung, nut, tha_tim

log = logging.getLogger("rcr-bot")
CHO_JIRA, SO_LAN_JIRA = 5 * 60, 6     # Jira mat ket noi khi xep verify: thu lai moi 5 phut, toi da 30 phut


async def nhan_tin_build(bot, m: discord.Message, out: Path) -> None:
    # dev bao build qua webhook "Build Notification" (author.bot=True) hoac bot Assistant cua dev
    # (DungNT2-Assistant, co trong bang tag dev) -> nhan; bo bot khac
    if m.author.bot and not m.webhook_id and not bot_kenh_project.la_bot_dev(m.author.id):
        return
    # Chi nhan build o kenh rieng cua tung project (`aip922-...`, moi server bot dang o) va kenh trong
    # DISCORD_BUILD_CHANNEL_ID (qa-auto). Kenh chung build-notification bo tu 30/10/2026 (user chot: chat
    # thuong o do bi bot hoi nham la tin build).
    o_kenh_build = m.channel.id in bot.kenh_build
    ma_kenh = "" if o_kenh_build else build_ma_app.ma_cua_kenh(
        getattr(getattr(m.channel, "parent", None) or m.channel, "name", ""))
    if not o_kenh_build and not (ma_kenh and m.guild):
        return
    # QA nhan o kenh project ("test pass v1.4.0(14)... rls") khong phai tin bao build: khong tha tim, khong hoi
    # (user chot 30/10/2026 - bot tha tim nham vao tin bao rls AIP805). QA gui lai build thi gui o qa-auto.
    if m.channel.id != bot.kenh_qa and not m.webhook_id and bot._duoc_duyet(m.author):
        return
    chu = noi_dung(m)
    tin = build_ma_app.tach(chu, ma_kenh)
    kenh = bot.get_channel(bot.kenh_qa)
    if tin is None:
        # Khong bam mau cau: tin webhook (bao build tu dong) hoac tin co ma app ma khong doc ra
        # version -> hoi QA. Kenh project con chat thuong nen chi hoi voi tin webhook.
        # Kenh QA cung la kenh build (QA gui lai tin build de chay lai), nhung webhook o day la
        # thong bao cua chinh cac tool (audit, rc-check) chu khong phai tin bao build -> bo qua.
        if m.webhook_id and m.channel.id == bot.kenh_qa:
            return
        if m.webhook_id or (o_kenh_build and build_ma_app.co_ma_app(chu)):
            await kenh.send(f"Bot không đọc được mã app + version (dạng `AIP922 v3.7.0 (30)`) "
                            f"trong tin báo build — QA xem giúp: {m.jump_url}")
        return
    if m.channel.id != bot.kenh_qa:     # tin build cua dev: tha tim bao da nhan (user chot 30/10/2026)
        await tha_tim(m)
    cu = [t for t in bot.q.tin.values() if t.get("ma") == tin["ma"] and t.get("version") == tin["version"]]
    if cu:
        # Giai doan chuyen kenh dev co the bao mot build o ca kenh chung lan kenh project.
        log.info("build da hoi roi: %s %s (%s)", tin["ma"], tin["version"], m.jump_url)
        # QA gui lai tin build de chay lai -> tro ve tin Check cu (build chi co luot verify thi khong co tin Check)
        if m.channel.id == bot.kenh_qa and any(t.get("loai_job") != "verify" for t in cu):
            await bot._hoi_lai(m, tin)
        return
    pkg = await asyncio.to_thread(bot_cong_viec.package_cua, tin["ma"], out)
    if not tin["sdk"]:
        # Build chuc nang / fix bug, khong apply SDK: khong hoi Check (chua co workflow, user chot 28/10/2026)
        # nhung VAN verify bug dev da keo Reviewing - build fix bug thuong khong ghi SDK (user chot 28/10/2026).
        log.info("build khong apply SDK, chi verify bug Reviewing: %s %s", tin["ma"], tin["version"])
        if pkg:
            await bot._xep_verify({**tin, "package": pkg, "loai_ban": build_ma_app.loai_ban(tin),
                                   "link_tin": m.jump_url}, kenh)
        return
    if not pkg:
        await kenh.send(f"Sheet Check thông số KT không có package của **{tin['ma']}** — {m.jump_url}")
        return
    qa = await kenh.send(f"**{tin['ma']}** `{tin['version']}`…")
    c = {**tin, "package": pkg, "loai_ban": build_ma_app.loai_ban(tin), "link_tin": m.jump_url, "msg_id": qa.id}
    bot.q.nho_tin(c)
    await qa.edit(content=bot_cong_viec.tin_hoi(c), view=nut(*NUT_HOI, msg_id=qa.id))
    await bot._xep_verify(c, kenh)


async def hoi_lai(bot, m: discord.Message, tin: dict) -> None:
    """Build da hoi roi, QA gui lai tin build o kenh QA -> tin hoi MOI (nut Check) tra loi ngay duoi tin
    QA vua gui, bo phien cu. Truoc day bot bat lai nut o tin cu va gui link -> QA bi day len tin cu
    (user phan nan 29/10/2026). Tin cu giu nguyen (con menu log bug / ket qua). Dang cho/chay thi chi
    bao trang thai ngay duoi, khong tao luot trung. Dev bao trung o kenh khac thi van im (o noi goi)."""
    cung = [t for t in bot.q.tin.values()
            if t.get("ma") == tin["ma"] and t.get("version") == tin["version"] and t.get("loai_job") != "verify"]
    if any(bot.q.vi_tri(t["msg_id"]) is not None for t in cung):
        await m.reply(f"Build **{tin['ma']}** `{tin['version']}` đang chờ / đang chạy — xong bot báo kết quả.",
                      mention_author=False)
        return
    c_cu = max(cung, key=lambda t: int(t["msg_id"]))   # snowflake tang dan -> lan hoi gan nhat
    qa = await m.reply(f"**{c_cu['ma']}** `{c_cu['version']}`…", mention_author=False)
    c = {k: c_cu[k] for k in GIU_KHI_HOI_LAI if k in c_cu}
    # Tin luu tu truoc 31/10/2026 con ghi "debug" -> tinh lai: gio moi build deu cai ban release.
    c.update(link_tin=m.jump_url, msg_id=qa.id, loai_ban=build_ma_app.loai_ban(c))
    bot.q.nho_tin(c)
    await qa.edit(content=bot_cong_viec.tin_hoi(c), view=nut(*NUT_HOI, msg_id=qa.id))


async def nhan_link_drive(bot, m: discord.Message) -> bool:
    """QA tra loi tin hoi cua bot kem link Google Drive (ban debug) -> gan link vao build do: bam Check /
    Verify thi tai APK tu link thay cho App Tester (user chot 29/10/2026). True khi da xu ly tin nay."""
    ref = getattr(getattr(m, "reference", None), "message_id", None)
    c = bot.q.tin_cua(ref) if ref and m.channel.id == bot.kenh_qa else None
    link = cai_apk_tu_drive.tim_link(m.content or "") if c is not None else ""
    if not link or not bot._duoc_duyet(m.author):
        return False
    c["drive"] = link
    bot.q.nho_tin(c)
    try:                                     # tin hoi cu ghi ro se tai tu Drive
        cu = await bot._tin_qa(ref)
        if c.get("loai_job") != "verify":
            await cu.edit(content=bot_cong_viec.tin_hoi(c), view=nut(*NUT_HOI, msg_id=cu.id))
    except discord.HTTPException:
        pass
    await m.reply(f"📦 Đã nhận link Drive cho **{c['ma']}** `{c['version']}` — bấm **Check** / **Verify** ở tin "
                  "hỏi, bot sẽ tải APK từ link này thay cho App Tester.", mention_author=False)
    return True


async def xep_verify(bot, c: dict, kenh) -> None:
    """Tim bug bot da log cua app dang Reviewing -> xep luot verify tren build `c`."""
    # Mang toi Jira chap chon vai phut (VPN) -> im lang doi roi thu lai, chi bao QA khi het luot van loi
    # (user phan nan 30/10/2026: bao loi ket noi tieng Anh ngay lan dau, ma app khong co bug Reviewing nao).
    for lan in range(SO_LAN_JIRA):
        try:                             # loi verify khong duoc lam hong tin Check vua gui
            tom_tat = await bot_job_verify.xep(bot, c, kenh)
            log.info("verify %s: %s", c["ma"], tom_tat)
            return
        except bot_jira_rest.JiraMatKetNoi as exc:
            log.warning("verify %s: Jira chua ket noi duoc (lan %d): %s", c["ma"], lan + 1, exc)
            if lan < SO_LAN_JIRA - 1:
                await asyncio.sleep(CHO_JIRA)
        except Exception as exc:         # noqa: BLE001
            log.exception("xep verify loi")
            await kenh.send(f"⚠️ Không kiểm được bug Reviewing của **{c['ma']}**: {exc}"[:2000])
            return
    await kenh.send(f"⚠️ Chưa kiểm được bug Reviewing của **{c['ma']}** `{c['version']}`: Jira không kết nối "
                    f"được suốt {SO_LAN_JIRA * CHO_JIRA // 60} phút (VPN?). Kết nối lại thì bấm **Verify bug Jira** "
                    f"ở tin Check, build không có tin Check thì gửi lại tin build để bot kiểm lại.")
