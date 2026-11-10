"""Kenh Forum `qa-builds`: moi build mot bai, tin dau bai la tin goc (user chot 10/11/2026).

qa-auto (kenh van ban) lan tin build moi voi ket qua -> nhieu build thi phai vuot len tim. Forum tu day bai vua
cap nhat len dau va loc duoc theo nhan trang thai. Tat (DISCORD_FORUM_CHANNEL_ID rong) thi moi tin goc o qa-auto
nhu cu.

- Id tin dau bai == id thread nen `msg_id` (khoa cua job / nut bam) giu nguyen y nghia.
- Tin goc khac cua CUNG build (verify, hoi lai, check-sub) gui vao bai do; `tin[msg_id].kenh_id` = id thread
  de `_tin_qa` biet tim tin o dau. Tin cu khong co kenh_id -> qa-auto.
- Nhan do QA tao tay trong kenh (bot khong co quyen Manage Channels); bot khop theo ten, thieu thi bo qua.
"""

from __future__ import annotations

import logging

import discord

log = logging.getLogger("rcr-bot")

CHO_DUYET, DANG_CHAY, PASS, FAIL, CAN_XEM = "Chờ duyệt", "Đang chạy", "PASS", "FAIL", "Cần xem"
LUU_TRU_PHUT = 10080          # bai tu archive sau 7 ngay khong hoat dong


def bat(bot) -> bool:
    return bool(getattr(bot, "kenh_forum", 0))


def kenh_cua(msg) -> dict:
    """{"kenh_id": id thread} khi tin nam trong bai Forum - them vao tin truoc khi `nho_tin`."""
    return {"kenh_id": msg.channel.id} if isinstance(getattr(msg, "channel", None), discord.Thread) else {}


def ten_bai(c: dict) -> str:
    ten = f" · {c['ten']}" if c.get("ten") else ""
    return f"{c.get('ma', '')} · {c.get('version', '')}{ten}"[:100]


def bai_cua_build(bot, c: dict) -> int | None:
    """Id bai Forum da co cua build (cung ma app + version), moi nhat truoc."""
    cung = [t for t in bot.q.tin.values()
            if t.get("kenh_id") and t.get("ma") == c.get("ma") and t.get("version") == c.get("version")]
    return int(max(cung, key=lambda t: int(t["msg_id"]))["kenh_id"]) if cung else None


async def _kenh(bot, kenh_id: int):
    return bot.get_channel(kenh_id) or await bot.fetch_channel(kenh_id)


def _nhan(forum, ten: str) -> list:
    return [t for t in getattr(forum, "available_tags", []) if t.name.casefold() == ten.casefold()][:1]


async def gui_goc(bot, c: dict, noi_dung: str, gui_cu=None, **k) -> discord.Message:
    """Gui mot tin goc cua build `c`. Forum tat -> `gui_cu(noi_dung)` (mac dinh gui o qa-auto). Build da co bai
    -> gui vao bai; chua co -> tao bai moi (tag nguoi duyet de co thong bao, nhan Cho duyet)."""
    gui = gui_cu or (await bot._kenh_qa()).send
    if not bat(bot):
        return await gui(noi_dung, **k)
    tid = bai_cua_build(bot, c)
    if tid:
        try:
            # Gui tin vao bai da archive thi Discord tu mo lai bai.
            return await (await _kenh(bot, tid)).send(noi_dung, **k)
        except discord.HTTPException as exc:        # bai bi xoa / khoa -> tao bai moi
            log.warning("khong gui duoc vao bai %s: %s - tao bai moi", tid, exc)
    try:
        forum = await _kenh(bot, bot.kenh_forum)
        if not isinstance(forum, discord.ForumChannel):
            raise TypeError(f"kenh {bot.kenh_forum} khong phai kenh Forum")
        tag = " ".join(f"<@{u}>" for u in sorted(getattr(bot, "duyet", ()) or ()))
        # Bai chi co luot verify: khong nhan Cho duyet (verify khong doi nhan nen se ket mai o do).
        nhan = [] if c.get("loai_job") == "verify" else _nhan(forum, CHO_DUYET)
        moi = await forum.create_thread(name=ten_bai(c), content=f"{noi_dung}\n{tag}".strip(),
                                       applied_tags=nhan, auto_archive_duration=LUU_TRU_PHUT, **k)
        return moi.message
    except Exception as exc:                        # noqa: BLE001 - Forum sai cau hinh / thieu quyen: khong mat build
        log.warning("khong tao duoc bai Forum (%s) - gui o qa-auto", exc)
        return await gui(noi_dung, **k)


async def dat_nhan(bot, c: dict, ten: str) -> None:
    """Doi nhan trang thai cua bai chua build `c`. Chi luot check / sub; loi thi chi ghi log."""
    kid = c.get("kenh_id")
    if not kid and c.get("msg_id"):                 # job tao tu ban cu cua tin: lay kenh_id o tin cua build
        kid = (bot.q.tin_cua(c["msg_id"]) or {}).get("kenh_id")
    if not bat(bot) or not kid or c.get("loai_job") == "verify":
        return
    try:
        bai = await _kenh(bot, int(kid))
        nhan = _nhan(getattr(bai, "parent", None), ten)
        if nhan:
            await bai.edit(applied_tags=nhan, archived=False)   # bai da archive: sua bi tu choi neu khong mo lai
        else:
            log.info("forum chua co nhan %r - bo qua", ten)
    except Exception as exc:                        # noqa: BLE001 - nhan hong khong duoc chan luot chay
        log.warning("khong doi duoc nhan %r: %s", ten, exc)


async def mo_lai(kenh) -> None:
    """Bai Forum da archive (7 ngay im) -> mo lai, khong thi sua tin trong bai bi Discord tu choi."""
    if isinstance(kenh, discord.Thread) and kenh.archived:
        try:
            await kenh.edit(archived=False)
        except discord.HTTPException as exc:
            log.warning("khong mo lai duoc bai %s: %s", kenh.id, exc)


def link_tin(bot, job: dict, link_kenh: str) -> str:
    """Link nhay toi tin goc. `link_kenh` = .../<server>/<kenh QA>; tin trong bai Forum thi thay id kenh = id bai."""
    kid = job.get("kenh_id") or (bot.q.tin_cua(job["msg_id"]) or {}).get("kenh_id")
    goc = f"{link_kenh.rsplit('/', 1)[0]}/{kid}" if kid else link_kenh
    return f"{goc}/{job['msg_id']}"


def nhan_ket_qua(kq: dict) -> str:
    """XONG + co bug -> FAIL, XONG khong bug -> PASS, con lai (Dung / Loi / Het gio) -> Can xem."""
    if kq.get("trang_thai") != "XONG":
        return CAN_XEM
    return FAIL if kq.get("bugs") else PASS
