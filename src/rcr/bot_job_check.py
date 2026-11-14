"""Luot Check cua bot: cai build -> kiem `testvsl` (ban release) -> chay `/rc-check` bang Claude headless -> bao
ket qua + menu bug vao tin cua build o kenh QA. Doi xung voi `bot_job_verify` (luot verify bug Reviewing).

Ket qua (`kq`) ghi vao job trong hang doi NGAY khi chay xong; gui loi mang thi `bot_gui_lai` goi lai `chay` -
job co `kq` thi chi gui ket qua, buoc da gui (`da_bao`, `da_bao_bug`) khong gui trung.
"""

from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path

import discord

from . import (audit_tom_tat, bot_chay_claude, bot_cong_viec, bot_dung_luot, bot_forum, bot_hop_thu_bug,
               bot_kiem_testvsl, bot_report_may_phu, build_ma_app, usage_log)
from . import bot_bug_tu_file_luot
from . import bot_tin_goc as tin_goc
from .bot_giao_dien import XAM, XANH, nut

log = logging.getLogger("rcr-bot")


async def chay(bot, job: dict, serial: str, ten: str, repo: Path, out: Path) -> None:
    qa = await bot._tin_qa(job["msg_id"])
    if job.get("kq") is None:            # co kq = da chay xong, lan truoc gui ket qua loi -> chi gui lai
        if not await cai_va_chay(bot, job, qa, serial, ten, repo, out):
            return
    await bao_ket_qua(bot, job, qa, out)


async def cai_va_chay(bot, job: dict, qa, serial: str, ten: str, repo: Path, out: Path) -> bool:
    """Cai build roi chay /rc-check; ket qua ghi vao job (luu file) truoc khi gui. False khi cai hong /
    chua co `testvsl`."""
    dau = f"{bot_cong_viec.dau_tin(job)} · máy **{ten}**"
    await qa.edit(content=f"{dau}\nĐang cài bản {job['loai_ban']} từ App Tester…",
                  view=bot_dung_luot.view_dung(qa.id))   # thay nut Huy bang nut Dung
    await bot_forum.dat_nhan(bot, job, bot_forum.DANG_CHAY)
    cai = await asyncio.to_thread(bot_cong_viec.cai, job["package"], job["version"], job["loai_ban"], serial)
    if "loi" in cai:
        await bot_forum.dat_nhan(bot, job, bot_forum.CAN_XEM)
        # Moi build deu cai ban release tu App Tester -> cai hong chi bao loi + nut Thu lai (user chot 02/11/2026).
        await qa.edit(content=f"{dau}\n⛔ Cài không được: {cai['loi']}",
                      view=nut(("check", "Thử lại", XANH), ("bo", "Bỏ qua", XAM), msg_id=qa.id))
        return False
    ghi = " (đã gỡ bản cũ rồi tải lại — mất data app)" if cai.get("go_ban_cu") else ""
    if job.get("loai_job") == "sub":     # /check-sub: khong doi Remote Config -> khong can testvsl
        await qa.edit(content=f"{dau}\n📲 Đã cài{ghi}. Đang chạy /sub-check…")
        bat_dau = time.time()
        kq = await asyncio.to_thread(bot_chay_claude.chay, job["package"], serial, repo, bot_chay_claude.TIMEOUT_SUB,
                                     out, None, False, "", job["version"])
        bot.q.cap_nhat(job, kq=kq, ten_may=ten, bat_dau=bat_dau)
        return True
    # /check tinh_nang hoac tin build chi ghi tinh nang: chi bo tinh nang, van doi RC qua testvsl.
    # Tin build ghi ca SDK lan tinh nang: chay SDK roi lan luot tung tinh nang, gop mot report (user chot 14/11/2026).
    tinh_nang = build_ma_app.chi_tinh_nang(job)
    them_tn = [] if tinh_nang else build_ma_app.tabs_tinh_nang(job)
    next_gen = False if tinh_nang else build_ma_app.la_next_gen(job)
    # Checklist Next-Gen khong doi RC, nhung bo tinh nang chay sau no thi co -> van can testvsl.
    chi_checklist = next_gen and not them_tn
    if bot_kiem_testvsl.doi_rc_firebase(job, chi_checklist):
        loi = await bot_kiem_testvsl.loi_testvsl(serial, job["package"])
        if loi:                          # chua co / sai testvsl: nhac QA tao, khong chay, khong dung Firebase
            await bot_forum.dat_nhan(bot, job, bot_forum.CAN_XEM)
            await qa.edit(content=tin_goc.noi(f"{dau}\n📲 Đã cài{ghi}.", bot_kiem_testvsl.tin_nhac(job, loi, bot.duyet)),
                          view=nut(("check", "Chạy lại", XANH), ("bo", "Bỏ qua", XAM), msg_id=qa.id))
            return False
    await qa.edit(content=f"{dau}\n📲 Đã cài{ghi}. Đang chạy /rc-check…")
    timeout = bot_chay_claude.TIMEOUT_NEXT_GEN if next_gen else bot_chay_claude.TIMEOUT_BO_TC
    bat_dau = time.time()
    bot_dung_luot.danh_dau_pha_rc(job, chi_checklist)  # Dung tu day -> phai don RC testvsl
    # Tin build ghi next-gen -> ep rc-check nhanh checklist; con lai bo TC (ban release doi RC qua Firebase).
    kq = await asyncio.to_thread(bot_chay_claude.chay, job["package"], serial, repo, timeout, out,
                                 None, next_gen, "" if tinh_nang else job.get("tutorial") or "", "",
                                 bool(job.get("bo_qua_plan")),
                                 build_ma_app.tabs_tinh_nang(job) if tinh_nang else None, them_tn)
    bot.q.cap_nhat(job, kq=kq, ten_may=ten, bat_dau=bat_dau)
    return True


def dung_vi_plan(kq: dict) -> bool:
    """Luot dung o preflight vi build khac plan tuan (rc-check.md 3b: `tom_tat` mo dau "Build khác plan tuần")."""
    return kq.get("trang_thai") == "DUNG" and "khác plan tuần" in (kq.get("tom_tat") or "").lower()


def nut_ket_qua(job: dict, kq: dict) -> list[tuple]:
    """Nut tren tin ket qua. Dung vi khac plan tuan -> them "Chạy bỏ qua plan": dev hay chi nang / ha version, ben
    trong giong nhau, QA muon chay luon (user chot 09/11/2026). Luot da bo qua plan roi thi khong hien lai."""
    cac = [("verify", "Verify bug Jira", XAM)]
    if dung_vi_plan(kq) and not job.get("bo_qua_plan"):
        cac.insert(0, ("boquaplan", "Chạy bỏ qua plan", XANH))
    return cac


async def bao_ket_qua(bot, job: dict, qa, out: Path) -> None:
    """Gui ket qua luot da chay. Goi lai duoc nhieu lan (mat mang giua chung): buoc nao da gui thi bo qua."""
    if not job.get("da_bao"):
        # Phien Claude chet truoc khi ghi KET_QUA (LOI / HET_GIO) -> lay case FAIL tu file luot de van co menu bug.
        cuu = bot_bug_tu_file_luot.cuu_ket_qua(job["kq"], out, job["package"], job.get("bat_dau"))
        if cuu is not job["kq"]:
            bot.q.cap_nhat(job, kq=cuu)        # sua tai cho: cac buoc sau (da_bao, da_bao_bug) ghi vao dung job
    kq, ten = job["kq"], job.get("ten_may") or "?"
    chu = bot_cong_viec.TRANG_THAI.get(kq["trang_thai"], ("", kq["trang_thai"]))[1]
    dong_dau = f"{bot_cong_viec.dau_tin(job)} · máy **{ten}**\n{chu}"
    f = bot_cong_viec.file_report(kq, out)
    if not job.get("da_bao"):
        # Tom tat ID ads doc bang code (dung package, ghi trong luot nay), khong theo chu Claude viet.
        # Trang audit day du nam trong tab cua chinh report -> chi dinh kem mot file report.
        # Luot sub / tab tinh nang khong check ID ads -> khong co dong audit.
        audit = "" if job.get("loai_job") == "sub" or build_ma_app.chi_tinh_nang(job) else audit_tom_tat.dong_tin(
            audit_tom_tat.tim(job["package"], tu_luc=job.get("bat_dau") or 0))
        # Ket qua + file report + nut Verify nam ngay tren tin goc (khong tra loi tin moi).
        await qa.edit(content=dong_dau,
                      embeds=[tin_goc.embed(tin_goc.KET_QUA, bot_cong_viec.tin_ket_qua(job, kq, f)
                                            + (f"\n{audit}" if audit else ""))],
                      attachments=[],
                      view=nut(*nut_ket_qua(job, kq), msg_id=job["msg_id"]))
        if f:   # chua co artifact -> phien publish lam, bot thay link vao tin nay (khong gui HTML)
            # May phu: gui HTML sang bot chinh (chi bot chinh co phien publish) - bot_report_may_phu.
            await bot_report_may_phu.them(bot, out, f, qa.channel.id, qa.id, bot_cong_viec.dau_tin(job),
                                          f"{job.get('ma', '')} {job.get('version', '')}".strip())
        bot.q.cap_nhat(job, da_bao=True)
        await bot_forum.dat_nhan(bot, job, bot_forum.nhan_ket_qua(kq))
    else:
        await qa.edit(content=dong_dau)
    if not job.get("da_log"):
        # Bang chung dung that: moi luot mot dong (nguoi duyet, thoi gian, ket qua) - khong phu thuoc Claude nho ghi.
        try:
            ngay = time.strftime("%d/%m/%Y", time.localtime(job.get("bat_dau") or time.time()))
            usage_log.ghi_luot_bot(job, kq, out, ngay)
        except Exception:                # noqa: BLE001 - ghi log hong khong duoc chan menu bug / ping
            log.exception("ghi usage-log bot loi")
        bot.q.cap_nhat(job, da_log=True)
    if kq.get("bugs") and not job.get("da_bao_bug"):
        # Luu vao tin cua build: bot khoi dong lai van tick / log tiep duoc.
        # link_report la duong dan file chi khi file do thuc su duoc dinh kem (tin_bug ghi "đính kèm")
        c = bot_hop_thu_bug.gan_bug(bot.q.tin_cua(job["msg_id"]) or job, kq["bugs"],
                                    kq.get("link", "") if kq.get("link", "").startswith("https://") else str(f or ""))
        # Chua publish duoc artifact -> dinh kem luon file report vao tin bug: QA phai mo duoc report
        # ngay tai tin can review, khong phai keo len tim tin ket qua.
        await bot_hop_thu_bug.dang_menu(bot, qa, c)
        bot.q.cap_nhat(job, da_bao_bug=True)
    if not job.get("da_ping"):
        so_bug = len(kq.get("bugs") or [])
        await tin_goc.ping_xong(bot, qa, f"🔔 **{job['ma']}** `{job['version']}` xong — {chu}"
                                         + (f", {so_bug} bug cần review" if so_bug else "") + " (xem tin gốc).")
        bot.q.cap_nhat(job, da_ping=True)
