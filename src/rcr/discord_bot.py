"""`rcr-bot`: bot Discord build-watch.

Dev dang tin build o kenh build (hoac QA chuyen tiep tin) -> bot tra package, hoi ngay o kenh
QA kem nut. Nguoi duoc duyet bam Check -> bot vao App Tester tai dung ban (next-gen: release,
con lai: release note co chu "debug") roi chay `/rc-check` bang Claude headless -> tra loi
ket qua vao tin do. Khong kiem App Tester truoc (user chot 27/10/2026): chua co ban thi bao
loi kem nut Thu lai.

Cau hinh (bien moi truong, doc ca bien User cua Windows dat sau khi mo terminal):
  DISCORD_BOT_TOKEN        token bot (bi mat, khong in, khong ghi repo)
  DISCORD_BUILD_CHANNEL_ID kenh dev bao build
  DISCORD_QA_CHANNEL_ID    kenh bot hoi duyet + bao ket qua
  DISCORD_DUYET_USER_IDS   id nguoi duoc bam nut (phay ngan cach)
  DISCORD_QA_ROLE_ID       (tuy) role duoc bam nut
Nhieu may cam cung luc -> moi may chay mot build, cac may song song (build khac nhau).
"""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path

import discord

from . import bot_chay_claude, bot_cong_viec, bot_hang_doi, build_ma_app
from .adb_client import AdbClient
from .adb_parsers import AdbError

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "out"
log = logging.getLogger("rcr-bot")


def env(ten: str) -> str:
    """Bien moi truong; tren Windows doc them bien User trong registry (setx sau khi mo shell)."""
    gt = os.environ.get(ten, "")
    if not gt and os.name == "nt":
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
                gt = str(winreg.QueryValueEx(k, ten)[0])
        except OSError:
            pass
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


class BuildBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)
        self.kenh_build = int(env("DISCORD_BUILD_CHANNEL_ID"))
        self.kenh_qa = int(env("DISCORD_QA_CHANNEL_ID"))
        self.duyet = {int(x) for x in env("DISCORD_DUYET_USER_IDS").split(",") if x.strip()}
        self.role = int(env("DISCORD_QA_ROLE_ID") or 0)
        self.q = bot_hang_doi.HangDoi(OUT / "bot-hang-doi.json")
        self.ban: dict[str, int] = {}   # serial -> msg_id job dang chay tren may do

    async def setup_hook(self):
        asyncio.create_task(self.worker())

    async def _tin_qa(self, msg_id: int) -> discord.Message:
        return await self.get_channel(self.kenh_qa).fetch_message(msg_id)

    # --- tin build -> hoi o kenh QA ----------------------------------------------------
    async def on_message(self, m: discord.Message):
        if m.channel.id != self.kenh_build or m.author.bot:
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
        vi_tri = self.q.them({**c, "nguoi_duyet": it.user.id})   # check | thu lai
        if vi_tri is None:
            await it.response.send_message("Build này đã trong hàng đợi.", ephemeral=True)
            return
        await it.response.edit_message(view=None, content=f"{bot_cong_viec.dau_tin(c)}\n"
                                       f"Đã duyệt bởi {it.user.mention} — bản {c['loai_ban']}, vị trí {vi_tri} trong hàng đợi.")

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
        await qa.reply(bot_cong_viec.tin_ket_qua(job, kq) + f"\nMáy: {ten}")


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    token = env("DISCORD_BOT_TOKEN")
    if not token:
        print("Thiếu DISCORD_BOT_TOKEN", flush=True)
        return 1
    BuildBot().run(token, log_handler=None)
    return 0
