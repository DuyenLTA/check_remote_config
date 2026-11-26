"""Bot va condition `testvsl` tren Firebase: nhac xoa khi QA bao test pass, tao theo dung version.

User chot 20/11/2026:
- QA bao "test pass" o kenh project (tin build cua nhom) -> condition `testvsl` do tai khoan bot (QA chu bot) tao
  thi bot TU XOA roi bao "da xoa" vao kenh `condition_fb` (khong thay thi qa-auto) - doi 26/11/2026, truoc la tin
  nhac kem nut. Khong tu xoa duoc (dang co luot chay app, Firebase loi) thi tin kem nut Xoa de thu lai.
  Condition nguoi khac tao thi chi bao, khong xoa.
- Cung luc do xoa moi bai Forum `qa-builds` cua app (moi version), tru bai cua build con trong hang doi / dang chay:
  app pass roi thi bai cu chi lam roi Forum (user chot 20/11/2026).
- Tao condition theo version tin build (lech plan tuan thi chua ca version plan): lenh `/testvsl`, nut tren tin nhac
  thieu / sai testvsl cua luot, va tu dong khi QA bam Check (`bot_kiem_testvsl.tu_tao`).
Moi thao tac Firebase o `rc_firebase_testvsl` (chot chan chi dong vao `testvsl`).
"""

from __future__ import annotations

import asyncio
import logging
import re
from pathlib import Path

import discord
from discord import app_commands

from . import bot_cong_viec, bot_lenh_xoa_bai, build_ma_app
from . import rc_firebase_testvsl as tv
from .bot_giao_dien import XAM, noi_dung, nut
from .models import RcError

log = logging.getLogger("rcr-bot")
OUT = Path(__file__).resolve().parents[2] / "out"
LOAI = "testvsl"              # tin nhac xoa luu trong bot.q.tin (khong co "ma"/"version" o ngoai: khong lan tin build)
XOA, TAO = "xoatestvsl", "taotestvsl"
KENH_CONDITION = "condition_fb"   # kenh nhan tin nhac xoa testvsl (tim theo ten trong server cua bot)
PASS_RE = re.compile(r"(?<![\w-])(?:test(?:ed)?\s*)?pass(?:ed)?(?![\w-])", re.I)
# "chua pass", "not pass", "fail" ... -> khong phai bao pass
CHUA_PASS_RE = re.compile(r"(?:chưa|chua|không|khong|ko|k|not|no|đéo|deo)\s+(?:test\s*)?pass|\bfail", re.I)


def la_tin_pass(text: str) -> bool:
    return bool(PASS_RE.search(text or "")) and not CHUA_PASS_RE.search(text or "")


def _job_dang_test(bot, package: str) -> bool:
    """Co luot dang cai / chay tren may cho package nay (dang dung testvsl) -> chua xoa."""
    return any(j.get("package") == package and bot.q._dang_test(j) for j in bot.q.jobs)


def _dau_tin(ma: str, version: str, link: str) -> str:
    return f"✅ **{ma}** `{version or '?'}` — QA báo test pass ({link})."


def tin_da_xoa(ma: str, version: str, link: str, kq: str) -> str:
    return f"{_dau_tin(ma, version, link)}\n🗑️ Bot đã tự xoá condition: {kq}"


def tin_nhac_xoa(ma: str, version: str, link: str, tt: dict, ly_do: str = "") -> str:
    """Tin khi bot KHONG tu xoa duoc: condition nguoi khac tao, hoac xoa hong (`ly_do`) -> kem nut thu lai."""
    dong = f"Condition `{tv.DIEU_KIEN}` còn trên Firebase: `{tt['bieu_thuc']}`"
    if tt["so_key"]:
        dong += f" · đang gán {tt['so_key']} key"
    if tt["cua_toi"]:
        return (f"{_dau_tin(ma, version, link)}\n{dong}\nBot chưa tự xoá được: {ly_do or 'không rõ lý do'}."
                f" Bấm **Xoá testvsl** để thử lại.")
    ai = "người khác tạo" if tt["nguoi_tao"] else "không xác định được người tạo"
    return f"{_dau_tin(ma, version, link)}\n{dong}\nCondition này {ai} — bot không xoá, nhờ người tạo xoá."


async def nhan_tin_pass(bot, m: discord.Message, ma_kenh: str, out: Path) -> bool:
    """Tin QA o kenh project bao test pass -> tu xoa testvsl bot tao, bao o #condition_fb. True khi la tin pass.

    User chot 26/11/2026: test pass thi bot tu xoa condition minh tao, chi nhan "da xoa", khong bat QA bam nut.
    Nut Xoa chi con khi bot khong tu xoa duoc (dang co luot chay app, Firebase loi) de QA thu lai."""
    chu = noi_dung(m)
    if not ma_kenh or not la_tin_pass(chu):
        return False
    if not bot.q.bao_lan_dau(f"{LOAI}|{m.id}"):        # quet lai tin lo sau restart: da nhac roi
        return True
    await don_bai_forum(bot, ma_kenh)
    ver = build_ma_app.VERSION_RE.search(chu)
    version = f"{ver.group(1)} ({ver.group(2)})" if ver else ""
    try:
        pkg = await asyncio.to_thread(bot_cong_viec.package_cua, ma_kenh, out)
        if not pkg:
            return True
        app = await asyncio.to_thread(tv.tim_app, pkg)
        tt = await asyncio.to_thread(tv.trang_thai, app["project"])
    except (RcError, OSError) as exc:
        log.warning("nhac xoa testvsl %s: %s", ma_kenh, exc)
        return True
    if not tt["co"]:
        log.info("test pass %s %s: khong con testvsl", ma_kenh, version)
        return True
    ly_do = ""
    if tt["cua_toi"]:
        if _job_dang_test(bot, pkg):
            ly_do = "đang có lượt chạy app này (đang dùng testvsl)"
        else:
            try:
                kq = await asyncio.to_thread(tv.xoa, app["project"])
                await _gui_kenh_condition(bot, tin_da_xoa(ma_kenh, version, m.jump_url, kq))
                log.info("test pass %s %s: tu xoa testvsl", ma_kenh, version)
                return True
            except (RcError, OSError) as exc:
                log.warning("tu xoa testvsl %s: %s", ma_kenh, exc)
                ly_do = str(exc)
    qa = await _gui_kenh_condition(bot, tin_nhac_xoa(ma_kenh, version, m.jump_url, tt, ly_do))
    bot.q.nho_tin({"msg_id": qa.id, "loai": LOAI, "app": {"ma": ma_kenh, "version": version, "package": pkg,
                                                             "project": app["project"]}})
    if tt["cua_toi"]:
        await qa.edit(view=nut((XOA, "Xoá testvsl", discord.ButtonStyle.danger), ("bo", "Để sau", XAM), msg_id=qa.id))
    return True


async def don_bai_forum(bot, ma: str) -> int:
    """Xoa moi bai Forum `qa-builds` bot tao cho app `ma` (moi version), tru bai dang dung. Loi chi ghi log."""
    if not getattr(bot, "kenh_forum", 0):
        return 0
    x = bot_lenh_xoa_bai
    try:
        forum = bot.get_channel(bot.kenh_forum) or await bot.fetch_channel(bot.kenh_forum)
        chon = x.chon_bai(await x.tat_ca_bai(forum), bot.user.id, ma, "", None, x.bai_dang_dung(bot))
        da, loi = await x.xoa(chon)
    except Exception as exc:          # noqa: BLE001 - loi Discord khong duoc chan tin nhac xoa testvsl
        log.warning("test pass %s: khong xoa duoc bai Forum: %s", ma, exc)
        return 0
    log.info("test pass %s: xoa %d/%d bai Forum %s", ma, da, len(chon), "; ".join(loi[:3]))
    return da


async def _gui_kenh_condition(bot, noi_dung_tin: str) -> discord.Message:
    """Gui vao kenh `condition_fb`; khong thay kenh / thieu quyen thi gui qa-auto nhu cu."""
    kenh = discord.utils.get(bot.get_all_channels(), name=KENH_CONDITION)
    if isinstance(kenh, discord.TextChannel):
        try:
            return await kenh.send(noi_dung_tin)
        except discord.HTTPException as exc:
            log.warning("khong gui duoc vao #%s: %s -> qa-auto", KENH_CONDITION, exc)
    return await (await bot._kenh_qa()).send(noi_dung_tin)


async def xu_ly_nut(bot, it: discord.Interaction, hanh_dong: str, c: dict) -> None:
    """Nut tren tin nhac xoa (c["loai"] == LOAI): Xoa testvsl | De sau."""
    if hanh_dong == XOA:
        await bam_xoa(bot, it, c)
        return
    await it.response.edit_message(content=f"{it.message.content}\n⏭ Để sau — {it.user.mention}", view=None)


async def bam_xoa(bot, it: discord.Interaction, c: dict) -> None:
    app = c.get("app") or {}
    await it.response.defer()
    if _job_dang_test(bot, app.get("package", "")):
        kq = "⏳ Đang có lượt chạy app này (đang dùng testvsl) — xong lượt rồi bấm lại."
        await it.message.edit(content=f"{it.message.content}\n{kq}")
        return
    try:
        kq = "🗑️ " + await asyncio.to_thread(tv.xoa, app["project"])
        view = None
    except (RcError, OSError, KeyError) as exc:
        kq, view = f"⛔ {exc}", discord.utils.MISSING
    await it.message.edit(content=f"{it.message.content}\n{kq} — {it.user.mention}", view=view)


def versions_can_tao(ma: str, version: str, out: Path = OUT) -> list[str]:
    """Version dua vao condition: version tin build; tin build KHAC version plan tuan thi them ca version plan
    (user chot 20/11/2026: dev build lai dung version thi khoi tao lai condition). Plan khong doc duoc -> chi build."""
    import datetime as dt
    import os

    from . import plan_tuan

    ban = tv.ten_version(version)
    try:
        link = os.environ.get(plan_tuan.ENV, "")
        plan = (plan_tuan.yeu_cau(plan_tuan.tai(link, out), ma, dt.date.today()) or {}).get("version") if link else []
    except Exception as exc:          # noqa: BLE001 - plan hong: van tao theo version build
        log.warning("plan tuan cho testvsl %s: %s", ma, exc)
        plan = []
    return [ban] if not plan or ban in plan else [ban, *plan]


async def tao_theo_build(ma: str, package: str, version: str, out: Path = OUT) -> str:
    cac = await asyncio.to_thread(versions_can_tao, ma, version, out)
    app = await asyncio.to_thread(tv.tim_app, package)
    return await asyncio.to_thread(tv.tao, app["project"], app["app_id"], cac)


async def bam_tao(bot, it: discord.Interaction, c: dict) -> None:
    """Nut tren tin nhac thieu / sai testvsl cua luot: tao condition theo package + version cua build do."""
    await it.response.defer()
    try:
        kq = "🧪 " + await tao_theo_build(c.get("ma", ""), c["package"], c["version"]) + " Bấm **Chạy lại** / **Verify lại** để chạy."
    except (RcError, OSError, KeyError) as exc:
        kq = f"⛔ Không tạo được testvsl: {exc}"
    await it.followup.send(f"{kq} — {it.user.mention}")


def dang_ky(bot, goi_y_ma) -> None:
    """Gan /testvsl vao `bot.tree`; `goi_y_ma` la autocomplete ma app dung chung voi /check."""

    @bot.tree.command(name="testvsl", description="Tạo condition testvsl theo đúng version, hoặc xoá condition bạn tạo")
    @app_commands.describe(ma_app="Mã app, vd AIP508", version="Version đang test (theo tin build), vd 1.1.0 (3) hoặc 1.1.0",
                           hanh_dong="tao: tạo / đổi sang version này · xoa: xoá (chỉ condition tài khoản bot tạo)")
    @app_commands.choices(hanh_dong=[app_commands.Choice(name="tạo", value="tao"),
                                     app_commands.Choice(name="xoá", value="xoa")])
    @app_commands.autocomplete(ma_app=goi_y_ma)
    async def testvsl(it: discord.Interaction, ma_app: str, version: str, hanh_dong: str = "tao"):
        await lenh(bot, it, ma_app, version, hanh_dong)


async def lenh(bot, it: discord.Interaction, ma_app: str, version: str, hanh_dong: str, out: Path = OUT) -> None:
    """/testvsl <ma> <version> [tao|xoa]."""
    if not bot._duoc_duyet(it.user):
        await it.response.send_message("Chỉ QA được duyệt mới dùng được /testvsl.", ephemeral=True)
        return
    ma = (ma_app or "").strip().upper()
    if not build_ma_app.MA_RE.fullmatch(ma) or not tv.ten_version(version):
        await it.response.send_message("Cần mã app (vd `AIP508`) và version (vd `1.1.0 (3)` hoặc `1.1.0`).",
                                       ephemeral=True)
        return
    await it.response.defer(thinking=True)
    try:
        pkg = await asyncio.to_thread(bot_cong_viec.package_cua, ma, out)
        if not pkg:
            raise RcError(f"sheet Check thông số KT không có package của {ma}")
        if hanh_dong == "xoa":
            if _job_dang_test(bot, pkg):
                raise RcError("đang có lượt chạy app này (đang dùng testvsl) — xong lượt rồi xoá")
            app = await asyncio.to_thread(tv.tim_app, pkg)
            kq = "🗑️ " + await asyncio.to_thread(tv.xoa, app["project"])
        else:
            kq = "🧪 " + await tao_theo_build(ma, pkg, version, out)
    except (RcError, OSError) as exc:
        kq = f"⛔ {exc}"
    await it.followup.send(f"**{ma}** `{version}`: {kq}"[:2000])
