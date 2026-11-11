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
  DISCORD_BUILD_CHANNEL_ID kenh nhan build ngoai kenh project (qa-auto; phay ngan cach)
  DISCORD_QA_CHANNEL_ID    kenh bot hoi duyet + bao ket qua
  DISCORD_FORUM_CHANNEL_ID (tuy) kenh Forum: moi build mot bai, tin goc nam trong bai (bot_forum)
  DISCORD_DUYET_USER_IDS   id nguoi duoc bam nut (phay ngan cach)
  DISCORD_QA_ROLE_ID       (tuy) role duoc bam nut
  DISCORD_JIRA_REVIEWER    email/username Jira gan lam Reviewer cho bug log tu Discord
  DISCORD_DEV_IDS          id dev duoc tag khi bao bug o kenh project (phay ngan cach)
  JIRA_URL, JIRA_PERSONAL_TOKEN  (tuy) bat tu verify bug Reviewing
Nhieu may cam cung luc -> moi may chay mot build, cac may song song (build khac nhau).

File nay giu class bot, vong worker va `_chay_tren`; phan viec tach module rieng:
  bot_giao_dien (nut, menu, doc tin) | bot_nhan_build (tin bao build, hoi QA, xep verify)
  bot_nut_bam (nut bam, log Jira)    | bot_job_check / bot_job_verify (mot luot Check / verify)
  bot_lenh_slash (/hang-doi, /check, /check-bug - chi bot chinh)
Method `_xxx` mong giu lai de test va module khac goi / thay tung buoc.
"""

from __future__ import annotations

import asyncio
import logging
import socket
from pathlib import Path

import discord
from discord import app_commands

from . import (audit_tom_tat, bot_bat_tin_lo, bot_canh_may, bot_chay_claude, bot_cho_publish, bot_cong_viec,  # noqa: F401 - test thay
               bot_dung_luot, bot_forum, bot_gui_lai, bot_hang_doi, bot_hoi_dap, bot_hop_thu_bug, bot_jira_rest, bot_job_check, bot_job_verify,
               bot_kenh_project, bot_keo_sprint, bot_lenh_slash, bot_log_jira, bot_may_phu, bot_nhan_build,
               bot_nut_bam, bot_tien_trinh)
from .adb_client import AdbClient
from .adb_parsers import AdbError
from .bot_giao_dien import XAM, XANH, noi_dung  # noqa: F401 - ten cu, test / module khac van dung
from .bot_giao_dien import nut as _nut, view_bug as _view_bug  # noqa: F401
from .cau_hinh_bot import FILE_CAU_HINH, env  # noqa: F401 - dung chung voi rcr-notify

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "out"
log = logging.getLogger("rcr-bot")


class BuildBot(discord.Client):
    duyet: frozenset[int] = frozenset()    # mac dinh khi chua __init__ (test); __init__ doc tu env
    role = 0
    dieu_phoi = 0                           # kenh dieu phoi may phu (0 = khong dung)
    vai_tro = "chinh"

    @property
    def la_phu(self) -> bool:
        return self.vai_tro == "phu"

    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)
        self.kenh_build = {int(x) for x in env("DISCORD_BUILD_CHANNEL_ID").split(",") if x.strip()}
        self.kenh_qa = int(env("DISCORD_QA_CHANNEL_ID"))
        self.kenh_forum = int(env("DISCORD_FORUM_CHANNEL_ID") or 0)   # moi build mot bai (bot_forum); 0 = tat
        self.duyet = {int(x) for x in env("DISCORD_DUYET_USER_IDS").split(",") if x.strip()}
        self.role = int(env("DISCORD_QA_ROLE_ID") or 0)
        # May phu (bot_may_phu): cung token, khong doc tin build, chi chay job bot chinh giao.
        self.vai_tro = env("RCR_VAI_TRO") or "chinh"
        self.ten_may = env("RCR_TEN_MAY") or socket.gethostname()
        self.dieu_phoi = int(env("DISCORD_DIEU_PHOI_CHANNEL_ID") or 0)
        self.out = OUT
        self.xin_cho: dict[tuple[str, str], str] = {}   # bot chinh: (may phu, serial) -> ten may test dang ranh
        self.da_xin: dict[str, float] = {}               # may phu: serial -> luc xin job
        self.may_san: set[str] = set()                   # may phu: serial dang cam, ready
        self.q = bot_hang_doi.HangDoi(OUT / ("bot-hang-doi-may-phu.json" if self.la_phu else "bot-hang-doi.json"))
        self.ban: dict[str, int] = {}   # serial -> msg_id job dang chay tren may do
        self.reviewer = env("DISCORD_JIRA_REVIEWER")
        self.dang_log: set[int] = set()  # msg_id dang log Jira -> bam Log Jira hai lan khong tao trung
        # Verify bug Reviewing goi Jira REST thang; thieu token -> tinh nang tat, luong Check giu nguyen.
        self.jira_url, self.jira_token = env("JIRA_URL"), env("JIRA_PERSONAL_TOKEN")
        self.dev_ids = env("DISCORD_DEV_IDS")   # dev tag khi bao bug o kenh project (phay ngan cach)
        self.hoi_lock = asyncio.Lock()          # hoi dap: moi lan mot cau
        # Lenh slash chi o bot chinh: may phu cung token, co CommandTree o ca hai thi hai ben cung tra loi lenh.
        self.tree = None if self.la_phu else app_commands.CommandTree(self)
        self.da_dong_bo_lenh = False
        if self.tree is not None:
            bot_lenh_slash.dang_ky(self)

    async def setup_hook(self):
        # Bug cua luot chay tay -> menu tick o kenh QA. May phu cung quet: chuyen sang bot chinh (bot_hop_thu_bug).
        asyncio.create_task(bot_hop_thu_bug.vong_lap(self))
        if self.la_phu:
            asyncio.create_task(self._vong_may_phu())
            return
        asyncio.create_task(self.worker())
        asyncio.create_task(bot_keo_sprint.vong_lap(self))   # bug log luc chua co sprint -> keo vao sprint moi
        asyncio.create_task(bot_cho_publish.vong_lap(self, OUT))   # report chua co artifact -> thay link khi publish

    async def on_ready(self):
        """Moi lan ket noi (ca reconnect sau mat mang - session bi huy thi Discord khong gui lai tin cu, 30/10/2026):
        phat lai tin build bi lo. Build da hoi roi thi tu bo, quet lai khong hoi trung."""
        if self.la_phu:
            return
        # Moi phien moi (khoi dong / session bi huy): tin `xin` cua may phu gui luc mat ket noi co the da lo ->
        # bao may phu xin lai ngay. Nho vay may phu khong phai xin lai dinh ky moi 15 phut (spam kenh dieu phoi).
        if self.dieu_phoi:
            try:
                await bot_may_phu.gui(await self._kenh_dieu_phoi(), "chinh_khoi_dong", {"may": "chinh"})
            except Exception as exc:         # noqa: BLE001
                log.warning("khong bao duoc may phu: %s", exc)
        if getattr(self, "tree", None) is not None and not self.da_dong_bo_lenh:
            self.da_dong_bo_lenh = True          # moi lan khoi dong mot lan, reconnect khong dong bo lai
            try:
                await bot_lenh_slash.dong_bo(self)
            except Exception:                # noqa: BLE001 - lenh slash loi khong duoc chan nhan build
                log.exception("dong bo lenh slash loi")
        try:
            log.info("quet tin build bi lo: %d tin", await bot_bat_tin_lo.quet(self))
        except Exception:                    # noqa: BLE001 - quet loi khong duoc lam chet bot
            log.exception("quet tin build bi lo loi")

    async def _kenh_qa(self):
        """Ngay sau khi ket noi lai cache kenh co the chua day (get_channel -> None) -> hoi thang Discord."""
        return self.get_channel(self.kenh_qa) or await self.fetch_channel(self.kenh_qa)

    async def _tin_qa(self, msg_id: int) -> discord.Message:
        """Tin goc cua job: trong bai Forum (`kenh_id` cua tin) hoac o qa-auto (tin cu / Forum tat)."""
        kid = int((self.q.tin_cua(msg_id) or {}).get("kenh_id") or 0)
        kenh = (self.get_channel(kid) or await self.fetch_channel(kid)) if kid else await self._kenh_qa()
        await bot_forum.mo_lai(kenh)          # bai Forum da archive -> mo lai truoc khi sua tin
        return await kenh.fetch_message(msg_id)

    # --- tien ich -----------------------------------------------------------------------
    def bi_mat(self) -> list[str]:
        """Gia tri phai che trong moi cau tra loi gui len Discord."""
        return [env("DISCORD_BOT_TOKEN"), self.jira_token, env("DISCORD_WEBHOOK_URL")]

    async def _kenh_dieu_phoi(self):
        return self.get_channel(self.dieu_phoi) or await self.fetch_channel(self.dieu_phoi)

    async def _vong_may_phu(self):
        await self.wait_until_ready()
        adb = AdbClient()

        async def may():
            return [d for d in await adb.devices() if d.ready]
        await bot_may_phu.vong_may_phu(self, await self._kenh_dieu_phoi(), may)

    async def _nhan_dieu_phoi(self, m: discord.Message):
        """Tin `RCR ...` cua chinh bot (cung token) o kenh dieu phoi; tin khac o kenh nay bo qua."""
        if self.user is None or m.author.id != self.user.id:
            return
        try:
            goi = await bot_may_phu.doc(m)
            if goi is None:
                return
            if self.la_phu:
                await bot_may_phu.nhan_o_may_phu(self, *goi, m.channel)
            elif goi[0] == "bug":            # luot chay tay o may phu co bug -> bot chinh dang menu
                await bot_hop_thu_bug.nhan_tu_may_phu(self, goi[1])
            else:
                bot_may_phu.nhan_o_may_chinh(self, *goi)
        except Exception:                    # noqa: BLE001 - mot tin hong khong duoc giet bot
            log.exception("tin dieu phoi loi: %s", m.content)

    async def on_message(self, m: discord.Message):
        if self.dieu_phoi and m.channel.id == self.dieu_phoi:
            await self._nhan_dieu_phoi(m)
            return
        if self.la_phu:                      # may phu: tin build / hoi dap la viec cua bot chinh
            return
        if bot_hoi_dap.la_cau_hoi(self, m):      # nhan rieng / tag bot -> hoi dap, khong doc nhu tin build
            await bot_hoi_dap.tra_loi_tin(self, m, REPO, OUT)
            return
        await bot_nhan_build.nhan_tin_build(self, m, OUT)

    async def _hoi_lai(self, m: discord.Message, tin: dict):
        await bot_nhan_build.hoi_lai(self, m, tin)

    async def _xep_verify(self, c: dict, kenh) -> None:
        await bot_nhan_build.xep_verify(self, c, kenh)

    # --- bam nut -------------------------------------------------------------------------
    def _duoc_duyet(self, user) -> bool:
        return user.id in self.duyet or (self.role and any(r.id == self.role for r in getattr(user, "roles", [])))

    async def on_interaction(self, it: discord.Interaction):
        if self.la_phu:                      # nut bam do bot chinh tra loi
            return
        await bot_nut_bam.xu_ly(self, it)

    async def _huy(self, it: discord.Interaction, c: dict):
        await bot_nut_bam.huy(self, it, c)

    async def _review_bug(self, it: discord.Interaction, hanh_dong: str, c: dict):
        await bot_nut_bam.review_bug(self, it, hanh_dong, c, REPO, OUT)

    async def _bao_dev(self, c: dict, tin: str, tin_qa: discord.Message, keys: list[str] = ()):
        """Bao o kenh rieng cua project (user chot 28/10/2026), tag dev duoc giao bug `keys`; khong gui duoc
        thi bao o kenh QA. Tra kenh da gui, None khi da phai bao o kenh QA."""
        return await bot_kenh_project.bao(self, c, tin, tin_qa, keys)

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
                may = None                   # khong biet may nao con -> khong canh mat may nhip nay
            if may is not None:
                try:                         # may dang chay luot mat ket noi qua han -> tu dung luot
                    await bot_canh_may.kiem(self, {d.serial for d in may})
                except Exception:            # noqa: BLE001 - canh may loi khong chan chia job
                    log.exception("canh may loi")
            may = may or []
            # Job chay xong nhung chua gui duoc ket qua truoc khi bot tat -> chi gui lai, khong can may.
            for job in self.q.lay_cho_gui():
                asyncio.create_task(self._chay_tren(job, "", job.get("ten_may") or "?"))
            for d in may:
                if d.serial in self.ban or bot_hang_doi.may_ban(bot_hang_doi.khoa_may(OUT, d.serial)):
                    continue
                job = self.q.lay()
                if job is None:
                    break
                self.ban[d.serial] = job["msg_id"]
                asyncio.create_task(self._chay_tren(job, d.serial, bot_cong_viec.ten_may(d.serial, d.model)))
            if self.dieu_phoi:
                try:
                    kenh_dp = await self._kenh_dieu_phoi()
                    for j in await bot_may_phu.thu_hoi_job_treo(self, kenh_dp):   # may phu tat han giua luot
                        try:
                            await (await self._kenh_qa()).send(
                                f"⚠️ {bot_cong_viec.dau_tin(j)} — máy phụ `{j['dang_o']}` không báo xong sau "
                                f"{bot_may_phu.HAN_MAY_PHU // 60} phút, bot đưa lượt về hàng đợi để chạy lại.")
                        except Exception as exc:   # noqa: BLE001 - job da ve hang, chi thieu tin bao
                            log.warning("khong bao duoc thu hoi job: %s", exc)
                    await bot_may_phu.chia_viec(self, kenh_dp)
                except Exception as exc:     # noqa: BLE001 - kenh dieu phoi loi khong chan may cua bot chinh
                    log.warning("chia viec may phu loi: %s", exc)
            await asyncio.sleep(5)

    async def _chay_tren(self, job: dict, serial: str, ten: str):
        def tra_may():                       # chi tra may con dang giu cho job nay (co the da giao job khac)
            if self.ban.get(serial) == job["msg_id"]:
                self.ban.pop(serial)

        async def mot_luot():
            if job.get("loai_job") == "verify":
                await bot_job_verify.chay(self, job, serial, ten, REPO, OUT)
            else:
                await self._chay(job, serial, ten)
        if serial:
            bot_tien_trinh.bat_dau(serial, job["msg_id"])   # bo dau Dung cua luot truoc tren may nay
        try:
            # May phu chi gui lai ngan (bot_gui_lai.HAN_GUI_LAI_MAY_PHU): qua HAN_MAY_PHU bot chinh thu hoi job.
            await bot_gui_lai.chay_toi_khi_gui_duoc(
                mot_luot, job, tra_may, han=bot_gui_lai.HAN_GUI_LAI_MAY_PHU if self.la_phu else None)
        except bot_tien_trinh.BiDung as exc:   # QA bam Dung: da giet ca cay tien trinh
            log.info("luot %s %s bi dung: %s", job.get("ma"), job.get("version"), exc)
            try:
                await bot_dung_luot.sau_khi_dung(self, job, serial, ten, str(exc))
            except Exception:                # noqa: BLE001
                log.exception("bao / don sau khi dung loi")
        except Exception as exc:             # noqa: BLE001 - mot job hong khong duoc giet bot
            log.exception("job loi")
            try:                             # mat mang thi bao loi cung hong -> chi ghi log
                await (await self._kenh_qa()).send(f"⛔ {bot_cong_viec.dau_tin(job)} [{ten}]: lỗi bot {exc}")
                await bot_forum.dat_nhan(self, job, bot_forum.CAN_XEM)
            except Exception as loi_bao:     # noqa: BLE001
                log.warning("khong bao duoc loi job: %s", loi_bao)
        finally:
            self.q.xong(job)
            tra_may()

    async def _chay(self, job: dict, serial: str, ten: str):
        await bot_job_check.chay(self, job, serial, ten, REPO, OUT)

    async def _cai_va_chay(self, job: dict, qa, serial: str, ten: str) -> bool:
        return await bot_job_check.cai_va_chay(self, job, qa, serial, ten, REPO, OUT)

    async def _bao_ket_qua(self, job: dict, qa):
        await bot_job_check.bao_ket_qua(self, job, qa, OUT)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    token = env("DISCORD_BOT_TOKEN")
    if not token:
        print("Thiếu DISCORD_BOT_TOKEN", flush=True)
        return 1
    BuildBot().run(token, log_handler=None)
    return 0
