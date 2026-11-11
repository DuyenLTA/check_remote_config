"""Dev bao lai CUNG ma app + version (build lai ma khong tang so version) -> bot coi la build moi.

Tach khoi `bot_nhan_build` (nhan tin build). Ham cua `bot_nhan_build` goi qua `nb.` luc chay (import vong).
"""

from __future__ import annotations

from pathlib import Path

import discord

from . import bot_kenh_project
from .bot_giao_dien import noi_dung


def _nb():
    from . import bot_nhan_build
    return bot_nhan_build


# Tin dev cach lan hoi gan nhat it hon muc nay khong tinh la day lai: dev dang cheo nhieu kenh gan nhu cung luc.
CHEO_KENH_MS = 15 * 60 * 1000


def _ms(snowflake) -> int:
    """Moc thoi gian (ms, lech goc co dinh) cua snowflake Discord - chi dung de so hai tin voi nhau."""
    return int(snowflake) >> 22


def la_dev_day_lai(bot, m: discord.Message, cu: list[dict]) -> bool:
    """Tin bao build MOI cua dev (webhook / bot Assistant cua dev) trung ma + version voi build da hoi: dev build
    lai ma khong tang so version. Khong tinh: tin da xu ly (link trung `link_tin`), tin cu hon / gan lan hoi gan nhat
    (quet lai tin lo moi lan reconnect phat lai tin cu; build hoi qua /check luu link rong), tin khong phai bao build
    (dev Assistant tra loi "da fix tren v3.9.0 (32)")."""
    if not (m.webhook_id or bot_kenh_project.la_bot_dev(m.author.id)):
        return False
    if "build" not in noi_dung(m).lower() or m.jump_url in {t.get("link_tin") for t in cu}:
        return False
    return _ms(m.id) - _ms(max(int(t["msg_id"]) for t in cu)) > CHEO_KENH_MS


async def dev_day_lai(bot, tin: dict, link_tin: str, kenh, out: Path) -> None:
    """Dev day lai CUNG version (build moi that, vd AIP922 3.9.0 (32) ngay 11/11/2026 them TikTok config + ads-core
    2.0.1 - truoc day bot im). Build da hoi Check -> hoi Check lai (cai ban moi nhat tu App Tester, SDK theo tin moi);
    lan dau khong ghi SDK ma lan nay co -> hoi Check nhu build moi. Lan nao cung xep verify bug Reviewing (hang doi
    cho luot cung package chay lan luot). Moi tin dev chi xu ly mot lan (`bao_lan_dau`): reconnect khong bao lap."""
    nb = _nb()
    if not bot.q.bao_lan_dau(f"day_lai|{link_tin}"):
        return
    check = [t for t in nb.tin_da_hoi(bot, tin) if t.get("loai_job") in (None, "check")]
    if not check:
        if tin.get("sdk"):
            await nb.hoi_build_moi(bot, tin, link_tin, kenh, out)    # hoi Check + xep verify
            return
    else:
        doi = {k: tin[k] for k in ("next_gen", "tutorial", "sdk") if k in tin} if tin.get("sdk") else None
        kq = await nb.hoi_lai_build(bot, tin, link_tin, kenh.send, doi)
        if kq.startswith("Build"):       # dang cho / dang chay: khong tao luot trung, bao tren tin goc cua luot do
            dang = next((t for t in check if bot.q.vi_tri(t["msg_id"]) is not None),
                        max(check, key=lambda t: int(t["msg_id"])))
            await nb._canh_bao(bot, dang, kenh, f"🔁 Dev đẩy lại `{tin['version']}` (cùng version) lúc lượt này đang "
                                             f"chờ / chạy — xong lượt thì QA gửi lại tin build để chạy bản mới: {link_tin}")
    moi = max(nb.tin_da_hoi(bot, tin), key=lambda t: int(t["msg_id"]))
    await bot._xep_verify({**moi, "link_tin": link_tin}, kenh)
