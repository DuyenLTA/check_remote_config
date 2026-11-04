"""Lenh slash cua bot chinh: /hang-doi, /check, /check-bug.

Chi bot chinh dang ky lenh (may phu dung chung token nhung khong co CommandTree). Lenh dong bo vao tung server
bot dang o (hien ngay), khong dang ky global. Tra loi rieng cho nguoi go (ephemeral) de khong rac kenh; viec
that (tin hoi Check, luot verify) van di qua dung duong cua tin build -> chi co mot luong chay.

- /hang-doi: luot dang chay, luot dang cho, tinh trang may; nut Dung / Huy cho tung luot.
- /check <ma app> <version> [sdk]: tin hoi Check moi o kenh QA (chi QA duoc duyet). Build bot da thay -> giu
  thong tin build cu; build chua thay -> can `sdk` de chon nhanh (Next-Gen / bo TC) nhu tin build.
- /check-bug <ma app>: bug bot da log cho app + trang thai Jira; nut verify bug Reviewing tren build gan nhat.
"""

from __future__ import annotations

import asyncio
import logging
import re

import discord
from discord import app_commands

from . import bot_cong_viec, bot_hang_doi, bot_nhan_build, build_ma_app
from . import bot_jira_rest as jira
from . import bot_verify_jira as v
from .adb_client import AdbClient
from .adb_parsers import AdbError

log = logging.getLogger("rcr-bot")
MAX_TIN = 1900
MAX_NUT = 25                       # Discord: toi da 25 nut (5 hang x 5) mot tin
MAX_GOI_Y = 25                     # Discord: toi da 25 goi y autocomplete
SDK_HOP_LE = re.compile(r"^(?:\d+\.\d+\.\d+|next-?gen|revert next-?gen)$", re.I)
ICON_TRANG_THAI = {"reviewing": "⏳", "closed": "✅", "done": "✅", "reopened": "🔁", "to do": "🔁"}


# --- dang ky + dong bo ---------------------------------------------------------------------
def dang_ky(bot) -> None:
    """Gan ba lenh vao `bot.tree`. Goi mot lan trong `BuildBot.__init__` (chi bot chinh)."""
    tree: app_commands.CommandTree = bot.tree

    async def goi_y_ma(it: discord.Interaction, dang_go: str) -> list[app_commands.Choice[str]]:
        return [app_commands.Choice(name=ma, value=ma) for ma in goi_y_ma_app(bot, dang_go)]

    @tree.command(name="hang-doi", description="Xem lượt đang chạy, lượt đang chờ và tình trạng máy test")
    async def hang_doi(it: discord.Interaction):
        await xem_hang_doi(bot, it)

    @tree.command(name="check", description="Gửi tin hỏi Check cho một build (chạy lại hoặc build bot chưa thấy)")
    @app_commands.describe(ma_app="Mã app, vd AIP922", version="Version kèm code, vd 3.7.0 (30)",
                           sdk="Chỉ cần khi bot chưa thấy tin build: số SDK (3.6.1, 3.7.0…) hoặc next-gen")
    @app_commands.autocomplete(ma_app=goi_y_ma)
    async def check(it: discord.Interaction, ma_app: str, version: str, sdk: str | None = None):
        await lenh_check(bot, it, ma_app, version, sdk)

    @tree.command(name="check-bug", description="Bug bot đã log cho một app, trạng thái Jira, verify bug Reviewing")
    @app_commands.describe(ma_app="Mã app, vd AIP922")
    @app_commands.autocomplete(ma_app=goi_y_ma)
    async def check_bug(it: discord.Interaction, ma_app: str):
        await lenh_check_bug(bot, it, ma_app)


async def dong_bo(bot) -> None:
    """Dong bo lenh vao tung server (hien ngay, global mat toi 1 gio). Server moi ra lenh khi bot ket noi lai.
    Bot moi vao server ma thieu scope `applications.commands` -> 403: chi ghi log, bot van chay binh thuong."""
    for g in bot.guilds:
        bot.tree.copy_global_to(guild=g)
        try:
            await bot.tree.sync(guild=g)
            log.info("da dong bo lenh slash vao server %s", g.name)
        except discord.HTTPException as exc:
            log.warning("khong dong bo duoc lenh slash vao server %s (thieu scope applications.commands?): %s",
                        g.name, exc)


def goi_y_ma_app(bot, dang_go: str) -> list[str]:
    """Ma app bot da tung thay (tin build cu), loc theo chu dang go - khong tai sheet (autocomplete phai < 3 giay)."""
    go = (dang_go or "").strip().upper()
    cac = sorted({str(t.get("ma") or "") for t in bot.q.tin.values()} - {""})
    return [ma for ma in cac if go in ma][:MAX_GOI_Y]


# --- /hang-doi ------------------------------------------------------------------------------
def _ten_luot(job: dict) -> str:
    if job.get("loai_job") == "verify":
        return f"🔁 verify {len(job.get('verify') or [])} bug — **{job.get('ma', '')}** `{job.get('version', '')}`"
    return f"**{job.get('ma', '')}** `{job.get('version', '')}`"


def tin_hang_doi(bot, may: list | None, link_kenh: str) -> tuple[str, discord.ui.View]:
    """Bang hang doi + may. `may`: danh sach Device tu adb (None = khong doc duoc adb).
    `link_kenh`: `https://discord.com/channels/<server>/<kenh QA>` de noi toi tin cua tung luot."""
    serial_cua = {m: s for s, m in bot.ban.items()}
    model = {d.serial: d.model for d in may or []}
    chay, cho = [], []
    for j in bot.q.jobs:
        (chay if bot.q.dang_chay_tren_may(j) else cho).append(j)
    view = discord.ui.View(timeout=None)

    def nut(hanh_dong: str, nhan: str, j: dict, kieu) -> None:
        if len(view.children) < MAX_NUT:
            view.add_item(discord.ui.Button(label=nhan, style=kieu, custom_id=f"rcr:{hanh_dong}:{j['msg_id']}"))

    dong = ["**▶️ Đang chạy**"]
    for i, j in enumerate(chay, 1):
        serial = serial_cua.get(j["msg_id"])
        if j.get("kq") is not None:
            o = "đang gửi kết quả"
        elif j.get("dang_o"):
            o = f"máy phụ `{j['dang_o']}`"
        else:
            o = f"máy **{bot_cong_viec.ten_may(serial, model.get(serial, ''))}**" if serial else "đang nhận máy"
        dong.append(f"{i}. {_ten_luot(j)} — {o} · [tin]({link_kenh}/{j['msg_id']})")
        if j.get("kq") is None:
            nut("dung", f"Dừng {j.get('ma', '')} #{i}", j, discord.ButtonStyle.danger)
    if not chay:
        dong.append("Không có lượt nào.")
    dong.append("**⏳ Đang chờ**")
    for i, j in enumerate(cho, 1):
        dong.append(f"{i}. {_ten_luot(j)} · [tin]({link_kenh}/{j['msg_id']})")
        nut("huyhd", f"Huỷ {j.get('ma', '')} #{i}", j, discord.ButtonStyle.secondary)
    if not cho:
        dong.append("Hàng đợi trống.")
    dong.append("**📱 Máy test**")
    if may is None:
        dong.append("Không đọc được danh sách máy (adb lỗi).")
    for d in may or []:
        ten = bot_cong_viec.ten_may(d.serial, d.model)
        if not d.ready:
            tt = f"chưa sẵn sàng (`{d.state}`)"
        elif d.serial in bot.ban:
            job = next((j for j in bot.q.jobs if j["msg_id"] == bot.ban[d.serial]), {})
            tt = f"đang chạy {_ten_luot(job)}" if job else "đang chạy"
        elif bot_hang_doi.may_ban(bot_hang_doi.khoa_may(bot.out, d.serial)):
            tt = "bị khoá bởi lượt chạy ngoài bot (rc-check tay…)"
        else:
            tt = "rảnh"
        dong.append(f"• {ten}: {tt}")
    if may == []:
        dong.append("Không có máy nào cắm vào máy chính.")
    for may_phu, serial in sorted(getattr(bot, "xin_cho", {})):
        dong.append(f"• máy phụ `{may_phu}` · {serial}: rảnh, đang xin việc")
    return _cat_tin(dong), view


async def xem_hang_doi(bot, it: discord.Interaction) -> None:
    await it.response.defer(ephemeral=True, thinking=True)
    try:
        may = await AdbClient().devices()
    except AdbError as exc:
        log.warning("/hang-doi: khong doc duoc adb: %s", exc)
        may = None
    kenh = await bot._kenh_qa()
    chu, view = tin_hang_doi(bot, may, f"https://discord.com/channels/{kenh.guild.id}/{kenh.id}")
    await it.followup.send(chu, view=view, ephemeral=True)


# --- /check ---------------------------------------------------------------------------------
def doc_lenh_check(ma_app: str, version: str, sdk: str | None) -> tuple[dict | None, str]:
    """(tin build kieu `build_ma_app.tach`, "") hoac (None, loi). Khong co sdk -> tin chi co ma + version."""
    ma = (ma_app or "").strip().upper()
    if not build_ma_app.MA_RE.fullmatch(ma):
        return None, f"Mã app `{ma_app}` sai mẫu — cần 3 chữ + 3 số, vd `AIP922`."
    ver = build_ma_app.VERSION_RE.fullmatch((version or "").strip())
    if not ver:
        return None, f"Version `{version}` sai mẫu — cần kèm code, vd `3.7.0 (30)`."
    sdk = (sdk or "").strip()
    if not sdk:
        return {"ma": ma, "version": f"{ver.group(1)} ({ver.group(2)})"}, ""
    if not SDK_HOP_LE.fullmatch(sdk):
        return None, f"SDK `{sdk}` sai mẫu — dùng số SDK (`3.6.1`, `3.7.0`…), `next-gen` hoặc `revert next-gen`."
    ghi = sdk if "next" in sdk.lower() else f"apply tutorial {sdk}"
    # Cung bo tach voi tin build -> chon nhanh Next-Gen / bo TC dung y nhu dev ghi trong tin.
    return build_ma_app.tach(f"{ma} v{ver.group(1)} ({ver.group(2)}) {ghi}"), ""


async def lenh_check(bot, it: discord.Interaction, ma_app: str, version: str, sdk: str | None) -> None:
    if not bot._duoc_duyet(it.user):
        await it.response.send_message("Chỉ QA được duyệt mới dùng được /check.", ephemeral=True)
        return
    tin, loi = doc_lenh_check(ma_app, version, sdk)
    if tin is None:
        await it.response.send_message(loi, ephemeral=True)
        return
    await it.response.defer(ephemeral=True, thinking=True)
    try:
        kq = await _check(bot, tin)
    except Exception as exc:              # noqa: BLE001 - loi sheet / Discord tra ve cho nguoi go
        log.exception("/check loi")
        kq = f"⛔ Lỗi: {exc}"
    await it.followup.send(kq[:2000], ephemeral=True)


async def _check(bot, tin: dict) -> str:
    kenh = await bot._kenh_qa()
    da_hoi = [t for t in bot_nhan_build.tin_da_hoi(bot, tin) if t.get("loai_job") != "verify"]
    if da_hoi:                             # build bot da thay: tin hoi moi, giu thong tin build (doi SDK neu go)
        doi = {k: tin[k] for k in ("next_gen", "tutorial", "sdk") if k in tin}
        return await bot_nhan_build.hoi_lai_build(bot, tin, "", kenh.send, doi)
    if "sdk" not in tin:
        return (f"Bot chưa thấy tin build **{tin['ma']}** `{tin['version']}` — gõ thêm `sdk` (vd `3.6.1`, `3.7.0`, "
                "`next-gen`) để bot chọn đúng nhánh chấm. Build không apply SDK thì dùng /check-bug để verify bug.")
    return await bot_nhan_build.hoi_build_moi(bot, tin, "", kenh, bot.out)


# --- /check-bug -----------------------------------------------------------------------------
def build_gan_nhat(bot, ma: str) -> dict | None:
    """Tin build gan nhat cua app co du package + version (tin hoi Check hoac luot verify) - build de verify."""
    cac = [t for t in bot.q.tin.values()
           if t.get("ma") == ma and t.get("package") and t.get("version") and t.get("msg_id")]
    return max(cac, key=lambda t: int(t["msg_id"]), default=None)


def tin_check_bug(ma: str, bugs: list[dict], build: dict | None) -> tuple[str, discord.ui.View | None]:
    reviewing = [b for b in bugs if b["status"].lower() == "reviewing"]
    dong = [f"🐞 **{ma}** — {len(bugs)} bug bot đã log, {len(reviewing)} đang Reviewing"]
    if not bugs:
        dong[0] = f"🐞 **{ma}** — chưa có bug nào bot log trên Jira."
    for b in bugs:
        icon = ICON_TRANG_THAI.get(b["status"].lower(), "•")
        dong.append(f"{icon} [{b['key']}]({b['link']}) `{b['status'] or '?'}` — {v._cat(b['summary'], 90)}")
    view = None
    if reviewing and build:
        dong.append(f"Verify sẽ cài build gần nhất bot thấy: `{build['version']}` (bản {build.get('loai_ban') or 'release'}).")
        view = discord.ui.View(timeout=None)
        view.add_item(discord.ui.Button(label=f"Verify {len(reviewing)} bug Reviewing",
                                        style=discord.ButtonStyle.success, custom_id=f"rcr:verify:{build['msg_id']}"))
    elif reviewing:
        dong.append("Bot chưa thấy build nào của app này — gõ /check với build mới trước rồi verify.")
    return _cat_tin(dong), view


async def lenh_check_bug(bot, it: discord.Interaction, ma_app: str) -> None:
    ma = (ma_app or "").strip().upper()
    if not jira.PROJECT_RE.fullmatch(ma):
        await it.response.send_message(f"Mã app `{ma_app}` sai mẫu — vd `AIP922`.", ephemeral=True)
        return
    if not jira.bat(bot.jira_url, bot.jira_token):
        await it.response.send_message("Bot chưa có JIRA_URL / JIRA_PERSONAL_TOKEN — không đọc được Jira.",
                                       ephemeral=True)
        return
    await it.response.defer(ephemeral=True, thinking=True)
    keys = [u["key"] for u in v.ung_vien(bot.q.tin, ma)]      # bug log truoc khi co label auto-qa
    try:
        bugs = await asyncio.to_thread(jira.bug_cua_app, bot.jira_url, bot.jira_token, ma, keys)
    except jira.JiraLoi as exc:
        await it.followup.send(f"⛔ Không đọc được Jira: {exc}", ephemeral=True)
        return
    chu, view = tin_check_bug(ma, bugs, build_gan_nhat(bot, ma))
    await it.followup.send(chu, view=view or discord.utils.MISSING, ephemeral=True)


def _cat_tin(dong: list[str]) -> str:
    """Ghep dong, cat bot dong cuoi cho vua mot tin Discord (bao so dong bi an)."""
    ra, dai = [], 0
    for i, d in enumerate(dong):
        if dai + len(d) + 1 > MAX_TIN - 40:
            ra.append(f"… và {len(dong) - i} dòng nữa")
            break
        ra.append(d)
        dai += len(d) + 1
    return "\n".join(ra)
