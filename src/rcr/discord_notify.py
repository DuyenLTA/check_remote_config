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
import re
import sys
import urllib.request
import uuid
from pathlib import Path

ENV_URL = "DISCORD_WEBHOOK_URL"
ENV_SWITCH = "DISCORD_NOTIFY"
TIMEOUT_S = 5
# Upload report vai MB qua mang cham: 5s la het gio giua chung.
TIMEOUT_FILE_S = 60
MAX_LEN = 2000
# Webhook Discord nhan file toi 10 MiB (server khong boost). Chua le cho phan
# con lai cua body multipart.
MAX_FILE = 9 * 1024 * 1024
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


def _doc_dinh_kem(file: Path | None) -> tuple[bytes | None, str]:
    """-> (noi dung file, dong ghi chu them vao tin). File qua lon / doc hong thi
    van gui tin, chi ghi duong dan local - mat tin vi file la mat ca thong bao."""
    if file is None:
        return None, ""
    try:
        if file.stat().st_size > MAX_FILE:
            return None, f"Report quá lớn để đính kèm, mở trên máy chạy: {file}"
        return file.read_bytes(), ""
    except OSError:
        return None, f"Không đọc được report để đính kèm: {file}"


def _multipart(payload: dict, file_name: str, data: bytes) -> tuple[bytes, str]:
    """Body multipart/form-data Discord doc: `payload_json` + `files[0]`."""
    ranh = uuid.uuid4().hex
    crlf = "\r\n"
    dau = (f"--{ranh}{crlf}"
           f'Content-Disposition: form-data; name="payload_json"{crlf}'
           f"Content-Type: application/json{crlf}{crlf}"
           + json.dumps(payload, ensure_ascii=False)
           + f"{crlf}--{ranh}{crlf}"
           f'Content-Disposition: form-data; name="files[0]"; filename="{file_name}"{crlf}'
           f"Content-Type: text/html{crlf}{crlf}").encode("utf-8")
    return dau + data + f"{crlf}--{ranh}--{crlf}".encode("utf-8"), ranh


def send(kind: str, title: str, lines: list[str], action: str | None = None,
         link: str | None = None, file: Path | None = None) -> bool:
    """Gui mot tin. True khi Discord nhan (2xx); moi truong hop khac -> False, khong raise.

    `file`: dinh kem file (report HTML) - dung khi khong co Claude publish artifact.
    """
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
        data, ghi_chu = _doc_dinh_kem(file)
        if ghi_chu:
            lines = [*lines, ghi_chu]

        def noi_dung(dong) -> dict:
            return {"content": build_text(kind, title, dong, action, link),
                    "allowed_mentions": {"parse": ["roles", "users"]}}

        if data is not None:
            if _post(url, noi_dung(lines), (_ten_file(file), data)):
                return True
            # Upload hong (mang cham, file lon) khong duoc lam mat ca tin.
            _warn("gửi kèm report hỏng, gửi lại tin không kèm file")
            lines = [*lines, f"Không gửi kèm được report, mở trên máy chạy: {file}"]
        return _post(url, noi_dung(lines), None)
    except Exception as exc:  # noqa: BLE001 - thong bao khong duoc lam hong luot chay
        _warn(f"gửi thất bại ({type(exc).__name__})")
        return False


def _ten_file(file: Path) -> str:
    """Ten file an toan cho header Content-Disposition (khong dau, khong nhay)."""
    return re.sub(r"[^A-Za-z0-9._-]", "_", file.name) or "report.html"


def _post(url: str, payload: dict, dinh_kem: tuple[str, bytes] | None) -> bool:
    """Mot request toi webhook. True khi 2xx; moi loi -> False, khong raise."""
    try:
        if dinh_kem is not None:
            body, ranh = _multipart(payload, *dinh_kem)
            loai = f"multipart/form-data; boundary={ranh}"
        else:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            loai = "application/json"
        req = urllib.request.Request(
            url, data=body, method="POST",
            headers={"Content-Type": loai, "User-Agent": USER_AGENT})
        timeout = TIMEOUT_FILE_S if dinh_kem is not None else TIMEOUT_S
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 - scheme da kiem
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
