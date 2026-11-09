"""Luot chay TAY (terminal) bao Discord bang cach them dong vao TIN GOC cua build o kenh QA, khong gui tin moi.

User chot 09/11/2026: moi thay doi chi doi trang thai cua mot tin goc (bot_tin_goc). Luot chay tay khong qua
bot (vd Claude publish report roi goi `rcr-artifact`) truoc day gui tin "✅ rc-check · Report da publish" rieng.
Tin goc = tin bot luu trong `out/bot-hang-doi.json` (truong `tin`, khoa msg_id) cung package, moi nhat.
Chi stdlib; token KHONG BAO GIO in ra. Loi bat ky -> False (noi goi gui tin moi nhu cu).
"""
from __future__ import annotations

import json
import urllib.request
from pathlib import Path

from . import cau_hinh_bot

HANG_DOI = Path(__file__).resolve().parents[2] / "out" / "bot-hang-doi.json"
API = "https://discord.com/api/v10"
USER_AGENT = "qa-workflow-bot/1.0"
TIMEOUT_S = 5
MAX_LEN = 2000


def msg_id_goc(package: str, path: Path = HANG_DOI) -> str:
    """msg_id tin goc moi nhat cua package ('' neu bot chua co tin nao cua package)."""
    try:
        tin = json.loads(path.read_text(encoding="utf-8")).get("tin") or {}
    except (OSError, ValueError):
        return ""
    hop = [k for k, c in tin.items() if isinstance(c, dict) and c.get("package") == package and str(k).isdigit()]
    return max(hop, key=int) if hop else ""


def _goi(method: str, url: str, token: str, payload: dict | None = None) -> dict:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        "Authorization": f"Bot {token}", "User-Agent": USER_AGENT, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=TIMEOUT_S) as r:  # noqa: S310 - URL co dinh discord.com
        return json.load(r)


def them_dong(package: str, dong: str, path: Path = HANG_DOI) -> bool:
    """Them `dong` vao cuoi content cua tin goc cua package. True khi sua duoc."""
    token = cau_hinh_bot.env("DISCORD_BOT_TOKEN")
    kenh = cau_hinh_bot.env("DISCORD_QA_CHANNEL_ID")
    mid = msg_id_goc(package, path)
    if not (token and kenh.isdigit() and mid):
        return False
    try:
        url = f"{API}/channels/{kenh}/messages/{mid}"
        cu = _goi("GET", url, token).get("content") or ""
        chu = f"{cu}\n{dong}" if cu else dong
        _goi("PATCH", url, token, {"content": chu if len(chu) <= MAX_LEN else chu[:MAX_LEN - 1] + "…"})
        return True
    except Exception:  # noqa: BLE001 - khong sua duoc thi noi goi gui tin moi
        return False
