"""Cac phep DO them trong luc lai may: chup man ket, do animation, thu vuot.

Tach khoi `case_drive` de moi file duoi 200 dong: `case_drive` lo trinh tu cac
buoc, file nay lo tung phep do lay bang chung cho khau cham.
"""

from __future__ import annotations

import asyncio

from . import anim_check, device_app, fo_steps, screencap, ui_dump

# Node co ten nhu mot animation. Chi nhung man CO node nay moi chup them khung
# de do - man khong co thi khong ton them giay nao.
ANIM_HINTS = ("lottie", "anim")


async def _chup_ket(client, serial: str, package: str, index: int,
                    trang_cu: int = 0, vuot: int = 0, dump_cu: str = "") -> dict:
    """Chup man hinh SAU khi lam xong buoc cuoi.

    Moi buoc chup TRUOC khi thao tac, nen khong co anh nao cho trang thai sau
    cung - ma nhieu dong Expected noi dung ve no ("Chuyen sang man Onboarding
    3" sau buoc vuot). Thieu anh nay thi dong do phai bo cho nguoi.

    Trang OB doc theo cham chi trang, nhung OB3 la trang quang cao native toan
    man va KHONG co cham nao (do tren may 2026-09-28). Luc do suy tu trang da
    DO duoc cong so lan tool tu vuot - va chi suy khi man that su da doi, de
    mot cu vuot khong an khong bi tinh thanh da sang trang.
    """
    _, activity = await device_app.focus(client, serial)
    xml = await ui_dump.dump(client, serial)
    shot = await screencap.capture(client, serial)
    nodes = ui_dump.app_nodes(ui_dump.parse_dump(xml), package)
    trang, nguon = fo_steps.onboarding_page(nodes), "cham"
    if not trang and trang_cu and vuot and dump_cu and xml != dump_cu:
        trang, nguon = trang_cu + vuot, "suy_ra"
    return {"n": index, "step": "(sau bước cuối)", "activity": activity, "dump": xml,
            "shot": shot["thumb"], "shot_warning": shot["warning"],
            "page": trang, "page_nguon": nguon if trang else "",
            "action": {"kind": "noop", "reason": "chụp lại màn sau khi làm xong các bước"}}


async def _thu_vuot(client, serial: str, package: str, truoc: dict, index: int) -> dict:
    """Vuot mot cai roi xem man co doi khong: "user co the vuot sang man ke".

    Lam SAU cung, khi moi dong khac da cham xong - cu vuot nay doi man nen lam
    som la hong bang chung cua cac dong con lai.
    """
    await device_app.swipe(client, serial, "left")
    await asyncio.sleep(1.2)
    sau = await _chup_ket(client, serial, package, index,
                          truoc.get("page") or 0, 1, truoc.get("dump") or "")
    sau["step"] = "(thử vuốt sang màn kế)"
    doi = bool(truoc.get("dump")) and sau.get("dump") != truoc.get("dump")
    return {"doi": doi, "trang_truoc": truoc.get("page") or 0,
            "trang_sau": sau.get("page") or 0, "anh": sau}


async def _do_animation(client, serial: str, nodes: list) -> dict:
    """{id node: ket qua do} cho cac node trong ten la animation.

    Dong Expected "icon la animation lap" truoc day phai bo cho nguoi, trong
    khi chup vai khung roi so vung cua node la tra loi duoc (do 2026-09-28).
    """
    canh = [n for n in nodes
            if n.visible and not n.bounds.empty
            and any(h in n.resource_id.lower() for h in ANIM_HINTS)]
    if not canh:
        return {}
    khung = await screencap.frames(client, serial)
    return {n.resource_id: anim_check.do(khung, n.bounds) for n in canh}
