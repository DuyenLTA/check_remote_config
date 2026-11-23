"""Tu don Forum `qa-builds` theo plan tuan (user chot 23/11/2026): app da release thi bai build chi lam roi Forum.

Moi CHU_KY giay tai lai plan tuan (`RC_PLAN_TUAN_SHEET`), doc tab tuan moi nhat da bat dau: dong app co cot
"Trạng thái" = Released -> xoa bai bot tao cua app do co version <= version da release. Bai version MOI HON giu lai:
dau tuan tab moi chua tao, build tuan nay khong duoc mat bai vi dong Released cua tuan truoc. Bai cua build con trong
hang doi / dang chay cung giu (lan sau don tiep). Plan chua cau hinh / tai hong -> chi ghi log, khong xoa gi.
Bo sung cho hai duong don da co: QA bao "test pass" o kenh project (`bot_testvsl`) va don Chu nhat.
"""

from __future__ import annotations

import asyncio
import datetime as dt
import logging
import os
import re

from . import bot_lenh_xoa_bai as x
from . import build_ma_app, plan_tuan

log = logging.getLogger("rcr-bot")
CHU_KY = 3600
DA_RELEASE_RE = re.compile(r"released?", re.I)
VER_RE = re.compile(r"(\d+)\.(\d+)\.(\d+)")


def _so(version: str) -> tuple[int, ...] | None:
    """'2.6.0 (16)' -> (2, 6, 0); khong co X.Y.Z -> None."""
    m = VER_RE.search(version or "")
    return tuple(int(s) for s in m.groups()) if m else None


def da_release(path, ngay: dt.date) -> dict[str, tuple[int, ...]]:
    """{ma app: version cao nhat co trang thai Released} trong tab tuan moi nhat bat dau <= `ngay`."""
    import openpyxl

    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        tab = [(t[0], w) for w in wb.worksheets if (t := plan_tuan.tuan_cua_tab(w.title)) and t[0] <= ngay]
        if not tab:
            return {}
        ra: dict[str, tuple[int, ...]] = {}
        cot: dict[str, int] = {}
        for r in max(tab, key=lambda c: c[0])[1].iter_rows(values_only=True):
            tieu_de = plan_tuan.cot_tieu_de(r)
            if tieu_de:                # bang khong co cot "Trạng thái" (bang cong viec theo ngay) -> bo ca bang
                tt = {plan_tuan._chuan(v): i for i, v in enumerate(r)}.get("trạng thái", -1)
                cot = {**tieu_de, "tt": tt} if tt >= 0 and tieu_de["ten"] >= 0 else {}
                continue
            if not cot:
                continue
            o = ["" if i >= len(r) or r[i] is None else str(r[i]).strip() for i in (cot["ten"], cot["version"], cot["tt"])]
            ma, ver = build_ma_app.MA_RE.match(o[0]), _so(o[1])
            if ma and ver and DA_RELEASE_RE.fullmatch(o[2]):
                ra[ma.group(1).upper()] = max(ver, ra.get(ma.group(1).upper(), ver))
        return ra
    finally:
        wb.close()


def chon_bai(bai: list, chu_bot: int, release: dict[str, tuple[int, ...]], dang_dung: set[int]) -> list:
    """Bai bot tao cua app da release, version <= version release, tru bai dang dung."""
    ra = []
    for t in bai:
        ma, ver = x._ma_ver(t.name)
        so = _so(ver)
        if getattr(t, "owner_id", None) == chu_bot and t.id not in dang_dung and so and ma in release \
                and so <= release[ma]:
            ra.append(t)
    return ra


async def don(bot, release: dict[str, tuple[int, ...]]) -> tuple[int, int, list[str]]:
    """Xoa bai cua app da release. Tra (da xoa, tong chon, loi)."""
    forum = bot.get_channel(bot.kenh_forum) or await bot.fetch_channel(bot.kenh_forum)
    chon = chon_bai(await x.tat_ca_bai(forum), bot.user.id, release, x.bai_dang_dung(bot))
    da, loi = await x.xoa(chon)
    return da, len(chon), loi


async def vong_lap(bot) -> None:
    await bot.wait_until_ready()
    while not bot.is_closed():
        link = os.environ.get(plan_tuan.ENV, "")
        if getattr(bot, "kenh_forum", 0) and link:
            try:
                path = await asyncio.to_thread(plan_tuan.tai, link, bot.out)
                release = await asyncio.to_thread(da_release, path, dt.date.today())
                da, tong, loi = await don(bot, release) if release else (0, 0, [])
                if tong:
                    log.info("don Forum theo plan: xoa %d/%d bai %s", da, tong, "; ".join(loi[:3]))
            except Exception as exc:          # noqa: BLE001 - plan / Discord loi khong duoc giet vong lap
                log.warning("don Forum theo plan loi: %s", exc)
        await asyncio.sleep(CHU_KY)
