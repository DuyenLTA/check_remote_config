"""Thao tac CA MAY ma case doi: nhan Home dua app xuong nen, xoay man hinh.

Tach khoi `device_app` (vong doi app) vi day la trang thai cua MAY: xoay man
doi cai dat he thong, quen tra lai la moi lan chay sau deu chup man ngang ma
khong ai biet vi sao. Nen `xoay` LUON tra che do xoay ve nhu cu, ke ca khi
mot lenh giua chung hong.

Dua app len lai sau khi o nen dung `device_app.launch` (am start dung intent
launcher): task da co thi Android chi keo no len truoc, khong mo lai tu dau -
dung nhu user bam icon app. Khong dung `monkey` (ban su kien that vao man).
"""

from __future__ import annotations

import asyncio

from .adb_parsers import AdbError, output_error
from .app_sandbox import guard

# `user_rotation`: 0 = doc, 1 = ngang (xoay 90 do). Chi co nghia khi tat
# tu xoay (`accelerometer_rotation` = 0), nen phai tat truoc roi tra lai sau.
ROTATION = {"doc": "0", "ngang": "1"}
# Cho app ve lai layout sau moi lan xoay truoc khi xoay tiep / chup man.
CHO_SAU_XOAY = 2.5


async def _shell(client, serial: str, *args: str) -> str:
    guard(serial)
    out, err, _ = await client.shell(serial, *args)
    problem = output_error(out, err)
    if problem:
        raise AdbError(f"`{' '.join(args)}` that bai: {problem}")
    return out.strip()


async def home(client, serial: str) -> None:
    """Nhan nut Home: app xuong nen, KHONG bi dong."""
    await _shell(client, serial, "input", "keyevent", "KEYCODE_HOME")


async def xoay(client, serial: str, orientations) -> list[str]:
    """Xoay lan luot theo `orientations`, cho app ve lai sau moi lan.

    Tra danh sach huong da xoay that. Che do xoay cua may tra ve nhu cu trong
    `finally` - may test dung chung cho moi case sau.
    """
    tu_xoay = await _shell(client, serial, "settings", "get", "system", "accelerometer_rotation")
    huong_cu = await _shell(client, serial, "settings", "get", "system", "user_rotation")
    da_xoay: list[str] = []
    try:
        await _shell(client, serial, "settings", "put", "system", "accelerometer_rotation", "0")
        for huong in orientations:
            await _shell(client, serial, "settings", "put", "system", "user_rotation",
                         ROTATION[huong])
            da_xoay.append(huong)
            await asyncio.sleep(CHO_SAU_XOAY)
    finally:
        await _shell(client, serial, "settings", "put", "system", "user_rotation",
                     huong_cu if huong_cu.isdigit() else "0")
        await _shell(client, serial, "settings", "put", "system", "accelerometer_rotation",
                     tu_xoay if tu_xoay.isdigit() else "1")
    return da_xoay
