"""Chia luot test cho may tinh phu (vd Ubuntu) - mot bot chinh nhan tin, cac may phu chi chay job.

User chot 30/10/2026: chay bot o ca Windows lan Ubuntu ma khong trung. Hai tien trinh cung token bot nen Discord
gui moi su kien cho ca hai; chi bot CHINH (`RCR_VAI_TRO` rong / `chinh`) doc tin build, hoi QA, xu ly nut bam va
giu hang doi. May PHU (`RCR_VAI_TRO=phu`, ten `RCR_TEN_MAY`) bo qua moi tin / nut, chi noi chuyen voi bot chinh qua
kenh dieu phoi rieng (`DISCORD_DIEU_PHOI_CHANNEL_ID`) bang tin `RCR <loai> <may>` kem file JSON:

  chinh -> phu  `chinh_khoi_dong`  bot chinh vua bat, mat yeu cau xin viec dang cho -> may phu xin lai ngay
  phu -> chinh  `khoi_dong`  may phu vua bat: job dang giao cho no (chet giua luot) tra ve hang de chay lai
  phu -> chinh  `xin`        may test <serial> cua may phu dang ranh, xin mot job
  chinh -> phu  `giao`       job + tin cua build + anh hang doi (verify can biet build moi hon)
  phu -> chinh  `tra`        nhan job nhung may test vua ban / rut cap -> tra lai hang
  phu -> chinh  `xong`       chay xong; kem tin build sau luot (danh sach bug de QA tick o bot chinh)
  chinh -> phu  `dung`       QA bam Dung luot dang chay o may phu -> may phu giet ca cay tien trinh + don RC

May phu chay job bang dung code cua bot chinh (`_chay_tren`): cung token nen sua / tra loi duoc tin cua bot o kenh
QA, nut bam no gui van ve bot chinh xu ly. Job dang o may phu ghi `dang_o` trong hang doi (luu file) -> bot chinh
khoi dong lai khong giao trung.
"""

from __future__ import annotations

import asyncio
import io
import json
import logging
import time
from datetime import datetime, timezone

import discord

from . import bot_canh_may, bot_chay_claude, bot_cong_viec, bot_gui_lai, bot_hang_doi, bot_tien_trinh

log = logging.getLogger("rcr-bot")
TIEN_TO = "RCR"
# Xin roi ma chua duoc giao: bot chinh van nho yeu cau (hang trong thi cho), ca hai lan lo tin da co
# `chinh_khoi_dong` moi lan bot chinh ket noi phien moi. Xin lai dinh ky chi la luoi an toan -> thua, tranh spam.
XIN_LAI = 2 * 3600
NHIP = 10
SO_LAN_GUI_XONG = 10
# May phu tat han giua luot thi khong bao gi gui `khoi_dong` / `xong` -> job dung "dang chay" mai. Qua han nay
# (luot dai nhat + cai + du phong; may phu chi gui lai ket qua toi da bot_gui_lai.HAN_GUI_LAI_MAY_PHU, nam trong
# phan du phong) thi may phu chac chan da thoi chay lan gui -> thu hoi, khong chay trung.
HAN_MAY_PHU = (max(bot_chay_claude.TIMEOUT_BO_TC, bot_chay_claude.TIMEOUT_NEXT_GEN,
                   bot_chay_claude.TIMEOUT_VERIFY_CHECKLIST) + bot_cong_viec.TIMEOUT_CAI + 15 * 60)


async def gui(kenh, loai: str, du_lieu: dict) -> None:
    """JSON di bang file dinh kem: job verify / tin co danh sach bug de vuot 2000 ky tu."""
    raw = json.dumps(du_lieu, ensure_ascii=False).encode("utf-8")
    await kenh.send(f"{TIEN_TO} {loai} {du_lieu.get('may', '')}", file=discord.File(io.BytesIO(raw), "rcr.json"))


async def doc(m) -> tuple[str, dict] | None:
    phan = (m.content or "").split()
    if len(phan) < 2 or phan[0] != TIEN_TO or not m.attachments:
        return None
    return phan[1], json.loads(await m.attachments[0].read())


# --- bot chinh ---------------------------------------------------------------------------
def tra_ve_hang(bot, may: str) -> int:
    """Bo `dang_o` cua moi job dang giao cho `may` -> job chay lai tu dau o may ranh dau tien."""
    so = 0
    for j in bot.q.jobs:
        if str(j.get("dang_o", "")).startswith(f"{may}:"):
            j.pop("dang_o")
            bot.q.dang_chay.discard(j["msg_id"])
            so += 1
    bot.q.luu()
    return so


async def _tin_xong_bi_lo(kenh, job: dict) -> dict | None:
    """Tin `RCR xong` cua job o kenh dieu phoi tu luc giao. Tin den luc bot chinh dang khoi dong lai thi
    Discord khong phat lai -> doc lich su kenh truoc khi ket luan may phu da chet."""
    tu = datetime.fromtimestamp(job["giao_luc"], tz=timezone.utc)
    async for m in kenh.history(after=tu, limit=500):
        if not (m.content or "").startswith(f"{TIEN_TO} xong"):
            continue
        goi = await doc(m)
        if goi and goi[1].get("msg_id") == job["msg_id"]:
            return goi[1]
    return None


async def thu_hoi_job_treo(bot, kenh, bay_gio: float | None = None) -> list[dict]:
    """Job giao cho may phu qua `HAN_MAY_PHU` ma chua `xong` -> ve hang (chay lai o may ranh). Tra cac job
    da thu hoi de bot bao QA. Job giao tu ban cu (chua co `giao_luc`) tinh han tu luc nay."""
    bay_gio = time.time() if bay_gio is None else bay_gio
    thu, doi = [], False
    for j in list(bot.q.jobs):
        if not j.get("dang_o"):
            continue
        if "giao_luc" not in j:
            j["giao_luc"], doi = bay_gio, True
        elif bay_gio - j["giao_luc"] > HAN_MAY_PHU:
            xong = await _tin_xong_bi_lo(kenh, j)
            if xong is not None:             # may phu da xong, chi la tin bi lo
                log.info("tin xong bi lo cua %s %s: danh dau xong", j.get("ma"), j.get("version"))
                nhan_o_may_chinh(bot, "xong", xong)
                continue
            log.warning("may phu %s im qua han voi %s %s: thu hoi job", j["dang_o"], j.get("ma"), j.get("version"))
            thu.append({**j})
            j.pop("dang_o")
            j.pop("giao_luc")
            bot.q.dang_chay.discard(j["msg_id"])
            doi = True
    if doi:
        bot.q.luu()
    return thu


def nhan_o_may_chinh(bot, loai: str, d: dict) -> None:
    may = str(d.get("may") or "")
    if not may:
        return
    if loai == "khoi_dong":
        bot.xin_cho = {k: v for k, v in bot.xin_cho.items() if k[0] != may}
        log.info("may phu %s khoi dong: tra %d job ve hang", may, tra_ve_hang(bot, may))
    elif loai == "xin":
        bot.xin_cho[(may, str(d["serial"]))] = str(d.get("ten") or d["serial"])
    elif loai in ("xong", "tra"):
        # Chi nhan khi job con dang giao cho chinh may nay: job da bi thu hoi (thu_hoi_job_treo) roi chay lai o
        # may khac thi tin den muon khong duoc xoa job dang chay / ghi de tin cua luot moi.
        job = next((j for j in bot.q.jobs if j["msg_id"] == d.get("msg_id")
                    and str(j.get("dang_o", "")).startswith(f"{may}:")), None)
        if job is None:
            return
        if loai == "xong" and d.get("tin"):
            bot.q.nho_tin(d["tin"])
        if loai == "xong":
            bot.q.xong(job)
        else:
            job.pop("dang_o", None)
            bot.q.dang_chay.discard(job["msg_id"])
            bot.q.luu()


async def chia_viec(bot, kenh) -> None:
    """Moi nhip cua vong worker bot chinh: yeu cau xin viec cu nhat lay job dau hang."""
    for khoa in list(bot.xin_cho):
        job = bot.q.lay()
        if job is None:
            return
        may, serial = khoa
        ten = bot.xin_cho.pop(khoa)
        job["dang_o"], job["giao_luc"] = f"{may}:{serial}", time.time()
        bot.q.luu()
        try:
            await gui(kenh, "giao", {"may": may, "serial": serial, "ten": ten, "job": job,
                                     "tin": bot.q.tin_cua(job["msg_id"]), "jobs": bot.q.jobs})
            log.info("giao %s %s cho %s:%s", job.get("ma"), job.get("version"), may, serial)
        except discord.HTTPException as exc:      # chua gui duoc -> job ve hang, may phu se xin lai
            log.warning("khong giao duoc job cho %s: %s", may, exc)
            job.pop("dang_o", None)
            bot.q.dang_chay.discard(job["msg_id"])
            bot.q.luu()


# --- may phu ------------------------------------------------------------------------------
async def nhan_o_may_phu(bot, loai: str, d: dict, kenh) -> None:
    if loai == "chinh_khoi_dong":
        bot.da_xin.clear()
        return
    if loai == "dung" and d.get("may") == bot.ten_may:   # QA bam Dung o bot chinh, luot dang chay o may nay
        serial = str(d.get("serial") or "")
        if bot.ban.get(serial) == d.get("msg_id"):
            await asyncio.to_thread(bot_tien_trinh.dung, serial, str(d.get("ly_do") or ""), d.get("msg_id"))
        return
    if loai != "giao" or d.get("may") != bot.ten_may:
        return
    serial, job = str(d["serial"]), d["job"]
    bot.da_xin.pop(serial, None)
    if (serial not in bot.may_san or serial in bot.ban
            or bot_hang_doi.may_ban(bot_hang_doi.khoa_may(bot.out, serial))):   # rut cap / ban tu luc xin
        await gui(kenh, "tra", {"may": bot.ten_may, "msg_id": job["msg_id"]})
        return
    bot.ban[serial] = job["msg_id"]
    # Hang doi cuc bo chi de code job dung chung doc: tin cua build + anh hang doi bot chinh luc giao.
    bot.q.jobs = d.get("jobs") or [job]
    if d.get("tin"):
        bot.q.tin[str(job["msg_id"])] = d["tin"]
    bot.q.dang_chay.add(job["msg_id"])
    asyncio.create_task(_chay_job(bot, job, serial, f"{d.get('ten') or serial} @{bot.ten_may}", kenh))


async def _chay_job(bot, job: dict, serial: str, ten: str, kenh) -> None:
    truoc = json.dumps(bot.q.tin_cua(job["msg_id"]), sort_keys=True, ensure_ascii=False)
    try:
        await bot._chay_tren(job, serial, ten)        # finally ben trong tra may (bot.ban) + xong hang cuc bo
    finally:
        sau = bot.q.tin_cua(job["msg_id"])
        doi = json.dumps(sau, sort_keys=True, ensure_ascii=False) != truoc
        for lan in range(SO_LAN_GUI_XONG):   # mat tin xong -> bot chinh doi HAN_MAY_PHU roi moi biet
            try:
                await gui(kenh, "xong", {"may": bot.ten_may, "msg_id": job["msg_id"], "tin": sau if doi else None})
                break
            except bot_gui_lai.LOI_MANG as exc:
                log.warning("chua gui duoc tin xong (lan %d): %s", lan + 1, exc)
                await asyncio.sleep(bot_gui_lai.CHO_GUI_LAI)


async def vong_may_phu(bot, kenh, danh_sach_may) -> None:
    """May test cam vao may phu, ranh, chua co yeu cau dang cho -> xin job. `danh_sach_may()`: may ready."""
    await gui(kenh, "khoi_dong", {"may": bot.ten_may})
    while not bot.is_closed():
        try:
            may = await danh_sach_may()
            bot.may_san = {d.serial for d in may}
            await bot_canh_may.kiem(bot, bot.may_san)   # may dang chay luot mat ket noi qua han -> tu dung
            for d in may:
                if d.serial in bot.ban or bot_hang_doi.may_ban(bot_hang_doi.khoa_may(bot.out, d.serial)):
                    bot.da_xin.pop(d.serial, None)
                elif time.time() - bot.da_xin.get(d.serial, 0) > XIN_LAI:
                    await gui(kenh, "xin", {"may": bot.ten_may, "serial": d.serial,
                                            "ten": bot_cong_viec.ten_may(d.serial, d.model)})
                    bot.da_xin[d.serial] = time.time()
        except Exception as exc:                  # noqa: BLE001 - adb / Discord loi: nhip sau thu lai
            log.warning("may phu xin viec loi: %s", exc)
        await asyncio.sleep(NHIP)
