"""Doc cau hinh bot (token, id kenh...) - dung chung cho `rcr-bot` va `rcr-notify`.

Thu tu: bien moi truong cua process -> bien User cua Windows (registry, dat bang setx /
SetEnvironmentVariable sau khi shell da mo van doc duoc) -> file `~/.config/rcr/bot.env`
(dong KEY=VALUE; systemd tren Ubuntu cung doc file nay). Chi stdlib: `rcr-notify` chay
duoc ca khi may khong cai extras `bot` (discord.py).
"""

from __future__ import annotations

import os
from pathlib import Path

FILE_CAU_HINH = Path.home() / ".config" / "rcr" / "bot.env"


def _doc_file_env(path: Path) -> dict[str, str]:
    """`KEY=VALUE` moi dong, bo dong trong / `#`, bo nhay boc ngoai. File thieu -> {}."""
    try:
        dong = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return {}
    ra = {}
    for d in dong:
        d = d.strip()
        if d and not d.startswith("#") and "=" in d:
            k, v = d.split("=", 1)
            ra[k.removeprefix("export ").strip()] = v.strip().strip("'\"")
    return ra


def env(ten: str, file_cau_hinh: Path = FILE_CAU_HINH) -> str:
    """Bien moi truong -> bien User cua Windows -> ~/.config/rcr/bot.env."""
    gt = os.environ.get(ten, "")
    if not gt and os.name == "nt":
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
                gt = str(winreg.QueryValueEx(k, ten)[0])
        except OSError:
            pass
    if not gt:
        gt = _doc_file_env(file_cau_hinh).get(ten, "")
    return gt.strip()
