"""Play Store cho check sub: trang Subscriptions / Manage subscription - xem trang thai, cancel, resubscribe, doi the
test, cho goi het han. Doc man o `sub_doc_man`; bam / dump dung chung `sub_thao_tac`.

Do tren may that 04/11/2026: cancel = "Cancel subscription" -> man khao sat -> bam thang nut "Cancel subscription" o
duoi (khong chon ly do, user chot); resubscribe = "Resubscribe" -> sheet "Resubscribe to <app>?" -> nut "Resubscribe".
"""

from __future__ import annotations

import asyncio
import time

from . import sub_doc_man
from .models import RcError
from .sub_thao_tac import bam, bam_chu, man

PLAY_SUBS = "https://play.google.com/store/account/subscriptions"


async def mo_play(client, serial: str, package: str = "", sku: str = "") -> dict:
    link = f"{PLAY_SUBS}?sku={sku}&package={package}" if sku and package else PLAY_SUBS
    # Mot chuoi shell: dau & trong link phai nam trong nhay, khong thi shell may cat lenh.
    await client.shell_line(serial, f"am start -a android.intent.action.VIEW -d '{link}'")
    await asyncio.sleep(6)
    return sub_doc_man.doc_play(await man(client, serial))


async def cancel_play(client, serial: str, package: str, sku: str) -> dict:
    """Cancel goi tren Play Store: Cancel subscription -> man khao sat -> bam thang nut Cancel subscription o duoi
    (khong chon ly do). Tra trang Manage doc lai sau khi cancel."""
    trang = await mo_play(client, serial, package, sku)
    if "cancel" not in trang["nut"]:
        raise RcError(f"trang Play Store không có nút Cancel subscription (trạng thái {trang['trang_thai']})")
    await bam(client, serial, trang["nut"]["cancel"], cho=3)
    xy = sub_doc_man.nut_xac_nhan_cancel(await man(client, serial))
    if xy is None:
        raise RcError("màn khảo sát cancel không có nút Cancel subscription")
    await bam(client, serial, xy, cho=4)
    # Man ngay sau khi bam xac nhan con dang chuyen (doc ra thieu gio het han) -> mo lai trang roi moi doc.
    return await mo_play(client, serial, package, sku)


async def resubscribe(client, serial: str, package: str, sku: str) -> dict:
    trang = await mo_play(client, serial, package, sku)
    if "resubscribe" not in trang["nut"]:
        raise RcError(f"không có nút Resubscribe (trạng thái {trang['trang_thai']})")
    await bam(client, serial, trang["nut"]["resubscribe"], cho=4)
    nodes = await man(client, serial)
    xy = sub_doc_man.nut_xac_nhan_resubscribe(nodes)
    if xy and xy != tuple(trang["nut"]["resubscribe"]):     # sheet xac nhan "Resubscribe to <app>?"
        await bam(client, serial, xy, cho=4)
    popup = sub_doc_man.doc_popup(await man(client, serial))
    if popup:                                               # Play hoi xac nhan lai bang popup mua
        if not popup["la_test"]:
            raise RcError("popup Resubscribe không phải giao dịch test — KHÔNG xác nhận")
        await bam(client, serial, popup["subscribe"], cho=4)
    return await mo_play(client, serial, package, sku)


async def doi_the_play(client, serial: str, package: str, sku: str, the: str) -> dict:
    """Doi phuong thuc thanh toan chinh cua goi sang the test `the` (approves | declines | slow)."""
    trang = await mo_play(client, serial, package, sku)
    if "update" not in trang["nut"]:
        raise RcError("trang Play Store không có nút Update phương thức thanh toán")
    await bam(client, serial, trang["nut"]["update"], cho=3)
    xy = sub_doc_man.the_test(await man(client, serial), the)
    if xy is None:
        raise RcError(f"không thấy thẻ test '{the}'")
    await bam(client, serial, xy, cho=3)
    await bam_chu(client, serial, "Save", "Update", "Done", "Lưu", "Cập nhật", cho=3)
    return sub_doc_man.doc_play(await man(client, serial))


async def cho_het_ky(client, serial: str, package: str, sku: str, toi_da: int = 40 * 60) -> dict:
    """Cho toi khi Play Store bao goi Expired (hoac het `toi_da` giay). Tra trang cuoi."""
    bat_dau = time.time()
    trang = await mo_play(client, serial, package, sku)
    while trang["trang_thai"] not in ("expired", "none") and time.time() - bat_dau < toi_da:
        await asyncio.sleep(45)
        trang = await mo_play(client, serial, package, sku)
    trang["cho_giay"] = int(time.time() - bat_dau)
    return trang
