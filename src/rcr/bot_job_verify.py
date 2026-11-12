"""Luot bot tu verify bug dev da keo sang Reviewing: xep job (tin build moi / QA bam Verify lai)
roi chay tren may - cai build, chay lai dung cac case, PASS -> Done, FAIL -> To Do (kem comment).
Ten transition tuy workflow (Reviewing -> "Reject Issue"/Reopened, "Close Issue"/Closed): xem
`jira.DICH_PASS` / `jira.DICH_FAIL`.

Comment Jira truoc roi moi chuyen trang thai: chuyen loi thi bang chung van nam tren issue.
Truoc khi doi trang thai hoi lai Jira: issue ai do da keo khoi Reviewing trong luc chay thi bo.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import discord

from . import (bot_chay_claude, bot_cho_publish, bot_cong_viec, bot_dung_luot, bot_forum, bot_jira_marker, bot_kenh_project,
               bot_kiem_testvsl, bot_report_may_phu)
from . import bot_jira_rest as jira
from . import bot_tin_goc as tin_goc
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


async def xep(bot, c: dict, kenh, bam_tay: bool = False) -> str:
    """Tim bug bot da log cho app `c['ma']` dang Reviewing -> dang tin + xep job verify tren build `c`.
    `bam_tay` (QA bam nut Verify): lay ca bug chua Done nam ngoai Reviewing - dev nhieu khi chua keo bug
    sang Reviewing (bug con o Backlog) ma da day build fix (user chot 12/11/2026). Luong tu dong khi co
    build moi van chi Reviewing: dev chua bao fix thi khong tu chay lai.
    Tra cau tom tat (de tra loi QA bam nut)."""
    if not jira.bat(bot.jira_url, bot.jira_token):
        return "Bot chưa có JIRA_URL / JIRA_PERSONAL_TOKEN — tính năng verify đang tắt."
    khoa = (c.get("package", ""), c.get("version", ""))
    if khoa in _DANG_XEP or bot.q.trung({"package": khoa[0], "version": khoa[1], "loai_job": "verify"}):
        return "Lượt verify build này đã trong hàng đợi."
    _DANG_XEP.add(khoa)
    try:
        return await _xep(bot, c, kenh, bam_tay)
    finally:
        _DANG_XEP.discard(khoa)


async def _xep(bot, c: dict, kenh, bam_tay: bool = False) -> str:
    uv = await (_ung_vien_chua_xong(bot, c["ma"]) if bam_tay else _ung_vien(bot, c["ma"]))
    if not uv:
        return f"{c['ma']}: không có bug nào của bot " + ("chưa Done." if bam_tay else "đang Reviewing.")
    chay, bo = v.phan_loai(uv, c["loai_ban"], c.get("package", ""))
    job = {**{k: c.get(k, "") for k in TRUONG_BUILD}, "loai_job": "verify", "verify": chay,
           "bo_qua": [{**u, "ly_do": ly} for u, ly in bo]}
    dong_bo = [("bo", u, ly) for u, ly in bo]
    if not chay:
        await bot_forum.gui_goc(bot, job, v.tin_ket_qua(job, dong_bo), kenh.send)
        return f"{c['ma']}: {len(bo)} bug nhưng không case nào chạy lại tự động được."
    vm = await bot_forum.gui_goc(bot, job, v.tin_ket_qua(job, [("cho", u, "") for u in chay] + dong_bo), kenh.send)
    job["msg_id"] = vm.id
    job.update(bot_forum.kenh_cua(vm))
    bot.q.nho_tin(job)
    vi_tri = bot.q.them(job)
    await vm.edit(view=nut(vm.id, ("huy", "Huỷ")))    # QA bo luot dang cho (vd dev bao day nham ban)
    ngoai = [u["key"] for u in chay if not _o_reviewing(u)]
    them = f" (ngoài Reviewing: {', '.join(ngoai)})" if ngoai else ""
    return f"Đã xếp verify {len(chay)} bug của {c['ma']}{them} — vị trí {vi_tri} trong hàng đợi."


async def _ung_vien(bot, ma: str) -> list[dict]:
    """Bug Reviewing cua app `ma`: label `auto-qa` tren Jira (moi flow) + bug bot log theo state (chua co label)."""
    tu_jira = await asyncio.to_thread(jira.tim_auto_qa, bot.jira_url, bot.jira_token, ma)
    co = {i["key"] for i in tu_jira}
    cu = v.ung_vien(bot.q.tin, ma)
    can_hoi = [u["key"] for u in cu if u["key"] not in co]       # key tren Jira da chac chan Reviewing
    con = set(await asyncio.to_thread(jira.dang_reviewing, bot.jira_url, bot.jira_token, can_hoi)) if can_hoi else set()
    return bot_jira_marker.gop(tu_jira, [u for u in cu if u["key"] in co or u["key"] in con])


async def _ung_vien_chua_xong(bot, ma: str) -> list[dict]:
    """Moi bug bot da log cho app `ma` chua Done (Reviewing, Backlog, To Do...), kem `status` hien tai."""
    tu_jira = await asyncio.to_thread(jira.tim_auto_qa, bot.jira_url, bot.jira_token, ma, chua_xong=True)
    st = {i["key"]: i.get("status") or "Reviewing" for i in tu_jira}
    cu = v.ung_vien(bot.q.tin, ma)
    can_hoi = [u["key"] for u in cu if u["key"] not in st]
    if can_hoi:
        tt = await asyncio.to_thread(jira.trang_thai, bot.jira_url, bot.jira_token, can_hoi)
        st |= {k: t["ten"] for k, t in tt.items() if not t["xong"]}
    uv = bot_jira_marker.gop(tu_jira, [u for u in cu if u["key"] in st])
    return [{**u, "status": st[u["key"]]} for u in uv if u["key"] in st]


def _dev_bao_fix(u: dict) -> bool:
    """Resolved (dev bao fix, chua keo Reviewing): FAIL thi keo To Do nhu Reviewing."""
    return str(u.get("status") or "").casefold() == "resolved"


def _o_reviewing(u: dict) -> bool:
    return str(u.get("status") or "Reviewing").casefold() == "reviewing"


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


async def _con_nguyen_trang_thai(bot, verify: list[dict]) -> set[str]:
    """Key van o dung trang thai luc xep (khong ai keo trong luc chay)."""
    rv = [u["key"] for u in verify if _o_reviewing(u)]
    khac = {u["key"]: u["status"] for u in verify if not _o_reviewing(u)}
    con = set(await asyncio.to_thread(jira.dang_reviewing, bot.jira_url, bot.jira_token, rv)) if rv else set()
    if khac:
        tt = await asyncio.to_thread(jira.trang_thai, bot.jira_url, bot.jira_token, list(khac))
        con |= {k for k, t in tt.items() if t["ten"] == khac.get(k)}
    return con


async def _doi_trang_thai(bot, job: dict, kq: dict, ten: str) -> list[tuple[str, dict, str]]:
    try:
        con = await _con_nguyen_trang_thai(bot, job["verify"])
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
        rv = _o_reviewing(u)
        # Bug ngoai Reviewing (Backlog / To Do) ma FAIL: van mo san, chi comment, khong chuyen trang thai.
        # Resolved (dev bao da fix) ma FAIL thi keo ve To Do nhu Reviewing.
        giu = "" if rv or kl == "PASS" or _dev_bao_fix(u) else u["status"]
        try:
            chu = v.noi_dung_comment(u, kl, job, kq, ten, giu)
            # Lan truoc comment xong nhung chuyen loi -> Verify lai khong comment trung.
            if not await asyncio.to_thread(jira.da_comment, bot.jira_url, bot.jira_token, u["key"],
                                           chu.split("\n", 1)[0]):
                await asyncio.to_thread(jira.comment, bot.jira_url, bot.jira_token, u["key"], chu)
            if giu:
                dong.append(("vanloi", u, f"giữ {giu}"))
                continue
            await asyncio.to_thread(jira.chuyen, bot.jira_url, bot.jira_token, u["key"],
                                    jira.DICH_PASS if kl == "PASS" else jira.DICH_FAIL)
            dong.append(("done" if kl == "PASS" else "todo", u, "" if rv else f"từ {u['status']}"))
        except Exception as exc:               # noqa: BLE001 - mot issue loi khong chan issue sau
            log.warning("verify %s: %s", u["key"], exc)
            dong.append(("giu", u, f"Jira lỗi: {exc}"))
    return dong


async def chay(bot, job: dict, serial: str, ten: str, repo: Path, out: Path) -> None:
    vm = await bot._tin_qa(job["msg_id"])
    # Co kq = da chay xong, lan truoc gui ket qua loi mang (bot_gui_lai) -> chi gui lai, khong cai / chay lai.
    if job.get("kq") is None and not await _cai_va_chay(bot, job, vm, serial, ten, repo, out):
        return
    await _bao_ket_qua(bot, job, vm, out)


async def _cai_va_chay(bot, job: dict, vm, serial: str, ten: str, repo: Path, out: Path) -> bool:
    moi = _build_moi_hon(bot, job)
    if moi:
        # Fix thuong chi co o build moi: verify build cu co the keo To Do truoc khi build moi kip chay.
        await vm.edit(content=f"{v.tin_ket_qua(job, [])}\n⏭ Bỏ — đã có build mới hơn `{moi}` chờ verify.", view=None)
        return False
    dau = f"{v.tin_ket_qua(job, [])} · máy **{ten}**"
    await vm.edit(content=f"{dau}\nĐang cài bản {job['loai_ban']} từ App Tester…",
                  view=bot_dung_luot.view_dung(vm.id))   # thay nut Huy bang nut Dung
    cai = await asyncio.to_thread(bot_cong_viec.cai, job["package"], job["version"], job["loai_ban"], serial)
    if "loi" in cai:
        await vm.edit(content=f"{dau}\n⛔ Cài không được: {cai['loi']}",
                      view=nut(vm.id, ("check", "Thử lại")))
        return False
    cases = sorted({u["case"] for u in job["verify"]})
    loai = v.loai_case(cases[0])                     # phan_loai chi cho qua mot nhom moi luot
    ck, sub = loai == "checklist", loai == "sub"
    if not sub and bot_kiem_testvsl.doi_rc_firebase(job, ck):    # sub khong doi Remote Config
        loi = await bot_kiem_testvsl.loi_testvsl(serial, job["package"])
        if loi:                              # chua co / sai testvsl: nhac QA tao, khong chay, khong dung Jira / Firebase
            await vm.edit(content=tin_goc.noi(f"{dau}\n📲 Đã cài.",
                                              bot_kiem_testvsl.tin_nhac(job, loi, getattr(bot, "duyet", ()))),
                          view=nut(vm.id, ("verify", "Verify lại")))
            return False
    het_gio = (bot_chay_claude.TIMEOUT_VERIFY_SUB if sub else
               bot_chay_claude.TIMEOUT_VERIFY_CHECKLIST if ck else bot_chay_claude.TIMEOUT_VERIFY)
    if not sub:
        bot_dung_luot.danh_dau_pha_rc(job, ck)        # Dung tu day -> phai don RC testvsl
    await vm.edit(content=f"{dau}\n📲 Đã cài. Đang chạy lại {len(cases)} {'dòng checklist' if ck else 'case'}…")
    kq = await asyncio.to_thread(bot_chay_claude.chay, job["package"], serial, repo, het_gio, out, cases)
    bot.q.cap_nhat(job, kq=kq, ten_may=ten)
    return True


async def _bao_ket_qua(bot, job: dict, vm, out: Path) -> None:
    """Doi trang thai Jira roi bao. Goi lai duoc nhieu lan (mat mang giua chung): buoc nao xong roi thi bo."""
    kq, ten = job["kq"], job.get("ten_may") or "?"
    if job.get("dong") is None:              # Jira chi doi mot lan, ket qua luu cung job
        dong = await _doi_trang_thai(bot, job, kq, ten)
        dong += [("bo", u, u.get("ly_do", "")) for u in job.get("bo_qua", [])]
        bot.q.cap_nhat(job, dong=[list(d) for d in dong])
    dong = [tuple(d) for d in job["dong"]]
    f = bot_cong_viec.file_report(kq, out)
    noi_dung = {"content": tin_goc.noi(v.tin_ket_qua(job, dong), f"Máy: {ten}"),
                "view": nut(vm.id, ("verify", "Verify bug Jira"))}
    if not job.get("da_bao"):
        # Tom tat + file report nam ngay tren tin goc cua luot verify (khong tra loi tin moi - bot_tin_goc).
        # Chua co artifact -> dong CHO, phien publish thay bang link (khong dinh kem HTML - user 10-11/11/2026).
        link = f"\n{bot_cho_publish.CHO}" if f else (f"\nReport: {kq['link']}" if kq.get("link") else "")
        noi_dung |= {"embeds": [tin_goc.embed(tin_goc.KET_QUA, f"{v.tin_tom_tat_verify(job, kq)}{link}")],
                     "attachments": []}
    await vm.edit(**noi_dung)
    if f and not job.get("da_bao"):
        khoa = f"{job.get('ma', '')} {job.get('version', '')}".strip()
        await bot_report_may_phu.them(bot, out, f, vm.channel.id, vm.id, khoa, khoa)   # may phu -> bot chinh
    bot.q.cap_nhat(job, da_bao=True)
    if not job.get("da_ping"):
        await tin_goc.ping_xong(bot, vm, f"🔔 Verify **{job['ma']}** `{job['version']}` xong (xem tin gốc).")
        bot.q.cap_nhat(job, da_ping=True)
    tin_dev = v.tin_bao_dev_fail(job, dong)
    if tin_dev and not job.get("da_bao_dev"):   # bug van FAIL -> bao dev o kenh project
        await bot_kenh_project.bao(bot, job, tin_dev, vm, [u["key"] for loai, u, _ in dong if loai == "todo"])
        bot.q.cap_nhat(job, da_bao_dev=True)
