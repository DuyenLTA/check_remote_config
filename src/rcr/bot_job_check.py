"""Luot Check cua bot: cai build -> kiem `testvsl` (ban release) -> chay `/rc-check` bang Claude headless -> bao
ket qua + menu bug vao tin cua build o kenh QA. Doi xung voi `bot_job_verify` (luot verify bug Reviewing).

Ket qua (`kq`) ghi vao job trong hang doi NGAY khi chay xong; gui loi mang thi `bot_gui_lai` goi lai `chay` -
job co `kq` thi chi gui ket qua, buoc da gui (`da_bao`, `da_bao_bug`) khong gui trung.
"""

from __future__ import annotations

import asyncio
import time
from pathlib import Path

import discord

from . import audit_tom_tat, bot_chay_claude, bot_cong_viec, bot_dung_luot, bot_kiem_testvsl, build_ma_app
from .bot_giao_dien import XAM, XANH, nut, view_bug


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
    nguon = "từ link Drive" if job.get("drive") else "từ App Tester"
    await qa.edit(content=f"{dau}\nĐang cài bản {job['loai_ban']} {nguon}…",
                  view=bot_dung_luot.view_dung(qa.id))   # thay nut Huy bang nut Dung
    cai = await asyncio.to_thread(bot_cong_viec.cai, job["package"], job["version"], job["loai_ban"], serial,
                                  job.get("drive", ""))
    if "loi" in cai:
        # Thuong la App Tester chua co ban (dev chua day) -> hoi link Drive, de nguoi bam thu lai sau.
        hoi = bot_cong_viec.hoi_link_drive(job)
        await qa.edit(content=f"{dau}\n⛔ Cài không được: {cai['loi']}" + (f"\n{hoi}" if hoi else ""),
                      view=nut(("check", "Thử lại", XANH), ("bo", "Bỏ qua", XAM), msg_id=qa.id))
        return False
    ghi = " (đã gỡ bản cũ khác loại — mất data app)" if cai.get("go_ban_cu") else ""
    next_gen = build_ma_app.la_next_gen(job)
    if bot_kiem_testvsl.doi_rc_firebase(job, next_gen):
        loi = await bot_kiem_testvsl.loi_testvsl(serial, job["package"])
        if loi:                          # chua co / sai testvsl: nhac QA tao, khong chay, khong dung Firebase
            await qa.edit(content=f"{dau}\nĐã cài{ghi}. ⛔ Chưa chạy: điều kiện `testvsl` chưa sẵn sàng.",
                          view=nut(("check", "Chạy lại", XANH), ("bo", "Bỏ qua", XAM), msg_id=qa.id))
            await qa.reply(bot_kiem_testvsl.tin_nhac(job, loi, bot.duyet))
            return False
    await qa.edit(content=f"{dau}\nĐã cài{ghi}. Đang chạy /rc-check…")
    await qa.reply(bot_cong_viec.tin_da_cai(job, ten, "/rc-check"))
    timeout = bot_chay_claude.TIMEOUT_NEXT_GEN if next_gen else bot_chay_claude.TIMEOUT_BO_TC
    bat_dau = time.time()
    bot_dung_luot.danh_dau_pha_rc(job, next_gen)       # Dung tu day -> phai don RC testvsl
    # Tin build ghi next-gen -> ep rc-check nhanh checklist; con lai bo TC (ban release doi RC qua Firebase).
    kq = await asyncio.to_thread(bot_chay_claude.chay, job["package"], serial, repo, timeout, out,
                                 None, next_gen, job.get("tutorial") or "")
    bot.q.cap_nhat(job, kq=kq, ten_may=ten, bat_dau=bat_dau)
    return True


async def bao_ket_qua(bot, job: dict, qa, out: Path) -> None:
    """Gui ket qua luot da chay. Goi lai duoc nhieu lan (mat mang giua chung): buoc nao da gui thi bo qua."""
    kq, ten = job["kq"], job.get("ten_may") or "?"
    chu = bot_cong_viec.TRANG_THAI.get(kq["trang_thai"], ("", kq["trang_thai"]))[1]
    await qa.edit(content=f"{bot_cong_viec.dau_tin(job)} · máy **{ten}**\n{chu}", view=None)   # go nut Dung
    f = bot_cong_viec.file_report(kq, out)
    if not job.get("da_bao"):
        # Tom tat ID ads doc bang code (dung package, ghi trong luot nay), khong theo chu Claude viet.
        # Trang audit day du nam trong tab cua chinh report -> chi dinh kem mot file report.
        audit = audit_tom_tat.tim(job["package"], tu_luc=job.get("bat_dau") or 0)
        files = [discord.File(f)] if f else []
        await qa.reply((bot_cong_viec.tin_ket_qua(job, kq, f) + f"\nMáy: {ten}\n{audit_tom_tat.dong_tin(audit)}")[:2000],
                       files=files or discord.utils.MISSING,
                       view=nut(("verify", "Verify bug Jira", XAM), msg_id=job["msg_id"]))
        bot.q.cap_nhat(job, da_bao=True)
    if kq.get("bugs") and not job.get("da_bao_bug"):
        # Luu vao tin cua build: bot khoi dong lai van tick / log tiep duoc.
        c = {**(bot.q.tin_cua(job["msg_id"]) or job), "bugs": kq["bugs"], "bug_chon": [],
             # link_report la duong dan file chi khi file do thuc su duoc dinh kem (tin_bug ghi "đính kèm")
             "link_report": kq.get("link", "") if kq.get("link", "").startswith("https://") else str(f or ""),
             "jira": None}
        bot.q.nho_tin(c)
        # Chua publish duoc artifact -> dinh kem luon file report vao tin bug: QA phai mo duoc report
        # ngay tai tin can review, khong phai keo len tim tin ket qua.
        await qa.reply(bot_cong_viec.tin_bug(kq["bugs"], None, c), files=[discord.File(f)] if f else discord.utils.MISSING,
                       view=view_bug(kq["bugs"], [], job["msg_id"]))
        bot.q.cap_nhat(job, da_bao_bug=True)
