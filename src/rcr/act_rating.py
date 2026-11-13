"""Buoc Action cua tab TC "rating" (SDK Rating com.apero.rating): gen anh toi result, chon sao, bam Rate / X,
thoat app, back tu Feedback / Google Play, shortcut.

AIP892 rating 12/11/2026: moi buoc nay tool tra NEEDS_HUMAN, Claude do tay ca lượt ~2,5 tieng. Cach do tay da duoc
user chap nhan nen dong goi lai o day; bang chung ghi vao `record["rating"]` cho `assert_rating` cham:
  "Gen anh[, cho popup]" / "Gen anh vao result[, bam X dong popup]" -> cong thuc `data/rating_gen.yaml` cua app (app
      chua co cong thuc -> dung NEEDS_HUMAN), toi result thi chup lien tuc de do luc nut X hien.
  "Chon N sao[, bam button / bam "..."]" / "Doi sang N sao" -> tap node "Star N", doc nhan nut, bam nut neu cau bao.
  "Bam X"                         -> bam nut Close cua popup (chi khi popup rating dang hien).
  "Thuc hien thao tac thoat app"  -> BACK (dang o Home), doc popup exit_click / app con foreground khong.
  "Bam <- tren man Feedback" / "Bam back tu Google Play" -> BACK, doc man quay ve.
  "Nhan giu icon app[, chon option Rating]" -> doc `dumpsys shortcut`; chon Rating = mo dung intent cua shortcut
      (launcher cung chi startActivity intent do).
"""

from __future__ import annotations

import asyncio
import re
import time
from dataclasses import dataclass

from . import device_app, log_moc, rating_cong_thuc, rating_may, ui_dump
from .adb_parsers import AdbError

GEN_RE = re.compile(r"^\s*gen\s+(ảnh|anh|video)\b", re.I)
BAM_X_SAU_RE = re.compile(r"b[ấa]m\s+x\b", re.I)
SAO_RE = re.compile(r"^\s*(?:ch[ọo]n|đ[ổo]i\s+sang|doi\s+sang)\s+([1-5])\s*sao\b(?P<rest>.*)$", re.I)
BAM_NUT_RE = re.compile(r"b[ấa]m\s+(?:button|n[úu]t|[\"“])", re.I)
X_RE = re.compile(r"^\s*b[ấa]m\s+(?:n[úu]t\s+|button\s+)?x\b", re.I)
THOAT_RE = re.compile(r"^\s*(?:th[ựu]c\s+hi[ệe]n\s+(?:thao\s+t[áa]c\s+)?)?tho[áa]t\s+app\b", re.I)
BACK_RE = re.compile(r"^\s*b[ấa]m\s+(?:←|back|n[úu]t\s+back)\s+(?:tr[êe]n|t[ừu])\b", re.I)
SHORTCUT_RE = re.compile(r"^\s*nh[ấa]n\s+gi[ữu]\s+icon\s+app\b(?P<rest>.*)$", re.I)
CHON_RATING_RE = re.compile(r"ch[ọo]n\s+(?:option\s+)?rat", re.I)
BAM_GIO_POPUP_RE = re.compile(r"b[ấa]m\s+gi[ờo].*popup", re.I)

HOME_RE = re.compile(r"Main|Home", re.I)     # activity Home cua app (AIP892: MainActivity)
CHUP_GIAY = 6.0         # cua so chup lien tuc tu luc toi result / bam BACK: du cho show_rating_button_x toi 4-5s
CHO_POPUP = 8.0
KHOI_DONG_CHUP = 0.8
SAU_THAO_TAC = 1.5


@dataclass(frozen=True, slots=True)
class Rating:
    viec: str            # gen | sao | x | thoat | back | shortcut | da_do
    reason: str
    loai: str = ""
    sao: int = 0
    bam: bool = False

    @property
    def summary(self) -> dict:
        return {"kind": f"rating_{self.viec}", "reason": self.reason}


def _co_popup(nodes) -> bool:
    return rating_may.doc_popup(nodes)["hien"]


def resolve(text: str, nodes):
    """Cau buoc cua tab rating -> thao tac; cau khac -> None."""
    m = GEN_RE.match(text)
    if m:
        loai = "video" if m.group(1).lower() == "video" else "anh"
        return Rating("gen", f"gen {'ảnh' if loai == 'anh' else loai} theo công thức của app tới màn result, "
                             "đo popup + nút X",
                      loai=loai, bam=bool(BAM_X_SAU_RE.search(text)))
    m = SAO_RE.match(text)
    if m:
        bam = bool(BAM_NUT_RE.search(m.group("rest")))
        return Rating("sao", f"chọn {m.group(1)} sao" + (", bấm nút Rate" if bam else ""), sao=int(m.group(1)),
                      bam=bam)
    if X_RE.match(text) and _co_popup(nodes):
        return Rating("x", "bấm nút X của popup Rating")
    if THOAT_RE.match(text):
        return Rating("thoat", "BACK để thoát app, đọc popup exit_click")
    if BACK_RE.match(text):
        return Rating("back", "BACK, đọc màn quay về")
    m = SHORTCUT_RE.match(text)
    if m:
        mo = bool(CHON_RATING_RE.search(m.group("rest")))
        return Rating("shortcut", "đọc shortcut của app" + (", mở option Rating" if mo else ""), bam=mo)
    if BAM_GIO_POPUP_RE.search(text):
        return Rating("da_do", "đo nút X ngay lúc popup hiện (khung chụp liên tục ở bước trước)")
    return None


async def lam(client, serial: str, action: Rating, record: dict, ctx: dict) -> None:
    package = ctx["package"]
    moc = await log_moc.bay_gio(client, serial)
    try:
        ket = await _lam(client, serial, package, action, moc)
    except (AdbError, OSError, ValueError, TypeError, KeyError) as exc:
        # Loi bat ngo trong mot buoc khong duoc lam sap ca luot (cac case sau van phai chay): dung case nay.
        ket = {"dung": f"lỗi khi làm bước rating {action.viec}: {type(exc).__name__}: {exc}"}
    record["rating"] = {"viec": action.viec, **ket, "su_kien": await rating_may.su_kien(client, serial, moc)}
    if ket.get("dung"):
        record["dung_lai"] = ket["dung"]


async def _lam(client, serial: str, package: str, action: Rating, moc: str) -> dict:
    if action.viec == "gen":
        ket = await _gen(client, serial, package, action, moc)
    elif action.viec == "sao":
        ket = await _sao(client, serial, package, action)
    elif action.viec == "x":
        ket = await _x(client, serial, package)
    elif action.viec == "thoat":
        ket = await _thoat(client, serial, package, moc)
    elif action.viec == "back":
        ket = await _back(client, serial, package)
    elif action.viec == "shortcut":
        ket = await _shortcut(client, serial, package, action.bam)
    else:
        ket = {}
    return ket


async def _act(client, serial: str) -> tuple[str, str]:
    pkg, act = await device_app.focus(client, serial)
    return pkg, act.rsplit(".", 1)[-1] if act else ""


async def _cho_popup_do_x(client, serial: str, package: str, moc: str) -> dict:
    """Vua toi man co the hien popup: chup lien tuc, cho popup + nut X, do moc X hien (giay tu popup hien)."""
    await rating_may.bat_dau_chup(client, serial, CHUP_GIAY)
    bat_dau = time.monotonic()
    pop = {}
    while time.monotonic() < bat_dau + CHO_POPUP:
        pop = await rating_may.nhin(client, serial, package)
        if pop["hien"]:
            break
        await asyncio.sleep(0.3)
    await asyncio.sleep(max(0.0, bat_dau + CHUP_GIAY + 1.5 - time.monotonic()))     # cho vong chup tren may xong
    if pop.get("hien") and not pop.get("x"):
        pop = await rating_may.nhin(client, serial, package)
    vw = await rating_may.viewed(client, serial, moc)
    if pop.get("hien"):
        do_x = await rating_may.ket_thuc_chup(client, serial, pop.get("x_khung"), vw[-1][0] if vw else None)
    else:
        do_x = {}
        await client.shell(serial, "rm", "-rf", rating_may.THU_MUC)
    _, act = await _act(client, serial)
    return {"popup": pop.get("hien", False), "nut": pop.get("nut", ""), "x_luc_xem": bool(pop.get("x")),
            "viewed": vw, "do_x": do_x, "man": act}


async def _gen(client, serial: str, package: str, action: Rating, moc: str) -> dict:
    ct = await rating_cong_thuc.chay(client, serial, package, action.loai)
    if not ct["co_cong_thuc"]:
        return {"dung": f"app chưa có công thức gen {action.loai} trong data/rating_gen.yaml"}
    if not ct["xong"]:
        return {"dung": f"gen {action.loai} không tới được result: {'; '.join(ct['log'][-3:])}", "log": ct["log"]}
    ket = {"log": ct["log"], **await _cho_popup_do_x(client, serial, package, moc)}
    if action.bam and ket["popup"]:
        ket["sau_x"] = await _x(client, serial, package)
    return ket


async def _sao(client, serial: str, package: str, action: Rating) -> dict:
    nodes = ui_dump.app_nodes(ui_dump.parse_dump(await ui_dump.dump(client, serial)), package)
    pop = rating_may.doc_popup(nodes)
    if not pop["hien"]:
        return {"sao": action.sao, "popup": False, "dung": "không thấy popup/màn Rating để chọn sao"}
    await device_app.tap(client, serial, *pop["sao"][action.sao])
    await asyncio.sleep(0.8)
    nodes = ui_dump.app_nodes(ui_dump.parse_dump(await ui_dump.dump(client, serial)), package)
    nut = rating_may.nut_rate(nodes)
    ket = {"sao": action.sao, "popup": True, "nut": nut.text if nut else "", "nut_enabled": bool(nut and nut.enabled)}
    if action.bam and nut:
        _, truoc = await _act(client, serial)
        await device_app.tap(client, serial, *nut.bounds.center)
        await asyncio.sleep(3.0)
        pkg, act = await _act(client, serial)
        ket.update({"da_bam": True, "truoc": truoc, "pkg_sau": pkg, "man_sau": act,
                    "google_play": pkg == rating_may.GOOGLE_PLAY})
    return ket


async def _x(client, serial: str, package: str) -> dict:
    pop = await rating_may.nhin(client, serial, package)
    if not pop.get("x"):
        return {"bam": False, "loi": "popup không có nút X"}
    _, truoc = await _act(client, serial)
    await device_app.tap(client, serial, *pop["x"])
    await asyncio.sleep(SAU_THAO_TAC)
    sau = await rating_may.nhin(client, serial, package)
    pkg, act = await _act(client, serial)
    return {"bam": True, "truoc": truoc, "man": act, "pkg": pkg, "popup_con": sau["hien"]}


async def _dong_popup_de(client, serial: str, package: str) -> list[str]:
    """Popup khac de len man (Add Widget, Check-in o Home session 1): BACK luc nay chi dong popup do chu khong
    phai thao tac thoat app -> bam Close cua chung truoc (khong dong popup Rating)."""
    da = []
    for _ in range(4):
        nodes = ui_dump.app_nodes(ui_dump.parse_dump(await ui_dump.dump(client, serial)), package)
        if rating_may.doc_popup(nodes)["hien"]:
            break
        node = rating_cong_thuc.tim(nodes, "^Close$")
        if not node:
            break
        await device_app.tap(client, serial, *node.bounds.center)
        da.append(node.content_desc or node.text)
        await asyncio.sleep(SAU_THAO_TAC)
    return da


async def _ve_home(client, serial: str, package: str) -> list[str]:
    """Thao tac thoat app = BACK o Home. Buoc truoc co the de app o result / Feedback: BACK ve Home truoc (BACK tu
    result chi ve Home, chua phai thoat - R07-01 19:27 FAIL gia)."""
    da = []
    for _ in range(3):
        pkg, act = await _act(client, serial)
        if pkg != package or HOME_RE.search(act):
            break
        await client.shell(serial, "input", "keyevent", "KEYCODE_BACK")
        da.append(f"BACK từ {act}")
        await asyncio.sleep(SAU_THAO_TAC)
    return da


async def _thoat(client, serial: str, package: str, moc: str) -> dict:
    ve = await _ve_home(client, serial, package)
    dong = ve + await _dong_popup_de(client, serial, package)
    _, truoc = await _act(client, serial)
    await rating_may.bat_dau_chup(client, serial, CHUP_GIAY)
    await asyncio.sleep(KHOI_DONG_CHUP)          # co khung "chua co popup" truoc khi BACK
    await client.shell(serial, "input", "keyevent", "KEYCODE_BACK")
    await asyncio.sleep(2.5)
    pop = await rating_may.nhin(client, serial, package)
    pkg, act = await _act(client, serial)
    vw = await rating_may.viewed(client, serial, moc)
    await asyncio.sleep(CHUP_GIAY - 2.0)
    if pop["hien"] and not pop["x"]:
        pop = await rating_may.nhin(client, serial, package)
    do_x = await rating_may.ket_thuc_chup(client, serial, pop.get("x_khung"), vw[-1][0] if vw else None) \
        if pop["hien"] else {}
    if not pop["hien"]:
        await client.shell(serial, "rm", "-rf", rating_may.THU_MUC)
    return {"dong_truoc": dong, "truoc": truoc, "popup": pop["hien"], "nut": pop["nut"], "pkg": pkg, "man": act,
            "con_trong_app": pkg == package, "viewed": vw, "do_x": do_x}


async def _back(client, serial: str, package: str) -> dict:
    _, truoc = await _act(client, serial)
    await client.shell(serial, "input", "keyevent", "KEYCODE_BACK")
    het = time.monotonic() + 8.0
    pkg, act = await _act(client, serial)
    while pkg != package and time.monotonic() < het:      # Google Play dong cham
        await asyncio.sleep(1.0)
        pkg, act = await _act(client, serial)
    await asyncio.sleep(SAU_THAO_TAC)
    pkg, act = await _act(client, serial)
    return {"truoc": truoc, "pkg": pkg, "man": act}


async def _shortcut(client, serial: str, package: str, mo: bool) -> dict:
    ds = await rating_may.shortcuts(client, serial, package)
    rating = [s for s in ds if rating_may.la_shortcut_rating(s)]
    ket = {"shortcuts": [s["nhan"] or s["id"] for s in ds], "co_rating": bool(rating)}
    if mo and rating:
        m = re.search(r"act=(\S+).*?cmp=(\S+)", rating[0]["intent"])
        if m:
            await client.shell(serial, "am", "force-stop", package)
            await client.shell(serial, "am", "start", "-a", m.group(1), "-n", m.group(2).rstrip("}"),
                               "-f", "0x10008000")
            await asyncio.sleep(4.0)
            pkg, act = await _act(client, serial)
            ket.update({"mo": True, "man": act, "pkg": pkg})
    elif mo:
        ket["dung"] = "app không có shortcut Rating để mở"
    return ket
