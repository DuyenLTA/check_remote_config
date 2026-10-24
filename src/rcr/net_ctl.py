"""Bat/tat mang tren may test, cho case doi hoi "mo app khi mat mang".

VI SAO PHAI CO: buoc "Mo app khong mang" khop LAUNCH_RE va thanh NoOp - ve
"khong mang" bi bo im, case chay voi mang day du roi bao PASS. Do la PASS gia:
ca case chi de hoi "mat mang co lam SDK request len unit da tat khong".

Tat bang `svc wifi disable` + `svc data disable`, KHONG bang airplane mode:
`cmd connectivity airplane-mode` doi root tren may test. adb di qua USB nen
tat mang khong lam mat duong dieu khien.

Bat lai thi PHAI CHO den khi mang that su thong (do 2026-09-28 tren 29301FDH:
`svc wifi enable` tra ve ngay, nhung ping chi di duoc sau ~4 giay). Bao "da co
mang" trong khi chua co la lam hong dung cai buoc dang test.
"""

from __future__ import annotations

import asyncio
import logging
import re

from .app_sandbox import guard

log = logging.getLogger(__name__)

# Cau bao TAT mang. "mo app khong mang", "tat mang truoc khi mo app", "mat mang".
TAT_RE = re.compile(
    r"(?:t[ắa]t|ng[ắa]t|m[ấa]t|(?:kh[ôo]ng|ko)\s*(?:c[óo]\s*)?|no)\s*"
    r"(?:m[ạa]ng|internet|wifi|network|k[ếe]t\s*n[ốo]i)",
    re.I,
)
# Cau bao BAT LAI mang. Phai kiem TRUOC TAT_RE: "bat lai mang" khong chua tu
# tat nao, nhung "khoi phuc ket noi mang" thi co the lan voi cau tat.
BAT_RE = re.compile(
    r"(?:b[ậa]t|m[ởo]|kh[ôo]i\s*ph[ụu]c|ph[ụu]c\s*h[ồo]i|restore|enable)\s*(?:l[ạa]i\s*)?"
    r"(?:m[ạa]ng|internet|wifi|network|k[ếe]t\s*n[ốo]i)",
    re.I,
)
# Tat mang phai xay ra TRUOC khi app khoi dong. Precondition noi thang dieu do.
TRUOC_KHI_MO_RE = re.compile(r"tr[ưu][ớo]c\s*khi\s*(?:m[ởo]|kh[ởo]i\s*[đd][ộo]ng)", re.I)

PING = "ping -c1 -W2 8.8.8.8 >/dev/null 2>&1 && echo THONG || echo TAC"
CHO_MANG = 25.0
NHIP = 2.0


def tat_truoc_khi_mo(precondition: str, steps=()) -> bool:
    """Mang phai TAT ngay truoc luc app khoi dong?

    Hai nguon deu tinh:
      - precondition "Tat mang truoc khi mo app"
      - buoc Action "Mo app khong mang" - app phai khoi dong KHI da mat mang,
        tat sau khi no chay roi la do mot thu khac han.

    Doi ca hai ve (tat + truoc khi mo) o precondition: "thiet bi co internet on
    dinh" cung khop TAT_RE neu chi soi mot ve.
    """
    from .act_resolver import LAUNCH_RE  # noi day: act_resolver import nguoc lai

    for dong in (precondition or "").splitlines():
        if TAT_RE.search(dong) and TRUOC_KHI_MO_RE.search(dong) and not BAT_RE.search(dong):
            return True
    return any(LAUNCH_RE.match(b or "") and TAT_RE.search(b or "") and not BAT_RE.search(b or "")
               for b in steps)


async def thong(client, serial: str) -> bool:
    """May co ra duoc internet that khong. `svc` tra ve ngay, ping moi la that."""
    guard(serial)
    out, _, _ = await client.shell(serial, PING)
    return "THONG" in out


async def tat(client, serial: str) -> dict:
    """Ngat wifi + data. Tra trang thai do duoc sau khi ngat."""
    guard(serial)
    for lenh in (("svc", "wifi", "disable"), ("svc", "data", "disable")):
        await client.shell(serial, *lenh)
    con = await thong(client, serial)
    if con:
        # Ngat roi ma van ra duoc mang -> con duong khac (usb tether, ethernet).
        # Noi ra, dung im: ca case dua tren gia dinh may dang mat mang.
        log.warning("da ngat wifi+data nhung may van ra duoc internet")
    return {"mang": "tat", "thong": con}


async def bat(client, serial: str, cho: float = CHO_MANG) -> dict:
    """Bat lai wifi + data roi CHO den khi ping di duoc."""
    guard(serial)
    for lenh in (("svc", "wifi", "enable"), ("svc", "data", "enable")):
        await client.shell(serial, *lenh)
    het = asyncio.get_event_loop().time() + cho
    doi = 0.0
    while asyncio.get_event_loop().time() < het:
        if await thong(client, serial):
            return {"mang": "bat", "thong": True, "cho_s": round(doi, 1)}
        await asyncio.sleep(NHIP)
        doi += NHIP
    return {"mang": "bat", "thong": False, "cho_s": round(doi, 1)}


# DNS chan domain quang cao (doubleclick, googlesyndication... -> 127.0.0.1) ma Firebase
# van chay: tao dieu kien "ad khong ve" khi RC khong khai `id_*` de doi slot (ID nam cung
# trong app). Do tay Sorapix 1.6.0 24/10/2026: OB3A-002/003 ra dung nhanh no-fill.
DNS_CHAN_AD = "dns.adguard-dns.com"


async def _doi_wifi(client, serial: str) -> dict:
    """Bat tat wifi de bo cache DNS cu (doi Private DNS ma khong doi wifi thi domain van phan giai cu)."""
    await client.shell(serial, "svc", "wifi", "disable")
    await asyncio.sleep(2)
    return await bat(client, serial)


async def chan_ad(client, serial: str) -> dict:
    """Bat Private DNS chan quang cao. Tra cai dat cu de `bo_chan_ad` tra ve dung nhu truoc."""
    guard(serial)
    cu = {}
    for k in ("private_dns_mode", "private_dns_specifier"):
        out, _, _ = await client.shell(serial, "settings", "get", "global", k)
        cu[k] = out.strip()
    await client.shell(serial, "settings", "put", "global", "private_dns_mode", "hostname")
    await client.shell(serial, "settings", "put", "global", "private_dns_specifier", DNS_CHAN_AD)
    cu["mang"] = await _doi_wifi(client, serial)
    return cu


async def bo_chan_ad(client, serial: str, cu: dict) -> dict:
    """Tra Private DNS ve cai dat truoc `chan_ad` (gia tri 'null' = chua tung dat -> xoa)."""
    guard(serial)
    for k in ("private_dns_mode", "private_dns_specifier"):
        v = cu.get(k, "null")
        if v in ("", "null"):
            await client.shell(serial, "settings", "delete", "global", k)
        else:
            await client.shell(serial, "settings", "put", "global", k, v)
    return await _doi_wifi(client, serial)
