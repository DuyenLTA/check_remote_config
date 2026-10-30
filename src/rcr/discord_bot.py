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
  DISCORD_DUYET_USER_IDS   id nguoi duoc bam nut (phay ngan cach)
  DISCORD_QA_ROLE_ID       (tuy) role duoc bam nut
  DISCORD_JIRA_REVIEWER    email/username Jira gan lam Reviewer cho bug log tu Discord
  DISCORD_DEV_IDS          id dev duoc tag khi bao bug o kenh project (phay ngan cach)
  JIRA_URL, JIRA_PERSONAL_TOKEN  (tuy) bat tu verify bug Reviewing
Nhieu may cam cung luc -> moi may chay mot build, cac may song song (build khac nhau).
"""

from __future__ import annotations

import asyncio
import logging
import socket
import time
from pathlib import Path

import discord

from . import (audit_tom_tat, bot_bat_tin_lo, bot_may_phu, bot_chay_claude, bot_cong_viec, bot_hang_doi, bot_job_verify, bot_hoi_dap, bot_kenh_project,
               bot_jira_rest, bot_keo_sprint, bot_log_jira, build_ma_app, cai_apk_tu_drive)
from .adb_client import AdbClient
from .cau_hinh_bot import FILE_CAU_HINH, env  # noqa: F401 - dung chung voi rcr-notify
from .adb_parsers import AdbError

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "out"
log = logging.getLogger("rcr-bot")
CHO_JIRA, SO_LAN_JIRA = 5 * 60, 6     # Jira mat ket noi khi xep verify: thu lai moi 5 phut, toi da 30 phut



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


async def _tha_tim(m) -> None:
    """Tha ❤️ vao tin bao build de dev biet bot da nhan. Thieu quyen Add Reactions / tin da xoa -> bo qua,
    khong duoc chan viec hoi QA."""
    try:
        await m.add_reaction("❤️")
    except Exception as exc:                 # noqa: BLE001
        log.warning("khong tha tim duoc vao tin build %s: %s", getattr(m, "jump_url", ""), exc)


XANH, XAM = discord.ButtonStyle.success, discord.ButtonStyle.secondary
NUT_HOI = (("check", "Check", XANH), ("bo", "Bỏ qua", XAM), ("verify", "Verify bug Jira", XAM))
# QA gui lai tin build: tin hoi moi chi mang thong tin build, khong mang ket qua / bug / Jira cua luot cu.
GIU_KHI_HOI_LAI = ("ma", "ten", "version", "next_gen", "tutorial", "sdk", "package", "loai_ban")
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

    async def setup_hook(self):
        if self.la_phu:
            asyncio.create_task(self._vong_may_phu())
            return
        asyncio.create_task(self.worker())
        asyncio.create_task(bot_keo_sprint.vong_lap(self))   # bug log luc chua co sprint -> keo vao sprint moi

    async def on_ready(self):
        """Moi lan ket noi (ca reconnect sau mat mang - session bi huy thi Discord khong gui lai tin cu, 30/10/2026):
        phat lai tin build bi lo. Build da hoi roi thi tu bo, quet lai khong hoi trung."""
        if self.la_phu:
            return
        lan_dau = not getattr(self, "_da_quet_tin_lo", False)
        self._da_quet_tin_lo = True
        if lan_dau and self.dieu_phoi:       # may phu xin lai viec ngay, khong doi XIN_LAI
            try:
                await bot_may_phu.gui(await self._kenh_dieu_phoi(), "chinh_khoi_dong", {"may": "chinh"})
            except Exception as exc:         # noqa: BLE001
                log.warning("khong bao duoc may phu: %s", exc)
        try:
            log.info("quet tin build bi lo: %d tin", await bot_bat_tin_lo.quet(self))
        except Exception:                    # noqa: BLE001 - quet loi khong duoc lam chet bot
            log.exception("quet tin build bi lo loi")

    async def _tin_qa(self, msg_id: int) -> discord.Message:
        return await self.get_channel(self.kenh_qa).fetch_message(msg_id)

    # --- tin build -> hoi o kenh QA ----------------------------------------------------
    def bi_mat(self) -> list[str]:
        """Gia tri phai che trong moi cau tra loi gui len Discord."""
        return [env("DISCORD_BOT_TOKEN"), self.jira_token, env("DISCORD_WEBHOOK_URL")]

    async def _hoi_lai(self, m: discord.Message, tin: dict):
        """Build da hoi roi, QA gui lai tin build o kenh QA -> tin hoi MOI (nut Check) tra loi ngay duoi tin
        QA vua gui, bo phien cu. Truoc day bot bat lai nut o tin cu va gui link -> QA bi day len tin cu
        (user phan nan 29/10/2026). Tin cu giu nguyen (con menu log bug / ket qua). Dang cho/chay thi chi
        bao trang thai ngay duoi, khong tao luot trung. Dev bao trung o kenh khac thi van im (o noi goi)."""
        cung = [t for t in self.q.tin.values()
                if t.get("ma") == tin["ma"] and t.get("version") == tin["version"] and t.get("loai_job") != "verify"]
        if any(self.q.vi_tri(t["msg_id"]) is not None for t in cung):
            await m.reply(f"Build **{tin['ma']}** `{tin['version']}` đang chờ / đang chạy — xong bot báo kết quả.",
                          mention_author=False)
            return
        c_cu = max(cung, key=lambda t: int(t["msg_id"]))   # snowflake tang dan -> lan hoi gan nhat
        qa = await m.reply(f"**{c_cu['ma']}** `{c_cu['version']}`…", mention_author=False)
        c = {k: c_cu[k] for k in GIU_KHI_HOI_LAI if k in c_cu}
        c.update(link_tin=m.jump_url, msg_id=qa.id)
        self.q.nho_tin(c)
        await qa.edit(content=bot_cong_viec.tin_hoi(c), view=_nut(*NUT_HOI, msg_id=qa.id))

    async def _nhan_link_drive(self, m: discord.Message) -> bool:
        """QA tra loi tin hoi cua bot kem link Google Drive (ban debug) -> gan link vao build do: bam Check /
        Verify thi tai APK tu link thay cho App Tester (user chot 29/10/2026). True khi da xu ly tin nay."""
        ref = getattr(getattr(m, "reference", None), "message_id", None)
        c = self.q.tin_cua(ref) if ref and m.channel.id == self.kenh_qa else None
        link = cai_apk_tu_drive.tim_link(m.content or "") if c is not None else ""
        if not link or not self._duoc_duyet(m.author):
            return False
        c["drive"] = link
        self.q.nho_tin(c)
        try:                                     # tin hoi cu ghi ro se tai tu Drive
            cu = await self._tin_qa(ref)
            if c.get("loai_job") != "verify":
                await cu.edit(content=bot_cong_viec.tin_hoi(c), view=_nut(*NUT_HOI, msg_id=cu.id))
        except discord.HTTPException:
            pass
        await m.reply(f"📦 Đã nhận link Drive cho **{c['ma']}** `{c['version']}` — bấm **Check** / **Verify** ở tin "
                      "hỏi, bot sẽ tải APK từ link này thay cho App Tester.", mention_author=False)
        return True

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
        if not m.author.bot and await self._nhan_link_drive(m):
            return
        if bot_hoi_dap.la_cau_hoi(self, m):      # nhan rieng / tag bot -> hoi dap, khong doc nhu tin build
            await bot_hoi_dap.tra_loi_tin(self, m, REPO, OUT)
            return
        # dev bao build qua webhook "Build Notification" (author.bot=True) hoac bot Assistant cua dev
        # (DungNT2-Assistant, co trong bang tag dev) -> nhan; bo bot khac
        if m.author.bot and not m.webhook_id and not bot_kenh_project.la_bot_dev(m.author.id):
            return
        # Chi nhan build o kenh rieng cua tung project (`aip922-...`, moi server bot dang o) va kenh trong
        # DISCORD_BUILD_CHANNEL_ID (qa-auto). Kenh chung build-notification bo tu 30/10/2026 (user chot: chat
        # thuong o do bi bot hoi nham la tin build).
        o_kenh_build = m.channel.id in self.kenh_build
        ma_kenh = "" if o_kenh_build else build_ma_app.ma_cua_kenh(
            getattr(getattr(m.channel, "parent", None) or m.channel, "name", ""))
        if not o_kenh_build and not (ma_kenh and m.guild):
            return
        # QA nhan o kenh project ("test pass v1.4.0(14)... rls") khong phai tin bao build: khong tha tim, khong hoi
        # (user chot 30/10/2026 - bot tha tim nham vao tin bao rls AIP805). QA gui lai build thi gui o qa-auto.
        if m.channel.id != self.kenh_qa and not m.webhook_id and self._duoc_duyet(m.author):
            return
        chu = noi_dung(m)
        tin = build_ma_app.tach(chu, ma_kenh)
        kenh = self.get_channel(self.kenh_qa)
        if tin is None:
            # Khong bam mau cau: tin webhook (bao build tu dong) hoac tin co ma app ma khong doc ra
            # version -> hoi QA. Kenh project con chat thuong nen chi hoi voi tin webhook.
            # Kenh QA cung la kenh build (QA gui lai tin build de chay lai), nhung webhook o day la
            # thong bao cua chinh cac tool (audit, rc-check) chu khong phai tin bao build -> bo qua.
            if m.webhook_id and m.channel.id == self.kenh_qa:
                return
            if m.webhook_id or (o_kenh_build and build_ma_app.co_ma_app(chu)):
                await kenh.send(f"Bot không đọc được mã app + version (dạng `AIP922 v3.7.0 (30)`) "
                                f"trong tin báo build — QA xem giúp: {m.jump_url}")
            return
        if m.channel.id != self.kenh_qa:     # tin build cua dev: tha tim bao da nhan (user chot 30/10/2026)
            await _tha_tim(m)
        cu = [t for t in self.q.tin.values() if t.get("ma") == tin["ma"] and t.get("version") == tin["version"]]
        if cu:
            # Giai doan chuyen kenh dev co the bao mot build o ca kenh chung lan kenh project.
            log.info("build da hoi roi: %s %s (%s)", tin["ma"], tin["version"], m.jump_url)
            # QA gui lai tin build de chay lai -> tro ve tin Check cu (build chi co luot verify thi khong co tin Check)
            if m.channel.id == self.kenh_qa and any(t.get("loai_job") != "verify" for t in cu):
                await self._hoi_lai(m, tin)
            return
        pkg = await asyncio.to_thread(bot_cong_viec.package_cua, tin["ma"], OUT)
        if not tin["sdk"]:
            # Build chuc nang / fix bug, khong apply SDK: khong hoi Check (chua co workflow, user chot 28/10/2026)
            # nhung VAN verify bug dev da keo Reviewing - build fix bug thuong khong ghi SDK (user chot 28/10/2026).
            log.info("build khong apply SDK, chi verify bug Reviewing: %s %s", tin["ma"], tin["version"])
            if pkg:
                await self._xep_verify({**tin, "package": pkg, "loai_ban": build_ma_app.loai_ban(tin),
                                        "link_tin": m.jump_url}, kenh)
            return
        if not pkg:
            await kenh.send(f"Sheet Check thông số KT không có package của **{tin['ma']}** — {m.jump_url}")
            return
        qa = await kenh.send(f"**{tin['ma']}** `{tin['version']}`…")
        c = {**tin, "package": pkg, "loai_ban": build_ma_app.loai_ban(tin), "link_tin": m.jump_url, "msg_id": qa.id}
        self.q.nho_tin(c)
        await qa.edit(content=bot_cong_viec.tin_hoi(c), view=_nut(*NUT_HOI, msg_id=qa.id))
        await self._xep_verify(c, kenh)

    async def _xep_verify(self, c: dict, kenh) -> None:
        """Tim bug bot da log cua app dang Reviewing -> xep luot verify tren build `c`."""
        # Mang toi Jira chap chon vai phut (VPN) -> im lang doi roi thu lai, chi bao QA khi het luot van loi
        # (user phan nan 30/10/2026: bao loi ket noi tieng Anh ngay lan dau, ma app khong co bug Reviewing nao).
        for lan in range(SO_LAN_JIRA):
            try:                             # loi verify khong duoc lam hong tin Check vua gui
                tom_tat = await bot_job_verify.xep(self, c, kenh)
                log.info("verify %s: %s", c["ma"], tom_tat)
                return
            except bot_jira_rest.JiraMatKetNoi as exc:
                log.warning("verify %s: Jira chua ket noi duoc (lan %d): %s", c["ma"], lan + 1, exc)
                if lan < SO_LAN_JIRA - 1:
                    await asyncio.sleep(CHO_JIRA)
            except Exception as exc:         # noqa: BLE001
                log.exception("xep verify loi")
                await kenh.send(f"⚠️ Không kiểm được bug Reviewing của **{c['ma']}**: {exc}"[:2000])
                return
        await kenh.send(f"⚠️ Chưa kiểm được bug Reviewing của **{c['ma']}** `{c['version']}`: Jira không kết nối "
                        f"được suốt {SO_LAN_JIRA * CHO_JIRA // 60} phút (VPN?). Kết nối lại thì bấm **Verify bug Jira** "
                        f"ở tin Check, build không có tin Check thì gửi lại tin build để bot kiểm lại.")

    # --- bam nut -------------------------------------------------------------------------
    def _duoc_duyet(self, user) -> bool:
        return user.id in self.duyet or (self.role and any(r.id == self.role for r in getattr(user, "roles", [])))

    async def on_interaction(self, it: discord.Interaction):
        if self.la_phu:                      # nut bam do bot chinh tra loi
            return
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
        if hanh_dong == "verify":
            await it.response.defer(ephemeral=True, thinking=True)
            try:
                tom_tat = await bot_job_verify.xep(self, c, self.get_channel(self.kenh_qa))
            except Exception as exc:         # noqa: BLE001 - loi Jira tra ve cho nguoi bam
                log.exception("verify lai loi")
                tom_tat = f"⛔ Lỗi: {exc}"
            await it.followup.send(tom_tat[:2000], ephemeral=True)
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
            await it.response.edit_message(content=bot_cong_viec.tin_bug(bugs, c["bug_chon"], c),
                                           view=_view_bug(bugs, c["bug_chon"], msg_id))
            return
        if hanh_dong == "khongbug":
            c["jira"] = {"issues": [], "loi": ""}
            self.q.nho_tin(c)
            await it.response.edit_message(content=f"{bot_cong_viec.tin_bug(bugs, None, c)}\n"
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
        await it.response.edit_message(content=f"{bot_cong_viec.tin_bug(bugs, chon, c)}\n"
                                       f"Đang log {len(chon)} bug lên Jira ({c['ma']}) — {it.user.mention}", view=None)
        try:
            # Gan bug cho dev gui build, khong de Jira tu gan nguoi mac dinh cua project (user chot 30/10/2026)
            dev = await bot_kenh_project.login_jira_gui_build(self, c)
            kq = await asyncio.to_thread(bot_log_jira.chay, [bugs[i] for i in chon], {**c, "dev_jira": dev},
                                         c.get("link_report", ""), self.reviewer, REPO, OUT)
        except Exception as exc:             # noqa: BLE001 - loi luot log khong duoc giet bot
            log.exception("log jira loi")
            await it.message.edit(view=_view_bug(bugs, chon, msg_id))   # tra menu lai de bam thu lai
            await it.message.reply(f"⛔ Log Jira lỗi: {exc}")
            return
        finally:
            self.dang_log.discard(msg_id)
        so = len([i for i in kq.get("issues") or [] if i.get("key")])
        if not so:
            # Khong tao duoc issue nao (Jira / MCP loi) -> chua tinh la da log: tra menu de bam thu lai.
            await it.message.reply(bot_cong_viec.tin_jira(kq, len(chon)))
            await it.message.edit(view=_view_bug(bugs, chon, msg_id))
            return
        c["jira"] = kq
        self.q.nho_tin(c)
        tin_dev = bot_cong_viec.tin_bao_dev(c, kq, [bugs[i] for i in chon])
        keys = [i["key"] for i in kq.get("issues") or [] if i.get("key")]
        kenh_dev = await self._bao_dev(c, tin_dev, it.message, keys) if tin_dev else None
        # Log du + bao duoc dev o kenh project -> khong dang them tin o kenh QA (user chot 28/10/2026),
        # chi sua dong trang thai cua tin menu. Thieu issue / Jira bao loi / khong bao duoc dev -> bao o QA.
        if kenh_dev is not None and so == len(chon) and not kq.get("loi"):
            await it.message.edit(content=f"{bot_cong_viec.tin_bug(bugs, chon, c)}\n"
                                          f"✅ Đã log {so} bug, đã báo dev ở {kenh_dev.mention} — {it.user.mention}")
        else:
            await it.message.reply(bot_cong_viec.tin_jira(kq, len(chon)))

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
                may = []
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
                    await bot_may_phu.chia_viec(self, await self._kenh_dieu_phoi())
                except Exception as exc:     # noqa: BLE001 - kenh dieu phoi loi khong chan may cua bot chinh
                    log.warning("chia viec may phu loi: %s", exc)
            await asyncio.sleep(5)

    async def _chay_tren(self, job: dict, serial: str, ten: str):
        try:
            if job.get("loai_job") == "verify":
                await bot_job_verify.chay(self, job, serial, ten, REPO, OUT)
            else:
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
        nguon = "từ link Drive" if job.get("drive") else "từ App Tester"
        await qa.edit(content=f"{dau}\nĐang cài bản {job['loai_ban']} {nguon}…")
        cai = await asyncio.to_thread(bot_cong_viec.cai, job["package"], job["version"], job["loai_ban"], serial,
                                      job.get("drive", ""))
        if "loi" in cai:
            # Thuong la App Tester chua co ban (dev chua day) -> hoi link Drive, de nguoi bam thu lai sau.
            hoi = bot_cong_viec.hoi_link_drive(job)
            await qa.edit(content=f"{dau}\n⛔ Cài không được: {cai['loi']}" + (f"\n{hoi}" if hoi else ""),
                          view=_nut(("check", "Thử lại", XANH), ("bo", "Bỏ qua", XAM), msg_id=qa.id))
            return
        ghi = " (đã gỡ bản cũ khác loại — mất data app)" if cai.get("go_ban_cu") else ""
        await qa.edit(content=f"{dau}\nĐã cài{ghi}. Đang chạy /rc-check…")
        await qa.reply(bot_cong_viec.tin_da_cai(job, ten, "/rc-check"))
        next_gen = build_ma_app.la_next_gen(job)
        timeout = bot_chay_claude.TIMEOUT_NEXT_GEN if next_gen else bot_chay_claude.TIMEOUT_BO_TC
        bat_dau = time.time()
        # Tin build ghi next-gen -> ep rc-check nhanh checklist; con lai bo TC (ban release doi RC qua Firebase).
        kq = await asyncio.to_thread(bot_chay_claude.chay, job["package"], serial, REPO, timeout, OUT,
                                     None, next_gen, job.get("tutorial") or "")
        chu = bot_cong_viec.TRANG_THAI.get(kq["trang_thai"], ("", kq["trang_thai"]))[1]
        await qa.edit(content=f"{dau}\n{chu}")
        f = bot_cong_viec.file_report(kq, OUT)
        # Tom tat ID ads doc bang code (dung package, ghi trong luot nay), khong theo chu Claude viet.
        # Trang audit day du nam trong tab cua chinh report -> chi dinh kem mot file report.
        audit = audit_tom_tat.tim(job["package"], tu_luc=bat_dau)
        files = [discord.File(f)] if f else []
        await qa.reply((bot_cong_viec.tin_ket_qua(job, kq, f) + f"\nMáy: {ten}\n{audit_tom_tat.dong_tin(audit)}")[:2000],
                       files=files or discord.utils.MISSING,
                       view=_nut(("verify", "Verify bug Jira", XAM), msg_id=job["msg_id"]))
        if kq.get("bugs"):
            # Luu vao tin cua build: bot khoi dong lai van tick / log tiep duoc.
            c = {**(self.q.tin_cua(job["msg_id"]) or job), "bugs": kq["bugs"], "bug_chon": [],
                 # link_report la duong dan file chi khi file do thuc su duoc dinh kem (tin_bug ghi "đính kèm")
                 "link_report": kq.get("link", "") if kq.get("link", "").startswith("https://") else str(f or ""),
                 "jira": None}
            self.q.nho_tin(c)
            # Chua publish duoc artifact -> dinh kem luon file report vao tin bug: QA phai mo duoc report
            # ngay tai tin can review, khong phai keo len tim tin ket qua.
            await qa.reply(bot_cong_viec.tin_bug(kq["bugs"], None, c), files=[discord.File(f)] if f else discord.utils.MISSING,
                           view=_view_bug(kq["bugs"], [], job["msg_id"]))


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    token = env("DISCORD_BOT_TOKEN")
    if not token:
        print("Thiếu DISCORD_BOT_TOKEN", flush=True)
        return 1
    BuildBot().run(token, log_handler=None)
    return 0
