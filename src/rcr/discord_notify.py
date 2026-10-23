"""Thong bao Discord (Webhook) cho luot /rc-check - chi stdlib.

URL webhook lay tu env `DISCORD_WEBHOOK_URL`, KHONG BAO GIO in ra hay ghi vao repo.
Gui hong (khong env, mang loi, HTTP loi, qua 5s) chi tra False + mot dong stderr:
thong bao la tien nghi, khong duoc lam doi stdout / exit code cua luot chay.
`DISCORD_NOTIFY=0` tat han viec gui (test dat san trong conftest).

    rcr-notify --kind stop --title "..." --line "..." [--line ...] [--action ...] [--link URL]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request

ENV_URL = "DISCORD_WEBHOOK_URL"
ENV_SWITCH = "DISCORD_NOTIFY"
TIMEOUT_S = 5
MAX_LEN = 2000
# Cloudflare truoc Discord chan UA mac dinh cua urllib (Python-urllib/x.y).
USER_AGENT = "qa-workflow-bot/1.0"

EMOJI = {"stop": "⛔", "done": "✅", "bug": "🐞"}


def _warn(msg: str) -> None:
    print(f"discord: {msg}", file=sys.stderr, flush=True)


def build_text(kind: str, title: str, lines: list[str], action: str | None = None,
               link: str | None = None) -> str:
    """Noi dung Discord markdown, cat ve 2000 ky tu (gioi han cua Discord)."""
    rows = [f"{EMOJI[kind]} **rc-check** · {title}"]
    rows += list(lines)
    if action:
        rows.append(f"→ {action}")
    if link:
        rows.append(f"[Mở report](<{link}>)")  # <> tat embed xem truoc
    text = "\n".join(rows)
    return text if len(text) <= MAX_LEN else text[:MAX_LEN - 1] + "…"


def send(kind: str, title: str, lines: list[str], action: str | None = None,
         link: str | None = None) -> bool:
    """Gui mot tin. True khi Discord nhan (2xx); moi truong hop khac -> False, khong raise."""
    try:
        if os.environ.get(ENV_SWITCH, "").strip() == "0":
            return False
        url = os.environ.get(ENV_URL, "").strip()
        if not url:
            _warn(f"{ENV_URL} chưa đặt, bỏ qua thông báo")
            return False
        if kind not in EMOJI:
            _warn(f"kind không hợp lệ: {kind!r}")
            return False
        if not url.lower().startswith(("https://", "http://")):
            # Chan file:// va scheme la cua urllib; khong in URL ra.
            _warn(f"{ENV_URL} không phải URL http(s), bỏ qua thông báo")
            return False
        body = json.dumps({"content": build_text(kind, title, lines, action, link),
                           "allowed_mentions": {"parse": ["roles", "users"]}},
                          ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            url, data=body, method="POST",
            headers={"Content-Type": "application/json", "User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:  # noqa: S310 - scheme da kiem
            if 200 <= resp.status < 300:
                return True
            _warn(f"HTTP {resp.status}, thông báo không gửi được")
            return False
    except Exception as exc:  # noqa: BLE001 - thong bao khong duoc lam hong luot chay
        # Chi in loai loi / ma HTTP: thong diep goc co the chua URL webhook.
        code = getattr(exc, "code", None)
        _warn(f"gửi thất bại ({'HTTP ' + str(code) if code else type(exc).__name__})")
        return False


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(prog="rcr-notify", description="Gửi một tin Discord (luôn exit 0).")
    p.add_argument("--kind", required=True, choices=sorted(EMOJI))
    p.add_argument("--title", required=True)
    p.add_argument("--line", action="append", default=[], help="một dòng nội dung (lặp lại được)")
    p.add_argument("--action")
    p.add_argument("--link")
    try:
        args = p.parse_args(argv)
    except SystemExit:
        return 0  # sai tham so cung khong duoc lam hong luot chay cua nguoi goi
    send(args.kind, args.title, args.line, args.action, args.link)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
