"""Thao tac tren may that cho check sub: ve Home, mo Paywall, mua goi qua popup Google Play, doc trang thai Premium
tu logcat, bat tat may bay. Play Store (xem / cancel / resubscribe / doi the / cho het ky) o `sub_play_store`.

Chot an toan: popup Google Play khong co dau hieu giao dich test (the "Test card…" / "This is a test subscription")
-> dong popup, nem loi, KHONG bam Subscribe. Moi may QA deu dang nhap tai khoan License Tester (user chot
04/11/2026) nen chot nay chi chan tai khoan la, khong phai buoc hoi user.
"""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path

from . import device_app, fo_flow, screencap, sub_doc_man, sub_log, ui_dump
from .models import RcError

CHO_POPUP = 20          # giay cho popup Google Play hien sau khi bam Continue
CHO_VE_APP = 15         # giay cho app quay lai sau khi Subscribe
CHO_KHOI_DONG = 13      # so lan doc log (2 giay/lan) cho app in ket qua verify sau khi mo lanh
PROFILE_DIR = Path(__file__).resolve().parent / "data" / "sub-profiles"
POPUP_DONG = ("Close", "Đóng", "Not now", "Later", "Maybe later", "No thanks", "Để sau")   # nut dong popup o Home


# --- man hinh ---------------------------------------------------------------------------------
async def man(client, serial: str) -> list[ui_dump.DeviceNode]:
    return ui_dump.parse_dump(await ui_dump.dump(client, serial))


async def chup(client, serial: str, path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(await screencap.raw(client, serial))
    return str(path)


async def bam(client, serial: str, xy: tuple[int, int], cho: float = 1.5) -> None:
    await device_app.tap(client, serial, *xy)
    await asyncio.sleep(cho)


async def bam_chu(client, serial: str, *mau: str, cho: float = 1.5) -> bool:
    """Bam node co text / content-desc bang mot trong `mau`. False khi khong thay."""
    nodes = await man(client, serial)
    n = sub_doc_man._tim(nodes, *mau)
    if n is None:
        return False
    await bam(client, serial, sub_doc_man.toa_do(nodes, n), cho)
    return True


# --- profile app ------------------------------------------------------------------------------
def doc_profile(package: str) -> dict | None:
    f = PROFILE_DIR / f"{package}.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else None


def ghi_profile(package: str, profile: dict) -> Path:
    """Profile app (Claude do lan dau): duong_vao_paywall, dau_hieu_premium, quan_ly_sub, quyen_loi, man_co_ad,
    chua_xac_nhan, ghi_chu. Moi buoc duong vao la {"text": ...} hoac {"desc": ...} - bam node co chu do.
    GOP vao profile da co (chi thay cac khoa co trong `profile`): ghi thu tung phan khong lam mat phan con lai."""
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    f = PROFILE_DIR / f"{package}.json"
    f.write_text(json.dumps({**(doc_profile(package) or {}), **profile, "package": package}, ensure_ascii=False,
                            indent=1), encoding="utf-8")
    return f


async def di_theo(client, serial: str, buoc: list[dict]) -> list[str]:
    """Bam lan luot cac buoc {text|desc}. Tra danh sach buoc khong tim thay (rong = di het)."""
    thieu = []
    for b in buoc:
        if not await bam_chu(client, serial, b.get("text") or b.get("desc") or "", cho=b.get("cho", 2.5)):
            thieu.append(b.get("text") or b.get("desc") or "")
    return thieu


async def ve_home(client, serial: str, package: str) -> dict:
    """Dua app ve Home: chua o foreground thi mo bang icon, roi lai qua FO (splash / ad / language / onboarding /
    Billing) bang walker chung. Walker gap man Billing chi dong / "Continue with ads", KHONG bam mua.
    App AIP936 mo lanh la di lai Onboarding Question (do 04/11/2026) -> moi buoc can Home deu phai qua day."""
    prof = doc_profile(package) or {}
    if await device_app.foreground(client, serial) != package:
        await device_app.launch(client, serial, package)
        await asyncio.sleep(3)
    walk = await fo_flow.walk_to(client, serial, package, prof.get("home_activity") or "MainActivity")
    # Home hay bat popup (Add Widget, Rate us - do 04/11/2026) che nut vao Paywall -> dong het truoc.
    da_dong = []
    for _ in range(4):
        if not await bam_chu(client, serial, *POPUP_DONG, cho=2):
            break
        da_dong.append("popup")
    return {"reached": walk.get("reached"), "activity": walk.get("activity", ""), "dong_popup": len(da_dong)}


async def mo_paywall(client, serial: str, package: str) -> dict:
    """Dang o Paywall thi doc luon; khong thi ve Home roi di theo profile. Khong co profile / di khong toi -> RcError."""
    pw = sub_doc_man.doc_paywall(await man(client, serial))
    if pw:
        return pw
    prof = doc_profile(package)
    if not prof or not prof.get("duong_vao_paywall"):
        raise RcError(f"chưa có profile đường vào Paywall cho {package} — dò tay rồi ghi bằng `rcr-sub profile`")
    home = await ve_home(client, serial, package)
    if not home["reached"]:
        raise RcError(f"không về được Home (đang ở {home['activity']})")
    thieu = await di_theo(client, serial, prof["duong_vao_paywall"])
    pw = sub_doc_man.doc_paywall(await man(client, serial))
    if pw and pw["dong"] is None:          # nut X cua Paywall VisionLab hien tre vai giay -> doc lai
        await asyncio.sleep(3)
        pw = sub_doc_man.doc_paywall(await man(client, serial)) or pw
    if not pw:
        raise RcError(f"đi theo profile không tới Paywall (không thấy: {thieu or 'màn Paywall'})")
    return pw


# --- logcat billing ---------------------------------------------------------------------------
async def xoa_log(client, serial: str) -> None:
    await client.shell(serial, "logcat", "-c")


async def log_billing(client, serial: str) -> list[str]:
    out, _, _ = await client.shell(serial, "logcat", "-d", "-v", "time", timeout=60)
    return [d for d in out.splitlines() if any(t in d for t in sub_log.TAG)]


# --- mua ------------------------------------------------------------------------------------
async def mua(client, serial: str, package: str, goi: str, the: str = "approves", xac_nhan: bool = True,
              anh_dir: Path | None = None) -> dict:
    """Tu Paywall: chon goi -> Continue -> doc popup -> (doi the test) -> Subscribe (hoac dong popup khi
    `xac_nhan` False). Tra {paywall, popup, ve_app, log} - Claude cham Expected tu day."""
    anh = {}
    pw = await mo_paywall(client, serial, package)
    chon = next((g for g in pw["goi"] if g["ten"] == goi.lower()), None)
    if chon is None:
        raise RcError(f"Paywall không có gói {goi} (có: {[g['ten'] for g in pw['goi']]})")
    if not chon["chon"]:
        await bam(client, serial, chon["xy"])
    await xoa_log(client, serial)
    await bam(client, serial, pw["continue"], cho=1)
    popup = None
    for _ in range(CHO_POPUP):
        popup = sub_doc_man.doc_popup(await man(client, serial))
        if popup:
            break
        await asyncio.sleep(1)
    if anh_dir:
        anh["popup"] = await chup(client, serial, anh_dir / f"popup-{goi}-{int(time.time())}.png")
    if popup is None:
        return {"paywall": pw, "popup": None, "ve_app": await device_app.foreground(client, serial),
                "log": sub_log.doc(await log_billing(client, serial)), "anh": anh}
    if not popup["la_test"]:
        if popup["dong"]:
            await bam(client, serial, popup["dong"])
        raise RcError("popup Google Play không phải giao dịch test (không có Test card) — KHÔNG mua")
    if the != "approves" and popup["doi_the"]:
        await bam(client, serial, popup["doi_the"], cho=2.5)
        xy = sub_doc_man.the_test(await man(client, serial), the)
        if xy is None:
            raise RcError(f"không thấy thẻ test '{the}' trong danh sách phương thức thanh toán")
        await bam(client, serial, xy, cho=2.5)
        popup = sub_doc_man.doc_popup(await man(client, serial)) or popup
    if xac_nhan:
        await bam(client, serial, popup["subscribe"], cho=2)
    elif popup["dong"]:
        await bam(client, serial, popup["dong"], cho=2)
    else:
        await client.shell(serial, "input", "keyevent", "KEYCODE_BACK")
    for _ in range(CHO_VE_APP):
        if await device_app.foreground(client, serial) == package:
            break
        await asyncio.sleep(1)
    await asyncio.sleep(3)                                   # app xu ly ket qua, acknowledge
    if anh_dir:
        anh["sau"] = await chup(client, serial, anh_dir / f"sau-mua-{goi}-{int(time.time())}.png")
    return {"paywall": pw, "popup": popup, "ve_app": (await device_app.focus(client, serial)),
            "log": sub_log.doc(await log_billing(client, serial)), "anh": anh}


# --- trang thai app ---------------------------------------------------------------------------
async def mo_lanh(client, serial: str, package: str) -> dict:
    """Kill roi mo app, doc log billing luc khoi dong -> {premium, ...} (sub_log.doc)."""
    await device_app.force_stop(client, serial, package)
    await xoa_log(client, serial)
    await device_app.launch(client, serial, package)
    kq = {}
    for _ in range(CHO_KHOI_DONG):      # cho toi khi co ket qua verify thanh cong (query dau co the hong: code -1)
        await asyncio.sleep(2)
        kq = sub_log.doc(await log_billing(client, serial))
        if kq["premium"] is not None:
            break
    return kq


async def may_bay(client, serial: str, bat: bool) -> None:
    out, err, code = await client.shell(serial, "cmd", "connectivity", "airplane-mode", "enable" if bat else "disable")
    if code:
        raise RcError(f"không đổi được chế độ máy bay: {(err or out).strip()}")
