"""Report cua luot chay o may PHU -> hang cho publish cua bot CHINH.

Phien Claude Code publish artifact (`rcr-publish`) chi chay tren may bot chinh va chi doc `out/cho-publish.json`
cua may do; `bot_cho_publish.vong_lap` cung chi chay o bot chinh. Truoc day may phu ghi report vao hang cho cua
chinh no -> khong ai publish, tin ket qua dung mai o dong "⏳ đang publish" (AIP892 chay o laptop 12/11/2026).

Nay may phu gui file HTML sang bot chinh qua kenh dieu phoi (`RCR report <may>`: JSON + file HTML), bot chinh luu
vao `out/tu-may-phu/` roi `bot_cho_publish.them` voi dung kenh / tin goc -> vong_lap thay link + canh bao 15 phut
nhu luot chay o may chinh. File qua gioi han dinh kem / Discord tu choi -> ghi hang cho cuc bo + canh bao log
(khong bo report). Loi mang thi nem ra cho `bot_gui_lai` goi lai ca buoc bao ket qua.
"""

from __future__ import annotations

import hashlib
import logging
import re
from pathlib import Path

import discord

from . import bot_cho_publish, bot_cong_viec, bot_gui_lai, bot_may_phu

log = logging.getLogger("rcr-bot")
THU_MUC = "tu-may-phu"
LOAI = "report"
DU_JSON = 64 * 1024   # chua cho file rcr.json di cung tin


def gioi_han(kenh) -> int:
    """Byte toi da cua file HTML: gioi han dinh kem cua server (khong boost = 10MB) tru phan JSON."""
    toi_da = getattr(getattr(kenh, "guild", None), "filesize_limit", None) or bot_cong_viec.MAX_DINH_KEM
    return int(toi_da) - DU_JSON


async def them(bot, out: Path, f: Path, kenh_id: int, msg_id: int, ten: str = "", khoa: str = "") -> None:
    """Thay cho `bot_cho_publish.them` o noi bao ket qua. Bot chinh (hoac khong co kenh dieu phoi) -> hang cho
    cuc bo nhu cu; may phu -> gui sang bot chinh. `khoa`: ma job (log / tra cuu), khong bat buoc."""
    if not getattr(bot, "la_phu", False) or not getattr(bot, "dieu_phoi", 0):
        bot_cho_publish.them(out, f, kenh_id, msg_id, ten)
        return
    kenh = await bot._kenh_dieu_phoi()
    co = Path(f).stat().st_size
    if co > gioi_han(kenh):
        log.warning("report %s (%d byte) qua gioi han dinh kem -> giu o hang cho may phu, bot chinh KHONG publish",
                    f, co)
        bot_cho_publish.them(out, f, kenh_id, msg_id, ten)
        return
    d = {"may": bot.ten_may, "kenh_id": int(kenh_id), "msg_id": int(msg_id), "ten": ten, "khoa": khoa,
         "file": Path(f).name}
    try:
        await bot_may_phu.gui(kenh, LOAI, d, kem=discord.File(str(f), Path(f).name))
        log.info("da gui report %s sang bot chinh (tin %s)", Path(f).name, msg_id)
    except bot_gui_lai.LOI_MANG:
        raise                                   # bot_gui_lai goi lai bao ket qua, buoc nay chua danh dau da_bao
    except discord.HTTPException as exc:        # 413 / 4xx: gui lai vo ich -> giu cuc bo, khong bo report
        log.warning("khong gui duoc report %s sang bot chinh (%s) -> giu o hang cho may phu", f, exc)
        bot_cho_publish.them(out, f, kenh_id, msg_id, ten)


def ten_an_toan(may: str, msg_id: int, ten_goc: str, noi_dung: bytes) -> str:
    """Ten file trong `out/tu-may-phu/`: chi ky tu an toan, khong co thu muc (chong path traversal), them may +
    tin + hash noi dung -> luot chay lai cung build khong ghi de report cu da publish."""
    sach = lambda s: re.sub(r"[^A-Za-z0-9._-]", "_", s).strip("._") or "x"   # noqa: E731
    goc = sach(Path(str(ten_goc).replace("\\", "/")).name)[:80]
    if not goc.lower().endswith(".html"):
        goc += ".html"
    return f"{sach(may)[:40]}-{int(msg_id)}-{hashlib.sha1(noi_dung).hexdigest()[:8]}-{goc}"


async def nhan_o_may_chinh(bot, m, d: dict) -> Path | None:
    """Bot chinh nhan `RCR report`: luu HTML vao `out/tu-may-phu/` roi dua vao hang cho publish nhu luot cua minh.
    Tin phat lai (cung noi dung) -> cung ten file -> `bot_cho_publish.them` khong them lan hai."""
    html = next((a for a in m.attachments if getattr(a, "filename", "") != bot_may_phu.TEN_JSON), None)
    if html is None:
        log.warning("tin report tu %s thieu file HTML: bo qua", d.get("may"))
        return None
    noi_dung = await html.read()
    thu_muc = Path(bot.out) / THU_MUC
    thu_muc.mkdir(parents=True, exist_ok=True)
    p = thu_muc / ten_an_toan(str(d.get("may") or "phu"), int(d["msg_id"]), d.get("file") or html.filename, noi_dung)
    p.write_bytes(noi_dung)
    bot_cho_publish.them(bot.out, p, int(d["kenh_id"]), int(d["msg_id"]), str(d.get("ten") or ""))
    log.info("report tu may %s (%s) -> hang cho publish: %s", d.get("may"), d.get("khoa"), p.name)
    return p
