"""`rcr-bot`: bot Discord build-watch.

Dev dang tin build o kenh build (hoac QA chuyen tiep tin) -> bot tra package, hoi ngay o kenh
QA kem nut. Nguoi duoc duyet bam Check -> bot vao App Tester tai dung ban (next-gen: release,
con lai: release note co chu "debug") roi chay `/rc-check` bang Claude headless -> tra loi
ket qua vao tin do. Khong kiem App Tester truoc (user chot 27/10/2026): chua co ban thi bao
loi kem nut Thu lai.

Cau hinh - chay duoc ca Windows lan Ubuntu. Doc lan luot: bien moi truong cua process,
bien User cua Windows (registry), file `~/.config/rcr/bot.env` (dong KEY=VALUE; systemd
tren Ubuntu cung doc file nay, khong doc ~/.bashrc):
  DISCORD_BOT_TOKEN        token bot (bi mat, khong in, khong ghi repo)
  DISCORD_BUILD_CHANNEL_ID kenh dev bao build (phay ngan cach: nghe them kenh QA chuyen tiep tin)
  DISCORD_QA_CHANNEL_ID    kenh bot hoi duyet + bao ket qua
  DISCORD_DUYET_USER_IDS   id nguoi duoc bam nut (phay ngan cach)
  DISCORD_QA_ROLE_ID       (tuy) role duoc bam nut
  DISCORD_JIRA_REVIEWER    email/username Jira gan lam Reviewer cho bug log tu Discord
Nhieu may cam cung luc -> moi may chay mot build, cac may song song (build khac nhau).
"""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path

import discord

from . import bot_chay_claude, bot_cong_viec, bot_hang_doi, bot_log_jira, build_ma_app
from .adb_client import AdbClient
from .adb_parsers import AdbError

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "out"
log = logging.getLogger("rcr-bot")


FILE_CAU_HINH = Path.home() / ".config" / "rcr" / "bot.env"


def _doc_file_env(path: Path) -> dict[str, str]:
    """`KEY=VALUE` moi dong, bo dong trong / `#`, bo nhay boc ngoai. File thieu -> {}."""
    try:
        dong = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return {}
    ra = {}
    for d in dong:
        d = d.strip()
        if d and not d.startswith("#") and "=" in d:
            k, v = d.split("=", 1)
            ra[k.removeprefix("export ").strip()] = v.strip().strip("'\"")
    return ra


def env(ten: str, file_cau_hinh: Path = FILE_CAU_HINH) -> str:
    """Bien moi truong -> bien User cua Windows (setx sau khi mo shell) -> ~/.config/rcr/bot.env."""
    gt = os.environ.get(ten, "")
    if not gt and os.name == "nt":
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
                gt = str(winreg.QueryValueEx(k, ten)[0])
        except OSError:
            pass
    if not gt:
        gt = _doc_file_env(file_cau_hinh).get(ten, "")
    return gt.strip()


def noi_dung(m) -> str:
    """Chu cua tin, ke ca tin CHUYEN TIEP: Discord de `content` rong, chu nam trong
    `message_snapshots` (do 2026-10-27, QA forward tin build sang kenh khac)."""
    phan = [m.content or ""] + [s.content or "" for s in getattr(m, "message_snapshots", None) or []]
    return "\n".join(p for p in phan if p)


def _nut(*cac: tuple[str, str, discord.ButtonStyle], msg_id: int) -> discord.ui.View:
    v = discord.ui.View(timeout=None)
    for hanh_dong, nhan, kieu in cac:
        v.add_item(discord.ui.Button(label=nhan, style=kieu, custom_id=f"rcr:{hanh_dong}:{msg_id}"))
    return v


XANH, XAM = discord.ButtonStyle.success, discord.ButtonStyle.secondary
NUT_HOI = (("check", "Check", XANH), ("bo", "Bỏ qua", XAM))
NUT_BUG = (("jira", "Log Jira", XANH), ("khongbug", "Không có bug thật", XAM))


def _view_bug(bugs: list[dict], chon: list[int], msg_id: int) -> discord.ui.View:
    """Menu tick bug (nhieu lua chon) + nut Log Jira / Khong co bug. Ve lai sau moi lan tick
    -> lua chon da tick phai la `default`, khong thi menu tu xoa trang."""
    v = discord.ui.View(timeout=None)
    v.add_item(discord.ui.Select(
        custom_id=f"rcr:chon:{msg_id}", placeholder="Tick bug thật…", min_values=0, max_values=len(bugs),
        options=[discord.SelectOption(label=nhan, value=gt, description=mo_ta, default=int(gt) in chon)
                 for gt, nhan, mo_ta in bot_cong_viec.lua_chon_bug(bugs)]))
    for hanh_dong, nhan, kieu in NUT_BUG:
        v.add_item(discord.ui.Button(label=nhan, style=kieu, custom_id=f"rcr:{hanh_dong}:{msg_id}"))
    return v


class BuildBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)
        self.kenh_build = {int(x) for x in env("DISCORD_BUILD_CHANNEL_ID").split(",") if x.strip()}
        self.kenh_qa = int(env("DISCORD_QA_CHANNEL_ID"))
        self.duyet = {int(x) for x in env("DISCORD_DUYET_USER_IDS").split(",") if x.strip()}
        self.role = int(env("DISCORD_QA_ROLE_ID") or 0)
        self.q = bot_hang_doi.HangDoi(OUT / "bot-hang-doi.json")
        self.ban: dict[str, int] = {}   # serial -> msg_id job dang chay tren may do
        self.reviewer = env("DISCORD_JIRA_REVIEWER")
        self.dang_log: set[int] = set()  # msg_id dang log Jira -> bam Log Jira hai lan khong tao trung

    async def setup_hook(self):
        asyncio.create_task(self.worker())

    async def _tin_qa(self, msg_id: int) -> discord.Message:
        return await self.get_channel(self.kenh_qa).fetch_message(msg_id)

    # --- tin build -> hoi o kenh QA ----------------------------------------------------
    async def on_message(self, m: discord.Message):
        # dev bao build qua webhook "Build Notification" (author.bot=True) -> nhan webhook, bo bot khac
        if m.channel.id not in self.kenh_build or (m.author.bot and not m.webhook_id):
            return
        chu = noi_dung(m)
        tin = build_ma_app.tach(chu)
        kenh = self.get_channel(self.kenh_qa)
        if tin is None:
            if "bản build" in chu.lower():   # dung la tin build ma lech mau -> hoi, khong doan
                await kenh.send(f"Tin build lệch mẫu, bot không tách được mã app / version: {m.jump_url}")
            return
        pkg = await asyncio.to_thread(bot_cong_viec.package_cua, tin["ma"], OUT)
        if not pkg:
            await kenh.send(f"Sheet Check thông số KT không có package của **{tin['ma']}** — {m.jump_url}")
            return
        qa = await kenh.send(f"**{tin['ma']}** `{tin['version']}`…")
        c = {**tin, "package": pkg, "loai_ban": build_ma_app.loai_ban(tin), "link_tin": m.jump_url, "msg_id": qa.id}
        self.q.nho_tin(c)
        await qa.edit(content=bot_cong_viec.tin_hoi(c), view=_nut(*NUT_HOI, msg_id=qa.id))

    # --- bam nut -------------------------------------------------------------------------
    def _duoc_duyet(self, user) -> bool:
        return user.id in self.duyet or (self.role and any(r.id == self.role for r in getattr(user, "roles", [])))

    async def on_interaction(self, it: discord.Interaction):
        cid = (it.data or {}).get("custom_id", "")
        if not cid.startswith("rcr:"):
            return
        _, hanh_dong, msg_id = cid.split(":")
        if not self._duoc_duyet(it.user):
            await it.response.send_message("Chỉ QA được duyệt mới bấm được.", ephemeral=True)
            return
        c = self.q.tin_cua(int(msg_id))
        if c is None:
            await it.response.send_message("Bot không còn nhớ build này.", ephemeral=True)
            return
        if hanh_dong == "bo":
            await it.response.edit_message(content=f"{bot_cong_viec.dau_tin(c)}\nBỏ qua — {it.user.mention}", view=None)
            return
        if hanh_dong in ("chon", "jira", "khongbug"):
            await self._review_bug(it, hanh_dong, c)
            return
        vi_tri = self.q.them({**c, "nguoi_duyet": it.user.id})   # check | thu lai
        if vi_tri is None:
            await it.response.send_message("Build này đã trong hàng đợi.", ephemeral=True)
            return
        await it.response.edit_message(view=None, content=f"{bot_cong_viec.dau_tin(c)}\n"
                                       f"Đã duyệt bởi {it.user.mention} — bản {c['loai_ban']}, vị trí {vi_tri} trong hàng đợi.")

    # --- QA review bug roi log Jira -----------------------------------------------------
    async def _review_bug(self, it: discord.Interaction, hanh_dong: str, c: dict):
        bugs, msg_id = c.get("bugs") or [], c["msg_id"]
        if not bugs or c.get("jira") is not None or msg_id in self.dang_log:
            await it.response.send_message("Danh sách bug này đã xử lý xong hoặc đang log.", ephemeral=True)
            return
        if hanh_dong == "chon":
            c["bug_chon"] = sorted(int(x) for x in (it.data or {}).get("values", [])
                                   if x.isdigit() and int(x) < len(bugs))
            self.q.nho_tin(c)
            await it.response.edit_message(content=bot_cong_viec.tin_bug(bugs, c["bug_chon"]),
                                           view=_view_bug(bugs, c["bug_chon"], msg_id))
            return
        if hanh_dong == "khongbug":
            c["jira"] = {"issues": [], "loi": ""}
            self.q.nho_tin(c)
            await it.response.edit_message(content=f"{bot_cong_viec.tin_bug(bugs)}\n"
                                           f"Không log — {it.user.mention} xác nhận không có bug thật.", view=None)
            return
        chon = c.get("bug_chon") or []
        if not chon:
            await it.response.send_message("Chưa tick bug nào trong menu.", ephemeral=True)
            return
        if not self.reviewer:
            await it.response.send_message("Bot thiếu DISCORD_JIRA_REVIEWER trong bot.env.", ephemeral=True)
            return
        self.dang_log.add(msg_id)
        await it.response.edit_message(content=f"{bot_cong_viec.tin_bug(bugs, chon)}\n"
                                       f"Đang log {len(chon)} bug lên Jira ({c['ma']}) — {it.user.mention}", view=None)
        try:
            kq = await asyncio.to_thread(bot_log_jira.chay, [bugs[i] for i in chon], c,
                                         c.get("link_report", ""), self.reviewer, REPO, OUT)
        except Exception as exc:             # noqa: BLE001 - loi luot log khong duoc giet bot
            log.exception("log jira loi")
            await it.message.edit(view=_view_bug(bugs, chon, msg_id))   # tra menu lai de bam thu lai
            await it.message.reply(f"⛔ Log Jira lỗi: {exc}")
            return
        finally:
            self.dang_log.discard(msg_id)
        c["jira"] = kq
        self.q.nho_tin(c)
        await it.message.reply(bot_cong_viec.tin_jira(kq, len(chon)))

    # --- chia job cho cac may ----------------------------------------------------------
    async def worker(self):
        """Moi nhip: may nao dang cam, ranh, khong bi luot tay giu khoa -> lay job dau tien chua chay."""
        await self.wait_until_ready()
        adb = AdbClient()
        while not self.is_closed():
            try:
                may = [d for d in await adb.devices() if d.ready]
            except AdbError as exc:
                log.warning("khong doc duoc danh sach may: %s", exc)
                may = []
            for d in may:
                if d.serial in self.ban or bot_hang_doi.may_ban(bot_hang_doi.khoa_may(OUT, d.serial)):
                    continue
                job = self.q.lay()
                if job is None:
                    break
                self.ban[d.serial] = job["msg_id"]
                asyncio.create_task(self._chay_tren(job, d.serial, bot_cong_viec.ten_may(d.serial, d.model)))
            await asyncio.sleep(5)

    async def _chay_tren(self, job: dict, serial: str, ten: str):
        try:
            await self._chay(job, serial, ten)
        except Exception as exc:             # noqa: BLE001 - mot job hong khong duoc giet bot
            log.exception("job loi")
            await self.get_channel(self.kenh_qa).send(f"⛔ {bot_cong_viec.dau_tin(job)} [{ten}]: lỗi bot {exc}")
        finally:
            self.q.xong(job)
            self.ban.pop(serial, None)

    async def _chay(self, job: dict, serial: str, ten: str):
        qa = await self._tin_qa(job["msg_id"])
        dau = f"{bot_cong_viec.dau_tin(job)} · máy **{ten}**"
        await qa.edit(content=f"{dau}\nĐang cài bản {job['loai_ban']} từ App Tester…")
        cai = await asyncio.to_thread(bot_cong_viec.cai, job["package"], job["version"], job["loai_ban"], serial)
        if "loi" in cai:
            # Thuong la App Tester chua co ban (dev chua day) -> de nguoi bam thu lai sau.
            await qa.edit(content=f"{dau}\n⛔ Cài không được: {cai['loi']}",
                          view=_nut(("check", "Thử lại", XANH), ("bo", "Bỏ qua", XAM), msg_id=qa.id))
            return
        ghi = " (đã gỡ bản cũ khác loại — mất data app)" if cai.get("go_ban_cu") else ""
        await qa.edit(content=f"{dau}\nĐã cài{ghi}. Đang chạy /rc-check…")
        timeout = (bot_chay_claude.TIMEOUT_NEXT_GEN if job["loai_ban"] == "release"
                   else bot_chay_claude.TIMEOUT_BO_TC)
        kq = await asyncio.to_thread(bot_chay_claude.chay, job["package"], serial, REPO, timeout, OUT)
        chu = bot_cong_viec.TRANG_THAI.get(kq["trang_thai"], ("", kq["trang_thai"]))[1]
        await qa.edit(content=f"{dau}\n{chu}")
        f = bot_cong_viec.file_report(kq, OUT)
        await qa.reply(bot_cong_viec.tin_ket_qua(job, kq, f) + f"\nMáy: {ten}",
                       file=discord.File(f) if f else discord.utils.MISSING)
        if kq.get("bugs"):
            # Luu vao tin cua build: bot khoi dong lai van tick / log tiep duoc.
            c = {**(self.q.tin_cua(job["msg_id"]) or job), "bugs": kq["bugs"], "bug_chon": [],
                 "link_report": kq.get("link", ""), "jira": None}
            self.q.nho_tin(c)
            await qa.reply(bot_cong_viec.tin_bug(kq["bugs"]), view=_view_bug(kq["bugs"], [], job["msg_id"]))


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    token = env("DISCORD_BOT_TOKEN")
    if not token:
        print("Thiếu DISCORD_BOT_TOKEN", flush=True)
        return 1
    BuildBot().run(token, log_handler=None)
    return 0
