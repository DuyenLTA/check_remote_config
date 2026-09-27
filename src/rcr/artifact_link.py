"""Link artifact cua report - do Claude publish roi ghi vao day.

Tool KHONG publish duoc artifact: no chay o 127.0.0.1, khong co duong nao toi
claude.ai. Nhung URL artifact la CO DINH (republish cung file giu nguyen URL),
nen biet URL mot lan la du - lan sau chi can republish de thay noi dung.

Bat buoc luu kem `generated_at` cua LUOT da publish. Thieu no thi khong phan
biet duoc link dang tro toi luot vua chay hay mot luot cu - va gui nham bao cao
cu cho team la sai mot cach im lang.
"""

from __future__ import annotations

import json
from pathlib import Path

TEN_FILE = "artifact.json"


def duong_dan(goc: Path | None = None) -> Path:
    return (goc or Path("out")) / TEN_FILE


def doc(goc: Path | None = None) -> dict:
    """{url, generated_at} - rong neu chua publish lan nao.

    File hong/thieu KHONG duoc lam hong luot chay: link artifact chi la tien
    nghi, con report local van mo duoc bang nhay doi.
    """
    try:
        data = json.loads(duong_dan(goc).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}
    url = str(data.get("url") or "")
    if not url.startswith("https://"):
        return {}
    return {"url": url, "generated_at": str(data.get("generated_at") or "")}


def ghi(url: str, generated_at: str, goc: Path | None = None) -> dict:
    path = duong_dan(goc)
    path.parent.mkdir(parents=True, exist_ok=True)
    ban = {"url": url, "generated_at": generated_at}
    path.write_text(json.dumps(ban, ensure_ascii=False, indent=2), encoding="utf-8")
    return ban
