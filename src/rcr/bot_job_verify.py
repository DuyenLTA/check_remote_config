"""Luot bot tu verify bug dev da keo sang Reviewing: xep job (tin build moi / QA bam Verify lai)
roi chay tren may - cai build, chay lai dung cac case, PASS -> Done, FAIL -> To Do (kem comment).

Comment Jira truoc roi moi chuyen trang thai: chuyen loi thi bang chung van nam tren issue.
Truoc khi doi trang thai hoi lai Jira: issue ai do da keo khoi Reviewing trong luc chay thi bo.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import discord

from . import bot_chay_claude, bot_cong_viec, bot_jira_marker, bot_kenh_project
from . import bot_jira_rest as jira
from . import bot_verify_jira as v

log = logging.getLogger("rcr-bot")
TRUONG_BUILD = ("ma", "ten", "version", "package", "loai_ban", "link_tin")
# Build dang duoc xep (giua cac await cua `xep`): tin build den hai kenh / QA bam Verify lai cung luc
# -> lan sau thay ngay, khong gui tin "Cho chay" thua.
_DANG_XEP: set[tuple[str, str]] = set()


def nut(msg_id: int, *cac: tuple[str, str]) -> discord.ui.View:
    view = discord.ui.View(timeout=None)
    for hanh_dong, nhan in cac:
        view.add_item(discord.ui.Button(label=nhan, style=discord.ButtonStyle.secondary,
                                        custom_id=f"rcr:{hanh_dong}:{msg_id}"))
    return view


async def xep(bot, c: dict, kenh) -> str:
    """Tim bug bot da log cho app `c['ma']` dang Reviewing -> dang tin + xep job verify tren build `c`.
    Tra cau tom tat (de tra loi QA bam nut)."""
    if not jira.bat(bot.jira_url, bot.jira_token):
        return "Bot chưa có JIRA_URL / JIRA_PERSONAL_TOKEN — tính năng verify đang tắt."
    khoa = (c.get("package", ""), c.get("version", ""))
    if khoa in _DANG_XEP or bot.q.trung({"package": khoa[0], "version": khoa[1], "loai_job": "verify"}):
        return "Lượt verify build này đã trong hàng đợi."
    _DANG_XEP.add(khoa)
    try:
        return await _xep(bot, c, kenh)
    finally:
        _DANG_XEP.discard(khoa)


async def _xep(bot, c: dict, kenh) -> str:
    uv = await _ung_vien(bot, c["ma"])
    if not uv:
        return f"{c['ma']}: không có bug nào của bot đang Reviewing."
    chay, bo = v.phan_loai(uv, c["loai_ban"], c.get("package", ""))
    job = {**{k: c.get(k, "") for k in TRUONG_BUILD}, "loai_job": "verify", "verify": chay,
           "bo_qua": [{**u, "ly_do": ly} for u, ly in bo]}
    dong_bo = [("bo", u, ly) for u, ly in bo]
    if not chay:
        await kenh.send(v.tin_ket_qua(job, dong_bo))
        return f"{c['ma']}: {len(bo)} bug Reviewing nhưng không case nào chạy lại tự động được."
    vm = await kenh.send(v.tin_ket_qua(job, [("cho", u, "") for u in chay] + dong_bo))
    job["msg_id"] = vm.id
    bot.q.nho_tin(job)
    vi_tri = bot.q.them(job)
    return f"Đã xếp verify {len(chay)} bug Reviewing của {c['ma']} — vị trí {vi_tri} trong hàng đợi."


async def _ung_vien(bot, ma: str) -> list[dict]:
    """Bug Reviewing cua app `ma`: label `auto-qa` tren Jira (moi flow) + bug bot log theo state (chua co label)."""
    tu_jira = await asyncio.to_thread(jira.tim_auto_qa, bot.jira_url, bot.jira_token, ma)
    co = {i["key"] for i in tu_jira}
    cu = v.ung_vien(bot.q.tin, ma)
    can_hoi = [u["key"] for u in cu if u["key"] not in co]       # key tren Jira da chac chan Reviewing
    con = set(await asyncio.to_thread(jira.dang_reviewing, bot.jira_url, bot.jira_token, can_hoi)) if can_hoi else set()
    return bot_jira_marker.gop(tu_jira, [u for u in cu if u["key"] in co or u["key"] in con])


def _build_moi_hon(bot, job: dict) -> str:
    """Version cua job verify cung package xep SAU job nay (build dev bao sau), khong co thi ""."""
    sau = False
    for j in bot.q.jobs:
        if j.get("msg_id") == job["msg_id"]:
            sau = True
        elif sau and j.get("loai_job") == "verify" and j.get("package") == job["package"]:
            return j.get("version", "")
    return ""


def _ly_do_giu(kq: dict, u: dict) -> str:
    if kq.get("trang_thai") != "XONG":
        return f"lượt {kq.get('trang_thai')}: {kq.get('tom_tat', '')}"
    vd = next((c.get("verdict") for c in kq.get("cases") or [] if c.get("case") == u["case"]), "")
    return f"verdict {vd}" if vd else "Claude không trả verdict cho case này"


async def _doi_trang_thai(bot, job: dict, kq: dict, ten: str) -> list[tuple[str, dict, str]]:
    keys = [u["key"] for u in job["verify"]]
    try:
        con = set(await asyncio.to_thread(jira.dang_reviewing, bot.jira_url, bot.jira_token, keys))
    except jira.JiraLoi as exc:
        return [("giu", u, f"không đọc được Jira: {exc}") for u in job["verify"]]
    dong = []
    for u in job["verify"]:
        if u["key"] not in con:
            dong.append(("bo", u, "đã đổi trạng thái trong lúc chạy"))
            continue
        kl = v.ket_luan(kq, u)
        if kl is None:
            dong.append(("giu", u, _ly_do_giu(kq, u)))
            continue
        try:
            await asyncio.to_thread(jira.comment, bot.jira_url, bot.jira_token, u["key"],
                                    v.noi_dung_comment(u, kl, job, kq, ten))
            await asyncio.to_thread(jira.chuyen, bot.jira_url, bot.jira_token, u["key"],
                                    "Done" if kl == "PASS" else "To Do")
            dong.append(("done" if kl == "PASS" else "todo", u, ""))
        except Exception as exc:               # noqa: BLE001 - mot issue loi khong chan issue sau
            log.warning("verify %s: %s", u["key"], exc)
            dong.append(("giu", u, f"Jira lỗi: {exc}"))
    return dong


async def chay(bot, job: dict, serial: str, ten: str, repo: Path, out: Path) -> None:
    vm = await bot._tin_qa(job["msg_id"])
    moi = _build_moi_hon(bot, job)
    if moi:
        # Fix thuong chi co o build moi: verify build cu co the keo To Do truoc khi build moi kip chay.
        await vm.edit(content=f"{v.tin_ket_qua(job, [])}\n⏭ Bỏ — đã có build mới hơn `{moi}` chờ verify.")
        return
    dau = f"{v.tin_ket_qua(job, [])} · máy **{ten}**"
    await vm.edit(content=f"{dau}\nĐang cài bản {job['loai_ban']} từ App Tester…")
    cai = await asyncio.to_thread(bot_cong_viec.cai, job["package"], job["version"], job["loai_ban"], serial)
    if "loi" in cai:
        await vm.edit(content=f"{dau}\n⛔ Cài không được: {cai['loi']}", view=nut(vm.id, ("check", "Thử lại")))
        return
    cases = sorted({u["case"] for u in job["verify"]})
    ck = v.loai_case(cases[0]) == "checklist"        # phan_loai chi cho qua mot nhom moi luot
    het_gio = bot_chay_claude.TIMEOUT_VERIFY_CHECKLIST if ck else bot_chay_claude.TIMEOUT_VERIFY
    await vm.edit(content=f"{dau}\nĐang chạy lại {len(cases)} {'dòng checklist' if ck else 'case'}…")
    kq = await asyncio.to_thread(bot_chay_claude.chay, job["package"], serial, repo, het_gio, out, cases)
    dong = await _doi_trang_thai(bot, job, kq, ten)
    dong += [("bo", u, u.get("ly_do", "")) for u in job.get("bo_qua", [])]
    await vm.edit(content=f"{v.tin_ket_qua(job, dong)}\nMáy: {ten}", view=nut(vm.id, ("verify", "Verify bug Jira")))
    f = bot_cong_viec.file_report(kq, out)
    link = f"\nReport: {kq['link']}" if kq.get("link") and not f else ""
    await vm.reply(f"{kq.get('tom_tat', '')[:1500]}{link}", file=discord.File(f) if f else discord.utils.MISSING)
    tin_dev = v.tin_bao_dev_fail(job, dong)
    if tin_dev:                              # bug van FAIL -> bao dev o kenh project
        await bot_kenh_project.bao(bot, job, tin_dev, vm)
