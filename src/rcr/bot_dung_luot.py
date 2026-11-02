"""QA bam **Dung** o tin cua luot dang chay: giet ca cay tien trinh (bot_tien_trinh) roi don Remote Config.

Luot bo TC tren ban release gan gia tri RC duoi dieu kien `testvsl` tren Firebase (rc_firebase) - giet ngang co the
de lai gia tri do. Dung o buoc chay test -> keo APK tu may lay Firebase project roi `tra_het` (go moi gia tri cua
`testvsl`, cung ham tool dung don luot chet giua chung; khong dung default / tham so nguoi khac). Nhanh checklist
Next-Gen va ban debug khong doi RC tren Firebase -> khong don. Dung luc dang cai -> chua dung RC, khong don.

Job dang o may phu: bot chinh chuyen lenh `dung` qua kenh dieu phoi; may phu giet + don tren may test cua no.
"""

from __future__ import annotations

import asyncio
import logging

import discord

from . import bot_cong_viec, bot_may_phu, bot_tien_trinh, bot_verify_jira, rc_firebase_app
from .adb_client import AdbClient

log = logging.getLogger("rcr-bot")
PHA_RC = "rc"     # job["pha"]: dang chay test co the gan RC testvsl (ban release, nhanh bo TC)


def view_dung(msg_id: int) -> discord.ui.View:
    v = discord.ui.View(timeout=None)
    v.add_item(discord.ui.Button(label="Dừng", style=discord.ButtonStyle.danger, custom_id=f"rcr:dung:{msg_id}"))
    return v


def danh_dau_pha_rc(job: dict, next_gen_hay_checklist: bool) -> None:
    """Goi ngay truoc khi chay Claude: luot nay co the gan RC `testvsl` khong (de biet co can don khi Dung)."""
    if job.get("loai_ban") == "release" and not job.get("drive") and not next_gen_hay_checklist:
        job["pha"] = PHA_RC


async def bam_dung(bot, it: discord.Interaction, c: dict) -> None:
    job = next((j for j in bot.q.jobs if j["msg_id"] == c["msg_id"]), None)
    if job is None or job.get("kq") is not None:
        await it.response.send_message("Lượt này không còn chạy (đã xong / đang gửi kết quả).", ephemeral=True)
        return
    ly_do = f"{it.user.mention} bấm Dừng"
    await it.response.defer(ephemeral=True, thinking=True)
    if job.get("dang_o"):
        may, serial = str(job["dang_o"]).split(":", 1)
        await bot_may_phu.gui(await bot._kenh_dieu_phoi(), "dung",
                              {"may": may, "serial": serial, "msg_id": job["msg_id"], "ly_do": ly_do})
        await it.followup.send(f"🛑 Đã gửi lệnh dừng tới máy phụ `{may}`.", ephemeral=True)
        return
    serial = next((s for s, m in bot.ban.items() if m == job["msg_id"]), None)
    if serial is None:
        await it.followup.send("Lượt chưa bắt đầu chạy — bấm **Huỷ** để bỏ khỏi hàng đợi.", ephemeral=True)
        return
    if await asyncio.to_thread(bot_tien_trinh.dung, serial, ly_do, job["msg_id"]):
        await it.followup.send("🛑 Đang dừng lượt…", ephemeral=True)
    else:
        await it.followup.send("Lượt này vừa xong trên máy, không còn gì để dừng.", ephemeral=True)


def _luot_khac_cung_app(bot, job: dict) -> bool:
    """Luot khac cua cung package dang chay (Check + verify cung build, may chinh + may phu): `tra_het` go MOI gia
    tri `testvsl` cua project -> se xoa gia tri luot kia dang dung giua case."""
    return any(j["msg_id"] != job["msg_id"] and j.get("package") == job.get("package")
               and (j["msg_id"] in bot.q.dang_chay or j.get("dang_o")) for j in bot.q.jobs)


async def _don_rc(bot, job: dict, serial: str) -> str:
    """Go gia tri `testvsl` luot vua dung co the de lai. Tra dong ghi them vao tin cua luot."""
    if _luot_khac_cung_app(bot, job):
        return ("\n⚠️ Chưa gỡ giá trị `testvsl`: đang có lượt khác của cùng app chạy trên máy khác (gỡ sẽ làm hỏng "
                "lượt đó). Lượt đó xong / lượt sau tự dọn khi đọc baseline — QA cần sạch ngay thì gỡ tay trên Firebase.")
    try:
        project = await rc_firebase_app.don_testvsl(AdbClient(), serial, job["package"])
        return f"\nĐã gỡ giá trị điều kiện `testvsl` trên Firebase `{project}`."
    except Exception as exc:                 # noqa: BLE001 - van phai bao QA
        log.warning("don testvsl sau khi dung loi: %s", exc)
        return f"\n⚠️ Chưa gỡ được giá trị `testvsl` ({exc}) — QA kiểm tra điều kiện `testvsl` trên Firebase."


async def sau_khi_dung(bot, job: dict, serial: str, ten: str, ly_do: str) -> None:
    """Luot da bi giet: bao o tin cua luot, don RC neu can, tra nut de chay lai."""
    verify = job.get("loai_job") == "verify"
    dau = (bot_verify_jira.tin_ket_qua(job, []) if verify else bot_cong_viec.dau_tin(job)) + f" · máy **{ten}**"
    # Don Firebase TRUOC khi dung toi Discord: mat mang Discord khong duoc lam bo qua buoc don.
    ghi = await _don_rc(bot, job, serial) if job.get("pha") == PHA_RC else ""
    msg = await bot._tin_qa(job["msg_id"])
    v = discord.ui.View(timeout=None)
    for hanh_dong, nhan in ((("verify", "Verify lại"),) if verify else (("check", "Chạy lại"), ("bo", "Bỏ qua"))):
        v.add_item(discord.ui.Button(label=nhan, style=discord.ButtonStyle.secondary,
                                     custom_id=f"rcr:{hanh_dong}:{job['msg_id']}"))
    await msg.edit(content=f"{dau}\n🛑 Đã dừng — {ly_do}.{ghi}", view=v)
