"""Mo thang trang app trong App Tester bang deep link, khong cuon danh sach tim app.

VI SAO: danh sach App Tester ~93 app (29/10/2026), cuon tung trang de tim bundle mat hang phut va co luc khong
thay app (App Tester nho vi tri cuon cu, dong bi cat o mep man). App Tester (v0.133) nhan link
`https://appdistribution.firebase.google.com/testerapps/<firebase app id>` va mo NGAY trang chi tiet cua app
(do Pixel 6 09/11/2026: am start -> trang AIP872 sau 58ms).

App id (`google_app_id` trong APK) khong co trong tin build -> nho theo package vao `out/app-tester-app-id.json`:
ghi moi lan tool doc APK cua app (`rc_firebase_app.thong_tin_tren_may`: baseline RC, kiem testvsl) va truoc khi
go ban cu luc cai build. Chua biet app id (app chua tung qua may nay) -> app_tester_ui cuon tim nhu cu.
"""
from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path

from .app_sandbox import guard

CACHE = Path(__file__).resolve().parents[2] / "out" / "app-tester-app-id.json"
LINK = "https://appdistribution.firebase.google.com/testerapps/{app_id}"
APP_ID_RE = re.compile(r"^1:\d+:android:[0-9a-f]+$")
CHO_MO_S = 2.0
LAN_DOI = 4


def _doc_cache(path: Path = CACHE) -> dict[str, str]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def doc(package: str, path: Path = CACHE) -> str:
    v = _doc_cache(path).get(package, "")
    return v if APP_ID_RE.match(v) else ""


def ghi(package: str, app_id: str, path: Path = CACHE) -> None:
    """Nho app id cua package. Loi ghi file khong duoc lam hong luot (chi la loi tat)."""
    if not package or not APP_ID_RE.match(app_id or "") or doc(package, path) == app_id:
        return
    try:
        bang = _doc_cache(path) | {package: app_id}
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(bang, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    except OSError:
        pass


async def nho(client, serial: str, package: str) -> str:
    """App id cua package: cache, khong co thi doc APK dang cai (goi TRUOC khi go app). '' neu khong biet."""
    co = doc(package)
    if co:
        return co
    from . import rc_firebase_app
    try:
        return (await rc_firebase_app.thong_tin_tren_may(client, serial, package)).get("app_id", "")
    except Exception:  # noqa: BLE001 - chua cai / keo APK hong -> cuon tim nhu cu
        return ""


async def mo(client, serial: str, package: str, app_id: str, doc_man, man_cua) -> list | None:
    """Mo trang app bang link. Tra nodes khi da o trang chi tiet (dung package) hoac man consent, None neu khong.

    `doc_man(client, serial)` / `man_cua(nodes)`: ham dump + nhan man cua app_tester_ui (tranh vong import).
    """
    guard(serial)
    if not app_id:
        return None
    await client.shell(serial, "am", "start", "-a", "android.intent.action.VIEW",
                       "-d", LINK.format(app_id=app_id), "dev.firebase.appdistribution")
    for _ in range(LAN_DOI):
        await asyncio.sleep(CHO_MO_S)
        nodes = await doc_man(client, serial)
        man = man_cua(nodes)
        if man == "consent":
            return nodes
        if man == "chi_tiet" and any(n.resource_id == "bundle_id" and n.text == package for n in nodes):
            return nodes
    return None
