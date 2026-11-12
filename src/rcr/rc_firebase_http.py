"""Tang goi HTTP cua Remote Config Firebase: thu lai loi tam (mang / 429 / 5xx) + nho access token + nho template.

Tach khoi `rc_firebase` (sua template) cho file khong vuot 200 dong.

Nho TEMPLATE + ETag theo project trong mot tien trinh: PUT tra ve chinh template vua publish kem ETag moi, nen
lan sua sau (restore cuoi case, patch case sau) PUT thang voi If-Match = ETag do, khong GET lai. Nguoi khac (may
kia dung chung testvsl) vua publish -> 412 -> doc lai roi gan lai: If-Match van chan ghi de thay doi cua nguoi khac.
"""

from __future__ import annotations

import copy
import gzip
import time
import urllib.error

THU_MANG = 4          # loi mang (VPN / handshake timeout, do 31/10/2026) -> thu lai
CHO_MANG = 5.0
TIMEOUT = 30
# 429 = vuot han muc goi API Remote Config (gap 12/11/2026 khi chay lien tuc nhieu case) - cung la loi tam.
LOI_TAM = (429, 500, 502, 503, 504)
CHO_LOI_TAM = 20.0
CHO_TOI_DA = 60.0

# Access token OAuth song 3600s - nho 50 phut, khong doi lai moi lan goi (truoc day 2 lan / lan sua).
TOKEN_SONG = 3000.0
_TOKEN: dict[str, tuple[str, float]] = {}
# project -> (template, etag, luc nho) cua lan doc / publish gan nhat trong tien trinh nay.
_MAU: dict[str, tuple[dict, str, float]] = {}
# Template nho chi dung lai trong MAU_SONG giay (patch case sau ngay sau restore case truoc). Lau hon thi GET lai
# truoc khi PUT: do vivo 12/11/2026, PUT voi ETag cua lan PUT ~60s truoc 4/5 lan treo 10s roi 5xx (mat ~15s ca
# thu lai), con PUT ngay sau GET (cach cu) 6/6 lan qua, PUT cach PUT truoc ~4s cung qua.
MAU_SONG = 20.0


def _cho_lai(exc: urllib.error.HTTPError, lan: int) -> float:
    """Giay cho truoc lan thu sau: theo Retry-After cua server neu co; 429 (het han muc theo phut) tang dan 20s,
    40s, 60s; 5xx tam thoi (PUT treo 10s roi loi, vivo 12/11/2026 - lan thu lai ngay sau la qua) chi 5s, 10s, 15s."""
    try:
        sau = float((exc.headers or {}).get("Retry-After") or 0)
    except (TypeError, ValueError):
        sau = 0.0
    if sau > 0:
        return min(CHO_TOI_DA, sau)
    return min(CHO_TOI_DA, (CHO_LOI_TAM if exc.code == 429 else CHO_MANG) * (lan + 1))


def _mang(goi):
    """Goi `goi()`; loi ket noi / timeout -> thu lai THU_MANG lan roi RcError (run_batch bat RcError tung case,
    URLError tran ra la chet ca luot - AIP886 31/10/2026). HTTPError: chi thu lai loi tam cua server (429 / 5xx) -
    09/11/2026 RC tra 503 bon lan trong mot buoi, moi lan dung ca luot; loi khac (401, 412...) nem ngay."""
    from .models import RcError

    for lan in range(THU_MANG):
        try:
            return goi()
        except urllib.error.HTTPError as exc:
            if exc.code not in LOI_TAM or lan == THU_MANG - 1:
                raise
            time.sleep(_cho_lai(exc, lan))
        except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
            if lan == THU_MANG - 1:
                raise RcError(f"không kết nối được Firebase sau {THU_MANG} lần: {exc}") from None
            time.sleep(CHO_MANG)


def _than_loi(e: urllib.error.HTTPError) -> str:
    """Than loi Firebase (co the gzip) -> chu doc duoc, toi da 300 ky tu."""
    raw = e.read()
    if e.headers.get("Content-Encoding") == "gzip" or raw[:2] == b"\x1f\x8b":
        try:
            raw = gzip.decompress(raw)
        except OSError:
            pass
    return raw[:300].decode("utf-8", "replace")


def token_nho(lay) -> str:
    """Access token con han trong bo nho, het thi `lay()` token moi roi nho lai."""
    co = _TOKEN.get("tok")
    if co and co[1] > time.monotonic():
        return co[0]
    tok = lay()
    _TOKEN["tok"] = (tok, time.monotonic() + TOKEN_SONG)
    return tok


def nho_mau(project: str, t: dict | None, etag: str) -> None:
    """Ghi template + ETag vua doc / vua publish. Thieu ETag hoac template khong ro rang -> quen (lan sau GET)."""
    if t is None or not etag or "conditions" not in t:
        _MAU.pop(project, None)
        return
    _MAU[project] = (copy.deepcopy(t), etag, time.monotonic())


def mau_da_nho(project: str) -> tuple[dict, str] | None:
    """Template + ETag da nho con trong MAU_SONG giay, khong thi None (nguoi goi GET lai)."""
    co = _MAU.get(project)
    if not co or time.monotonic() - co[2] > MAU_SONG:
        return None
    return copy.deepcopy(co[0]), co[1]


def quen(project: str | None = None) -> None:
    """Quen template da nho (412 / test)."""
    if project is None:
        _MAU.clear()
        _TOKEN.clear()
    else:
        _MAU.pop(project, None)
