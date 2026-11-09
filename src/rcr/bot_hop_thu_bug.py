"""Hop thu bug: luot chay TAY (terminal, khong qua bot) dua danh sach bug len kenh QA cho QA tick + Log Jira.

User chot 05/11/2026: luot chay tay xong co bug thi hoi QA ngay trong qa-auto, khong hoi o terminal.
Bot giu hang doi trong RAM nen tien trinh khac khong ghi thang `bot-hang-doi.json` duoc (bot ghi de).
Thay vao do `rcr-bao-bug` tha mot file JSON vao `out/bot-hop-thu-bug/`; bot chinh quet dinh ky, gan bug vao
tin cua build (giong luot bot tu chay) roi tra loi duoi tin do: menu tick bug dat len chinh tin goc. Tu luc do nut
tick / Log Jira / Khong co bug that chay y het luot cua bot.

File: {"msg_id": <tin cua bot o kenh QA> | null, "package": "...", "version": "1.9.0 (14)",
       "link_report": "https://claude.ai/...", "bugs": [{case, tieu_de, precondition, buoc, expected, thuc_te, muc_do}]}
Khong co `msg_id` thi tim tin build moi nhat cung package (+ version neu co).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
import time
from pathlib import Path

from . import bot_chay_claude, bot_cong_viec
from . import bot_tin_goc as tin_goc

log = logging.getLogger("rcr-bot")
THU_MUC = "bot-hop-thu-bug"
CHU_KY = 20               # giay giua 2 lan quet hop thu


def tim_tin(tin: dict[str, dict], package: str, version: str = "") -> dict | None:
    """Tin build moi nhat (msg_id lon nhat) cung package, cung version neu truyen."""
    hop = [c for c in tin.values() if c.get("package") == package
           and (not version or str(c.get("version") or "").strip() == version.strip())]
    return max(hop, key=lambda c: int(c["msg_id"])) if hop else None


def gan_bug(c: dict, bugs: list[dict], link: str) -> dict:
    """Tin build + bug cho QA review; reset lua chon / ket qua Jira cu (giong bot_job_check)."""
    return {**c, "bugs": bugs, "bug_chon": [], "link_report": link, "jira": None}


async def dang_menu(bot, qa, c: dict) -> None:
    """Luu bug vao tin cua build (bot khoi dong lai van tick tiep duoc) roi dat menu bug len CHINH tin goc
    (embed "Bug can review" + menu tick + nut Verify) - khong tra loi tin moi (bot_tin_goc)."""
    bot.q.nho_tin(c)
    await qa.edit(embeds=tin_goc.thay(qa, tin_goc.embed(tin_goc.BUG, bot_cong_viec.tin_bug(c["bugs"], None, c))),
                  view=view_menu_bug(c, []))


def view_menu_bug(c: dict, chon: list[int] | None):
    """Menu tick bug + nut Verify bug Jira tren tin goc. `chon` None = da xu ly xong (chi con nut Verify)."""
    from .bot_giao_dien import XAM, nut, view_bug
    verify = nut(("verify", "Verify bug Jira", XAM), msg_id=int(c["msg_id"]))
    if chon is None:
        return verify
    return tin_goc.view_gop(view_bug(c["bugs"], chon, int(c["msg_id"])), verify)


async def xu_ly_file(bot, f: Path) -> str:
    """Mot file hop thu -> dang menu. Tra mo ta ket qua; loi thi doi ten file .loi kem ly do de nguoi xem."""
    try:
        d = json.loads(f.read_text(encoding="utf-8"))
        bugs = bot_chay_claude.doc_bugs(d.get("bugs"))
        if not bugs:
            raise ValueError("file khong co bug hop le (moi bug can truong `case`)")
        c = bot.q.tin_cua(int(d["msg_id"])) if d.get("msg_id") else tim_tin(
            bot.q.tin, str(d.get("package") or ""), str(d.get("version") or ""))
        if not c:
            raise ValueError(f"khong thay tin build cua {d.get('msg_id') or d.get('package')} {d.get('version') or ''}")
        await dang_menu(bot, await bot._tin_qa(int(c["msg_id"])), gan_bug(c, bugs, str(d.get("link_report") or "")))
        f.unlink()
        return f"da dang {len(bugs)} bug cho {c.get('ma')} {c.get('version')}"
    except Exception as exc:              # noqa: BLE001 - mot file hong khong chan file khac
        f.with_suffix(".loi").write_text(f"{exc}\n\n{f.read_text(encoding='utf-8', errors='replace')}",
                                         encoding="utf-8")
        f.unlink(missing_ok=True)
        return f"loi {f.name}: {exc}"


async def vong_lap(bot) -> None:
    hop = Path(bot.out) / THU_MUC
    while True:
        try:
            await bot.wait_until_ready()
            for f in sorted(hop.glob("*.json")):
                log.info("hop thu bug: %s", await xu_ly_file(bot, f))
        except Exception:                 # noqa: BLE001 - vong lap khong duoc chet
            log.exception("hop thu bug loi")
        await asyncio.sleep(CHU_KY)


def tha_vao_hop(out: Path, bugs: list[dict], link: str, msg_id: int | None = None,
                package: str = "", version: str = "") -> Path:
    """Ghi file hop thu (tmp roi doi ten: bot khong doc file viet do)."""
    hop = Path(out) / THU_MUC
    hop.mkdir(parents=True, exist_ok=True)
    f = hop / f"bug-{int(time.time() * 1000)}.json"
    tmp = f.with_suffix(".tmp")
    tmp.write_text(json.dumps({"msg_id": msg_id, "package": package, "version": version, "link_report": link,
                               "bugs": bugs}, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(f)
    return f


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="rcr-bao-bug",
                                description="Dua bug cua luot chay tay len kenh QA (menu tick + Log Jira) qua bot dang chay.")
    p.add_argument("--bugs", required=True, help="file JSON: danh sach bug (case, tieu_de, precondition, buoc, "
                                                 "expected, thuc_te, muc_do)")
    p.add_argument("--link", default="", help="link artifact report (claude.ai)")
    p.add_argument("--msg-id", type=int, default=None, help="tin cua bot o kenh QA cho build nay")
    p.add_argument("--package", default="", help="khong co --msg-id: tim tin build moi nhat cua package")
    p.add_argument("--version", default="", help="loc them theo version, vd '1.9.0 (14)'")
    p.add_argument("--out", default=str(Path(__file__).resolve().parents[2] / "out"))
    a = p.parse_args(argv)
    if not a.msg_id and not a.package:
        p.error("can --msg-id hoac --package")
    bugs = bot_chay_claude.doc_bugs(json.loads(Path(a.bugs).read_text(encoding="utf-8")))
    if not bugs:
        print("LOI: file khong co bug hop le (moi bug can truong `case`)", file=sys.stderr)
        return 1
    if a.link and not a.link.startswith("https://"):
        print("LOI: --link phai la link https (QA mo report tu Discord)", file=sys.stderr)
        return 1
    f = tha_vao_hop(Path(a.out), bugs, a.link, a.msg_id, a.package, a.version)
    print(json.dumps({"file": str(f), "bugs": len(bugs)}, ensure_ascii=False))
    return 0
