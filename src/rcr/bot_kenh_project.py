"""Bao dev o kenh rieng cua project (tin bug vua log Jira, bug verify van FAIL).

Kenh project nam cung server voi kenh build cua dev, ten bat dau bang ma app viet thuong
(`aip920-ai-english-official-group`). Tag dev theo NGUOI DUOC GIAO (assignee Jira) cua cac bug trong tin
(user chot 29/10/2026: tag ca 2 dev khong on): bang `DISCORD_DEV_THEO_ASSIGNEE` = `ten:discord_id;...`
(ten hien thi hoac login Jira, khong phan biet dau / hoa thuong) - nam o cau hinh may vi repo public.
Bug chua giao cho dev trong bang (round dau, Jira tu gan nguoi mac dinh) -> tag dev da gui tin build, tim
theo ten Discord nguoi gui ('TrungHD', 'DungNT2' co trong bang - user chot 30/10/2026). Webhook / QA gui lai
tin build / Jira loi -> tag `DISCORD_DEV_IDS` nhu truoc.
Khong tim duoc kenh / bot khong co quyen gui (kenh Publishing) -> dang o kenh QA kem noi dung de QA chuyen tay.
"""

from __future__ import annotations

import asyncio
import logging
import re
import unicodedata

import discord

from . import bot_jira_rest as jira
from .cau_hinh_bot import env

log = logging.getLogger("rcr-bot")
LINK_RE = re.compile(r"/channels/(\d+)/(\d+)(?:/(\d+))?")


def dev_ids(gia_tri: str) -> list[int]:
    return [int(x) for x in (gia_tri or "").split(",") if x.strip().isdigit()]


def _chuan(ten: str) -> str:
    """'Nguyễn Tấn Dũng' -> 'nguyen tan dung' de so khop ten assignee."""
    s = unicodedata.normalize("NFD", ten or "").replace("đ", "d").replace("Đ", "D")
    return " ".join("".join(c for c in s if unicodedata.category(c) != "Mn").casefold().split())


def bang_dev(gia_tri: str) -> dict[str, int]:
    """`DISCORD_DEV_THEO_ASSIGNEE` ('Nguyễn Tấn Dũng:7847...;dungnt2:7847...') -> {ten chuan: discord id}."""
    ra = {}
    for phan in (gia_tri or "").split(";"):
        ten, _, i = phan.rpartition(":")
        if ten.strip() and i.strip().isdigit():
            ra[_chuan(ten)] = int(i)
    return ra


def la_bot_dev(i: int) -> bool:
    """Bot Assistant cua dev (id co trong bang tag dev) - tin build no gui van phai doc."""
    return i in bang_dev(env("DISCORD_DEV_THEO_ASSIGNEE")).values()


def dev_theo_ten(ten: str, bang: dict[str, int]) -> int | None:
    """Ten nguoi gui tin build ('trrung3894 TrungHD', 'DungNT2-Assistant') chua ten dev trong bang
    ('trunghd', 'dungnt2') -> id can tag."""
    s = _chuan(ten)
    return next((i for t, i in bang.items() if t in s), None)


def dev_theo_assignee(assignee: dict[str, list[str]], keys: list[str], bang: dict[str, int],
                      mac_dinh: list[int], gui_build: int | None = None) -> list[int]:
    """Discord id can tag cho cac bug `keys`; bug nao khong ra dev trong bang (build moi chua giao,
    Jira tu gan nguoi mac dinh cua project) -> them dev gui build, khong biet ai gui thi them `mac_dinh`."""
    ra, thieu = [], False
    for k in keys:
        i = next((bang[_chuan(t)] for t in assignee.get(k, []) if _chuan(t) in bang), None)
        if i is None:
            thieu = True
        elif i not in ra:
            ra.append(i)
    if thieu or not ra:
        ra += [i for i in ([gui_build] if gui_build else mac_dinh) if i not in ra]
    return ra


async def _dev_gui_build(bot, c: dict, bang: dict[str, int]) -> int | None:
    """Dev tu gui tin build ('TrungHD: e gui ban build') -> id cua dev do; webhook 'Build Notification'
    hay QA gui lai tin -> None. Doc tin loi cung None (van bao dev, tag nhu cu)."""
    m = LINK_RE.search(c.get("link_tin") or "")
    if not bang or not m or not m.group(3):
        return None
    try:
        kenh = bot.get_channel(int(m.group(2))) or await bot.fetch_channel(int(m.group(2)))
        tin = await kenh.fetch_message(int(m.group(3)))
    except Exception as exc:                 # noqa: BLE001 - khong doc duoc tin build khong duoc chan bao dev
        log.warning("khong doc duoc tin build %s: %s", c.get("link_tin"), exc)
        return None
    a = tin.author
    return dev_theo_ten(" ".join(filter(None, (a.name, getattr(a, "global_name", None),
                                               getattr(a, "nick", None)))), bang)


async def ids_can_tag(bot, keys: list[str], c: dict | None = None) -> list[int]:
    mac_dinh = dev_ids(getattr(bot, "dev_ids", ""))
    bang = bang_dev(env("DISCORD_DEV_THEO_ASSIGNEE"))
    gui_build = await _dev_gui_build(bot, c or {}, bang)
    du_phong = [gui_build] if gui_build else mac_dinh
    if not keys or not bang or not jira.bat(getattr(bot, "jira_url", ""), getattr(bot, "jira_token", "")):
        return du_phong
    try:
        a = await asyncio.to_thread(jira.assignee, bot.jira_url, bot.jira_token, keys)
    except jira.JiraLoi as exc:               # Jira loi: van bao dev, tag nhu cu
        log.warning("khong doc duoc assignee %s: %s", keys, exc)
        return du_phong
    return dev_theo_assignee(a, keys, bang, mac_dinh, gui_build)


def chon_kenh(kenh: list, ma: str, co_quyen) -> object | None:
    """Kenh text dau tien ten `<ma>-...` ma bot gui duoc (ma khop nguyen, `aip92` khong an `aip920-`)."""
    dau = f"{ma.lower()}-"
    return next((k for k in kenh if k.name.startswith(dau) and co_quyen(k)), None)


async def _kenh_project(bot, c: dict):
    """Uu tien server chua tin build; khong co thi tim o cac server khac bot dang o. QA hay gui lai
    tin build o kenh QA (server test, khong co kenh project) - luot AIP922 28/10/2026 hong vi vay."""
    m = LINK_RE.search(c.get("link_tin") or "")
    g_tin = bot.get_guild(int(m.group(1))) if m else None
    cac_server = [g_tin] if g_tin is not None else []
    cac_server += [g for g in getattr(bot, "guilds", None) or [] if g is not g_tin]
    for g in cac_server:
        def co_quyen(k, g=g) -> bool:
            p = k.permissions_for(g.me)
            return p.view_channel and p.send_messages

        kenh = chon_kenh(sorted(g.text_channels, key=lambda k: k.position), c.get("ma", ""), co_quyen)
        if kenh is not None:
            return kenh
    return None


async def bao(bot, c: dict, tin: str, tin_qa, keys: list[str] = ()):
    """Gui `tin` o kenh project cua `c['ma']`, tag dev theo assignee cua bug `keys`; that bai thi tra loi duoi
    `tin_qa`. Tra kenh da gui (None khi phai bao o kenh QA)."""
    try:
        ids = await ids_can_tag(bot, list(keys), c)
        tag = " ".join(f"<@{i}>" for i in ids)
        noi_dung = f"{tag}\n{tin}" if tag else tin
        kenh = await _kenh_project(bot, c)
        if kenh is not None:
            await kenh.send(noi_dung[:2000], allowed_mentions=discord.AllowedMentions(
                users=[discord.Object(i) for i in ids], roles=False, everyone=False))
            return kenh
        ly_do = f"không thấy kênh `{c.get('ma', '').lower()}-…` bot gửi được"
    except Exception as exc:             # noqa: BLE001 - bao dev hong khong duoc lam mat ket qua Jira
        log.warning("khong bao duoc dev o kenh project: %s", exc)
        ly_do = str(exc)
    await tin_qa.reply(f"⚠️ Không báo được dev ({ly_do}) — gửi tin này cho dev:\n{tin}"[:2000])
