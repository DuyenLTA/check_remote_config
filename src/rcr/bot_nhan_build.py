"""Bot chinh nhan tin bao build: tach ma app + version, tra package, hoi QA o kenh QA (nut Check), xep luot
verify bug Reviewing; QA gui lai tin build de chay lai.

Goi tu `BuildBot.on_message` (sau khi da loai tin dieu phoi, may phu, hoi dap). Ham nhan `bot` (BuildBot) va goi
lai cac method mong cua no (`bot._hoi_lai`, `bot._xep_verify`) de test thay duoc tung buoc.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import discord

from . import bot_cong_viec, bot_forum, bot_jira_rest, bot_job_verify, bot_kenh_project, build_ma_app
from . import bot_tin_goc as tin_goc
from .bot_giao_dien import GIU_KHI_HOI_LAI, NUT_HOI, noi_dung, nut

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
    if build_ma_app.la_kenh_bo(getattr(m.channel, "name", "")):
        return
    o_kenh_build = m.channel.id in bot.kenh_build
    ma_kenh = "" if o_kenh_build else build_ma_app.ma_cua_kenh(
        getattr(getattr(m.channel, "parent", None) or m.channel, "name", ""))
    if not o_kenh_build and not (ma_kenh and m.guild):
        return
    # QA nhan o kenh project ("test pass v1.4.0(14)... rls") khong phai tin bao build: khong hoi
    # (user chot 30/10/2026 - tin bao rls AIP805 bi nhan nham la build). QA gui lai build thi gui o qa-auto.
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
    cu = tin_da_hoi(bot, tin)
    if cu:
        # Giai doan chuyen kenh dev co the bao mot build o ca kenh chung lan kenh project.
        log.info("build da hoi roi: %s %s (%s)", tin["ma"], tin["version"], m.jump_url)
        # QA gui lai tin build de chay lai -> tro ve tin Check cu (build chi co luot verify thi khong co tin Check)
        if m.channel.id == bot.kenh_qa and any(t.get("loai_job") != "verify" for t in cu):
            await bot._hoi_lai(m, tin)
        elif la_dev_day_lai(bot, m, cu):
            log.info("dev day lai cung version: %s %s (%s)", tin["ma"], tin["version"], m.jump_url)
            await dev_day_lai(bot, tin, m.jump_url, kenh)
        return
    await hoi_build_moi(bot, tin, m.jump_url, kenh, out)


def la_dev_day_lai(bot, m: discord.Message, cu: list[dict]) -> bool:
    """Tin bao build MOI cua dev (webhook / bot Assistant cua dev) trung ma + version voi build da hoi: dev build
    lai ma khong tang so version. Tin da xu ly roi (quet lai tin lo sau restart) thi link trung `link_tin` da luu."""
    tu_dev = bool(m.webhook_id) or bot_kenh_project.la_bot_dev(m.author.id)
    return tu_dev and m.jump_url not in {t.get("link_tin") for t in cu}


async def dev_day_lai(bot, tin: dict, link_tin: str, kenh) -> None:
    """Dev day lai CUNG version (build moi that, vd AIP922 3.9.0 (32) ngay 11/11/2026 them TikTok config + ads-core
    2.0.1 - truoc day bot im). Build da hoi Check -> hoi Check lai (cai ban moi nhat tu App Tester); lan nao cung
    xep verify bug Reviewing tren build moi. Luot cu dang cho / dang chay thi ghi them dong vao tin goc cua no."""
    check = [t for t in tin_da_hoi(bot, tin) if t.get("loai_job") != "verify"]
    if check:
        kq = await hoi_lai_build(bot, tin, link_tin, kenh.send)
        if kq.startswith("Build"):       # dang cho / dang chay: khong tao luot trung, bao tren tin goc cu
            c_cu = max(check, key=lambda t: int(t["msg_id"]))
            await _canh_bao(bot, c_cu, kenh, f"🔁 Dev đẩy lại `{tin['version']}` (cùng version) lúc lượt này đang "
                                             f"chờ / chạy — xong lượt thì QA gửi lại tin build để chạy bản mới: {link_tin}")
            return
    moi = max(tin_da_hoi(bot, tin), key=lambda t: int(t.get("msg_id") or 0))
    await bot._xep_verify({**moi, "link_tin": link_tin}, kenh)


def tin_da_hoi(bot, tin: dict) -> list[dict]:
    """Moi tin bot da luu (hoi Check / verify) cua cung ma app + version."""
    return [t for t in bot.q.tin.values() if t.get("ma") == tin["ma"] and t.get("version") == tin["version"]]


async def hoi_build_moi(bot, tin: dict, link_tin: str, kenh, out: Path) -> str:
    """Build bot chua tung hoi: tra package, gui tin hoi (nut Check) o kenh QA + xep verify bug Reviewing.
    Dung chung cho tin bao build va lenh /check. Tra cau tom tat cho nguoi go lenh."""
    pkg = await asyncio.to_thread(bot_cong_viec.package_cua, tin["ma"], out)
    goc = f" — {link_tin}" if link_tin else ""
    if not tin["sdk"]:
        # Build chuc nang / fix bug, khong apply SDK: khong hoi Check (chua co workflow, user chot 28/10/2026)
        # nhung VAN verify bug dev da keo Reviewing - build fix bug thuong khong ghi SDK (user chot 28/10/2026).
        if not bot.q.bao_lan_dau(f"{tin['ma']}|{tin['version']}"):   # quet lai tin lo sau restart: da bao roi
            return f"Build **{tin['ma']}** `{tin['version']}` không ghi SDK — đã báo trước đó."
        log.info("build khong apply SDK, chi verify bug Reviewing: %s %s", tin["ma"], tin["version"])
        # Van BAO QA moi build (user chot 05/11/2026): dev hay quen ghi SDK, QA tu kiem roi go /check kem SDK.
        await kenh.send(f"🔔 **{tin['ma']}** `{tin['version']}` — tin build không ghi SDK nên bot chưa hỏi Check, "
                        f"chỉ verify bug Reviewing.\nBuild có apply SDK thì gõ `/check {tin['ma']} {tin['version']} "
                        f"<sdk>` (vd `3.6.1`, `3.7.0`, `next-gen`){goc}")
        if not pkg:
            return f"Sheet Check thông số KT không có package của **{tin['ma']}**."
        await bot._xep_verify({**tin, "package": pkg, "loai_ban": build_ma_app.loai_ban(tin),
                               "link_tin": link_tin}, kenh)
        return f"Build không apply SDK → không hỏi Check, chỉ xếp verify bug Reviewing của **{tin['ma']}**."
    if not pkg:
        await kenh.send(f"Sheet Check thông số KT không có package của **{tin['ma']}**{goc}")
        return f"Sheet Check thông số KT không có package của **{tin['ma']}**."
    qa = await bot_forum.gui_goc(bot, tin, f"**{tin['ma']}** `{tin['version']}`…", kenh.send)
    c = {**tin, "package": pkg, "loai_ban": build_ma_app.loai_ban(tin), "link_tin": link_tin, "msg_id": qa.id,
         **bot_forum.kenh_cua(qa)}
    bot.q.nho_tin(c)
    await qa.edit(content=bot_cong_viec.tin_hoi(c), view=nut(*NUT_HOI, msg_id=qa.id))
    await bot._xep_verify(c, kenh)
    return f"Đã gửi tin hỏi Check: {qa.jump_url}"


async def hoi_lai(bot, m: discord.Message, tin: dict) -> None:
    """Build da hoi roi, QA gui lai tin build o kenh QA -> tin hoi MOI (nut Check) tra loi ngay duoi tin
    QA vua gui, bo phien cu. Truoc day bot bat lai nut o tin cu va gui link -> QA bi day len tin cu
    (user phan nan 29/10/2026). Tin cu giu nguyen (con menu log bug / ket qua). Dang cho/chay thi chi
    bao trang thai ngay duoi, khong tao luot trung. Dev bao trung o kenh khac thi van im (o noi goi)."""
    kq = await hoi_lai_build(bot, tin, m.jump_url, lambda chu: m.reply(chu, mention_author=False))
    # dang cho / dang chay: bao ngay duoi tin QA gui. Forum bat: tin hoi moi nam trong bai cua build -> tra link.
    if kq.startswith("Build") or bot_forum.bat(bot):
        await m.reply(kq, mention_author=False)


async def hoi_lai_build(bot, tin: dict, link_tin: str, gui, doi: dict | None = None) -> str:
    """Tao tin hoi MOI cho build da hoi (giu thong tin build cua lan hoi gan nhat). `gui(chu)` gui tin
    (tra loi duoi tin QA, hoac gui vao kenh QA khi go /check). Dang cho / dang chay thi khong tao luot trung.
    `doi`: truong build thay cho lan hoi cu (QA go /check kem SDK khac). Tra cau tom tat; cau bat dau bang
    "Build" la bao trang thai (chua tao tin nao)."""
    cung = [t for t in tin_da_hoi(bot, tin) if t.get("loai_job") != "verify"]
    if any(bot.q.vi_tri(t["msg_id"]) is not None for t in cung):
        return f"Build **{tin['ma']}** `{tin['version']}` đang chờ / đang chạy — xong bot báo kết quả."
    c_cu = max(cung, key=lambda t: int(t["msg_id"]))   # snowflake tang dan -> lan hoi gan nhat
    qa = await bot_forum.gui_goc(bot, c_cu, f"**{c_cu['ma']}** `{c_cu['version']}`…", gui)
    c = {**{k: c_cu[k] for k in GIU_KHI_HOI_LAI if k in c_cu}, **(doi or {})}
    # Tin luu tu truoc 31/10/2026 con ghi "debug" -> tinh lai: gio moi build deu cai ban release.
    c.update(link_tin=link_tin, msg_id=qa.id, loai_ban=build_ma_app.loai_ban(c), **bot_forum.kenh_cua(qa))
    bot.q.nho_tin(c)
    await qa.edit(content=bot_cong_viec.tin_hoi(c), view=nut(*NUT_HOI, msg_id=qa.id))
    return f"Đã gửi tin hỏi Check mới: {qa.jump_url}"


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
            await _canh_bao(bot, c, kenh, f"⚠️ Không kiểm được bug Reviewing của **{c['ma']}**: {exc}")
            return
    await _canh_bao(bot, c, kenh, f"⚠️ Chưa kiểm được bug Reviewing của **{c['ma']}** `{c['version']}`: Jira không "
                    f"kết nối được suốt {SO_LAN_JIRA * CHO_JIRA // 60} phút (VPN?). Kết nối lại thì bấm **Verify bug "
                    f"Jira** ở tin Check, build không có tin Check thì gửi lại tin build để bot kiểm lại.")


async def _canh_bao(bot, c: dict, kenh, dong: str) -> None:
    """Build da co tin goc (tin hoi Check) -> them dong canh bao vao tin do; chua co tin goc moi gui tin moi."""
    if c.get("msg_id"):
        try:
            qa = await bot._tin_qa(int(c["msg_id"]))
            await qa.edit(content=tin_goc.noi(qa.content, dong))
            return
        except discord.HTTPException as exc:
            log.warning("khong sua duoc tin goc de canh bao: %s", exc)
    await kenh.send(dong[:2000])
