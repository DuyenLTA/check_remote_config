"""Lam mot thao tac da dich tren may that. Tach khoi `case_drive` de file duoi
200 dong: `case_drive` lo trinh tu buoc va cac cho dung, file nay lo LAM.

`ctx` la trang thai mang qua cac buoc cua mot case:
    vuot_sau   so trang da vuot sang ke tu lan doc cham chi trang gan nhat
    trang_cu   trang doc duoc gan nhat (0 = khong biet)
    o_nen      app dang nam nen sau buoc nhan Home -> buoc "Mo lai app" phai
               dua no len that, khong duoc coi la "app da mo san"
    cua_so     so giay theo doi cho buoc "bam gio" / cho nut X hien
    ghi_khung  case co dong Expected ve nut X / so dem -> buoc CHO cung nhin
               lien tuc thay vi ngu (quan_sat)
    khung      cac khung da nhin, kem moc gio cua may
"""

from __future__ import annotations

import asyncio
import time

from . import act_resolver, device_app, device_motion, net_ctl, quan_sat

# Cho SDK co co hoi retry sau khi mang len lai, truoc khi doc log.
CHO_SAU_KHI_CO_MANG = 6.0
# Cu vuot / tap lien tuc: ngan de du nhieu cu trong ~1s nhu TC doi.
VUOT_NHANH_MS = 120
GIUA_HAI_CU = 0.05
CHO_SAU_THAO_TAC = 1.0


def _noop(_msg: str) -> None:
    pass


CUA_SO_MAC_DINH = 12.0


def ctx_moi(package: str = "", cua_so: float = CUA_SO_MAC_DINH, ghi_khung: bool = False) -> dict:
    return {"vuot_sau": 0, "trang_cu": 0, "o_nen": False, "package": package,
            "cua_so": cua_so, "ghi_khung": ghi_khung, "khung": [], "thao_tac": []}


async def resume_neu_o_nen(client, serial: str, package: str, step: str, record: dict,
                           ctx: dict) -> bool:
    """Buoc "Mo lai app" sau khi app xuong nen -> dua app len that. Tra True neu da lam.

    Luat co ban dich "Mo lai app" thanh "app da mo san" - dung voi luc vua
    patch config, SAI khi app dang nam nen: bo qua thi case cham man launcher.
    """
    if not ctx["o_nen"] or not act_resolver.LAUNCH_RE.match(step):
        return False
    await device_app.launch(client, serial, package)
    await device_app.wait_foreground(client, serial, package)
    ctx["o_nen"] = False
    record["action"] = {"kind": "resume", "reason": "đưa app từ nền lên lại (như bấm icon app)"}
    await asyncio.sleep(CHO_SAU_THAO_TAC)
    return True


async def lam(client, serial: str, action, record: dict, ctx: dict, log_fn=_noop) -> None:
    """Lam `action`. GoTo va NeedsHuman do `case_drive` lo, khong toi day."""
    if isinstance(action, (act_resolver.Tap, act_resolver.Swipe)):
        # Moc tool tu vuot/bam: man doi ngay sau do la do TOOL, khong phai app tu
        # chuyen - assert_timing can phan biet hai thu nay.
        ctx["thao_tac"].append(await quan_sat.gio_may(client, serial))
    if isinstance(action, act_resolver.Seq):
        for con in action.actions:
            await lam(client, serial, con, record, ctx, log_fn)
        return
    if isinstance(action, act_resolver.Tap):
        bat_dau = time.monotonic()
        for i in range(action.lan):
            await device_app.tap(client, serial, action.x, action.y)
            if i + 1 < action.lan:
                await asyncio.sleep(GIUA_HAI_CU)
        if action.lan > 1:
            record["lien_tuc"] = {"lan": action.lan, "giay": round(time.monotonic() - bat_dau, 2)}
        await asyncio.sleep(CHO_SAU_THAO_TAC)
    elif isinstance(action, act_resolver.Swipe):
        await _vuot(client, serial, action, record, ctx)
    elif isinstance(action, act_resolver.Net):
        ket = await (net_ctl.bat(client, serial) if action.on else net_ctl.tat(client, serial))
        record["net"] = ket
        log_fn(f"    mang -> {ket['mang']}" + (" (ping thong)" if ket["thong"] else " (ping khong di)"))
        if action.on:
            # Ca cau hoi cua case la "mang len lai thi SDK co request len unit
            # da tat khong". Doc log ngay luc vua co mang la doc truoc khi SDK
            # kip retry - khong thay gi roi bao PASS.
            await asyncio.sleep(CHO_SAU_KHI_CO_MANG)
    elif isinstance(action, act_resolver.Wait):
        if ctx["ghi_khung"]:
            await quan_sat.theo_doi(client, serial, ctx["package"], action.seconds, ctx["khung"])
        else:
            await asyncio.sleep(action.seconds)
    elif isinstance(action, act_resolver.Watch):
        await quan_sat.theo_doi(client, serial, ctx["package"], ctx["cua_so"], ctx["khung"])
        record["theo_doi_giay"] = ctx["cua_so"]
    elif isinstance(action, act_resolver.TapId):
        await _bam_khi_hien(client, serial, action, record, ctx)
    elif isinstance(action, act_resolver.Background):
        await device_motion.home(client, serial)
        ctx["o_nen"] = True
        await asyncio.sleep(action.seconds)
    elif isinstance(action, act_resolver.Rotate):
        record["xoay"] = await device_motion.xoay(client, serial, action.orientations)


async def _vuot(client, serial: str, action, record: dict, ctx: dict) -> None:
    if action.lan == 1:
        await device_app.swipe(client, serial, action.direction)
        # Trai = sang trang ke, phai = lui mot trang: de suy trang OB3 (khong
        # co cham chi trang) cho dung ca khi case vuot qua lai.
        ctx["vuot_sau"] += {"left": 1, "right": -1}.get(action.direction, 0)
        await asyncio.sleep(CHO_SAU_THAO_TAC)
        return
    man = await device_app.screen_size(client, serial)
    bat_dau = time.monotonic()
    for i in range(action.lan):
        await device_app.swipe(client, serial, action.direction, man, VUOT_NHANH_MS)
        if i + 1 < action.lan:
            await asyncio.sleep(GIUA_HAI_CU)
    record["lien_tuc"] = {"lan": action.lan, "giay": round(time.monotonic() - bat_dau, 2)}
    # Vuot lien tuc la de xem app co nhay NHIEU trang khong - khong duoc suy
    # trang bang so lan vuot (ra dung cai bug dang tim). Chi tin cham chi trang.
    ctx["vuot_sau"], ctx["trang_cu"] = 0, 0
    await asyncio.sleep(CHO_SAU_THAO_TAC)


async def _bam_khi_hien(client, serial: str, action, record: dict, ctx: dict) -> None:
    """Cho node hien (nhin lien tuc, toi da `cua_so` giay) roi tap. Ghi luc bam."""
    if tuple(action.ids) == quan_sat.VAI_NUT_X:
        # Nut X: nhin bang khung nhanh va tap NGAY khi hien - cho uiautomator
        # (~2,5s) thi "X hien 2s, bam luc 3s" da tre, timer auto chuyen trang truoc.
        tam = await quan_sat.cho_nut_x(client, serial, ctx["package"], ctx["cua_so"], ctx["khung"])
        if not tam:
            record["action"] = {"kind": "needs_human", "reason":
                                f"nút X không hiện trong {ctx['cua_so']:g}s theo dõi"}
            return
        await _tap_ghi_luc(client, serial, tam, action, record, ctx)
        return
    nodes = await quan_sat.theo_doi(
        client, serial, ctx["package"], ctx["cua_so"], ctx["khung"],
        dung_khi=lambda ns: len(quan_sat.tim(ns, action.ids)) == 1)
    if not nodes:
        record["action"] = {"kind": "needs_human", "reason":
                            f"{'/'.join(action.ids)} không hiện trong {ctx['cua_so']:g}s theo dõi"}
        return
    await _tap_ghi_luc(client, serial, quan_sat.tim(nodes, action.ids)[0].bounds.center,
                       action, record, ctx)


async def _tap_ghi_luc(client, serial: str, tam, action, record: dict, ctx: dict) -> None:
    x, y = tam
    record["bam_luc"] = await quan_sat.gio_may(client, serial)
    ctx["thao_tac"].append(record["bam_luc"])
    for i in range(action.lan):
        await device_app.tap(client, serial, x, y)
        if i + 1 < action.lan:
            await asyncio.sleep(GIUA_HAI_CU)
    await asyncio.sleep(CHO_SAU_THAO_TAC)
