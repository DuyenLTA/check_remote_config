"""Hang cho publish report thanh artifact claude.ai.

`claude -p` (bot chay lượt) khong co tool Artifact, nen bot KHONG dinh kem file HTML len Discord nua
(user chot 10/11/2026, nhac lai 11/11/2026: "dung gui html nua mat cong tai ve"). Thay vao do:

  1. Bot bao ket qua voi dong `CHO` ("đang publish"), ghi report vao `out/cho-publish.json` (`them`).
  2. Mot phien Claude Code THUONG (co tool Artifact) chay `/loop` tren may bot: `rcr-publish ds` lay danh sach,
     publish tung file, roi `rcr-publish xong <id> <url>` ghi link vao hang cho.
  3. Vong lap cua bot (`vong_lap`) thay link vao dung tin ket qua tren Discord; report cho qua `CANH_BAO_SAU`
     ma chua co link thi bao mot lan len kenh QA (phien publish chet / het dang nhap).

File hang cho la JSON nho, ghi ca file moi lan (bot va CLI chay khac tien trinh, it ghi) qua file tam + rename.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
import time
import uuid
from pathlib import Path

log = logging.getLogger(__name__)

TEN_FILE = "cho-publish.json"
CHO = "⏳ Report đang publish artifact…"
CANH_BAO_SAU = 15 * 60          # giay
CHU_KY = 30                     # giay giua hai lan bot quet hang cho


def _duong(out_dir: Path) -> Path:
    return Path(out_dir) / TEN_FILE


def doc(out_dir: Path) -> list[dict]:
    p = _duong(out_dir)
    try:
        return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else []
    except (OSError, json.JSONDecodeError) as exc:
        log.warning("hang cho publish hong (%s) - coi nhu rong", exc)
        return []


def _ghi(out_dir: Path, ds: list[dict]) -> None:
    p = _duong(out_dir)
    tam = p.with_suffix(".tmp")
    tam.write_text(json.dumps(ds, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tam, p)


def them(out_dir: Path, file: Path, kenh_id: int, msg_id: int, ten: str = "") -> str:
    """Ghi mot report cho publish. Cung tin + cung file thi khong them lan hai (bao ket qua goi lai duoc)."""
    ds = doc(out_dir)
    for m in ds:
        if m["msg_id"] == int(msg_id) and m["file"] == str(file):
            return m["id"]
    m = {"id": uuid.uuid4().hex[:8], "file": str(Path(file).resolve()), "ten": ten, "kenh_id": int(kenh_id),
         "msg_id": int(msg_id), "luc": time.time(), "url": "", "da_sua": False, "da_canh_bao": False}
    _ghi(out_dir, [*ds, m])
    return m["id"]


def chua_publish(out_dir: Path) -> list[dict]:
    return [m for m in doc(out_dir) if not m["url"]]


def xong(out_dir: Path, id_: str, url: str) -> dict:
    if not url.startswith("https://claude.ai/"):
        raise ValueError(f"link phai la artifact claude.ai: {url!r}")
    ds = doc(out_dir)
    for m in ds:
        if m["id"] == id_:
            m["url"] = url
            _ghi(out_dir, ds)
            return m
    raise KeyError(f"khong co report {id_!r} trong hang cho")


def thay_link(chu: str, url: str) -> str:
    """Doi dong CHO trong noi dung tin (embed/content) thanh link artifact."""
    return (chu or "").replace(CHO, f"Report: {url}")


async def _sua_tin(bot, m: dict) -> None:
    import discord   # chi can khi chay bot, de CLI `rcr-publish` khong phu thuoc discord.py

    kenh = bot.get_channel(m["kenh_id"]) or await bot.fetch_channel(m["kenh_id"])
    tin = await kenh.fetch_message(m["msg_id"])
    embeds = []
    for e in tin.embeds:
        if e.description and CHO in e.description:
            e = discord.Embed(title=e.title, description=thay_link(e.description, m["url"]), color=e.color)
        embeds.append(e)
    await tin.edit(content=thay_link(tin.content, m["url"]), embeds=embeds)


async def mot_vong(bot, out_dir: Path, bao_kenh) -> None:
    """Mot lan quet: sua tin da co link; canh bao report cho qua lau. `bao_kenh(chu)` gui len kenh QA."""
    ds, doi = doc(out_dir), False
    for m in ds:
        if m["url"] and not m["da_sua"]:
            try:
                await _sua_tin(bot, m)
                m["da_sua"] = doi = True
            except Exception as exc:          # noqa: BLE001 - tin bi xoa / mat mang: thu lai vong sau
                log.warning("chua sua duoc tin %s: %s", m["msg_id"], exc)
        elif not m["url"] and not m["da_canh_bao"] and time.time() - m["luc"] > CANH_BAO_SAU:
            await bao_kenh(f"⚠️ Report `{Path(m['file']).name}` ({m.get('ten') or '?'}) chờ publish artifact quá "
                           f"{CANH_BAO_SAU // 60} phút. Kiểm phiên Claude Code publish trên máy bot "
                           "(`tmux attach -t rcr-publish`).")
            m["da_canh_bao"] = doi = True
    # Giu 7 ngay gan nhat cho de tra cuu, bo muc da xong cu hon.
    con = [m for m in ds if not (m["da_sua"] and time.time() - m["luc"] > 7 * 86400)]
    if doi or len(con) != len(ds):
        _ghi(out_dir, con)


async def vong_lap(bot, out_dir: Path) -> None:
    async def bao(chu: str) -> None:
        kenh = await bot._kenh_qa()
        await kenh.send(chu)
    while True:
        try:
            await mot_vong(bot, out_dir, bao)
        except Exception:                     # noqa: BLE001 - vong nen khong duoc chet
            log.exception("vong hang cho publish loi")
        await asyncio.sleep(CHU_KY)


def main(argv: list[str] | None = None) -> int:
    """CLI cho phien Claude Code publish: `rcr-publish ds` | `rcr-publish xong <id> <url>`."""
    out_mac_dinh = Path(__file__).resolve().parents[2] / "out"   # = discord_bot.OUT, khong import ca bot

    ap = argparse.ArgumentParser(prog="rcr-publish", description="Hang cho publish report thanh artifact")
    sub = ap.add_subparsers(dest="lenh", required=True)
    sub.add_parser("ds", help="in JSON cac report chua publish")
    x = sub.add_parser("xong", help="ghi link artifact cho mot report")
    x.add_argument("id")
    x.add_argument("url")
    ap.add_argument("--out-dir", default=str(out_mac_dinh))
    a = ap.parse_args(argv)
    out = Path(a.out_dir)
    if a.lenh == "ds":
        print(json.dumps([{"id": m["id"], "file": m["file"], "ten": m.get("ten", "")} for m in chua_publish(out)],
                         ensure_ascii=False))
        return 0
    try:
        m = xong(out, a.id, a.url)
    except (KeyError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(f"OK {m['id']} -> {m['url']} (bot sua tin trong {CHU_KY}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
