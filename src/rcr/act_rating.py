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
import shlex
import time
from dataclasses import dataclass

from . import device_app, log_moc, rating_cong_thuc, rating_may, ui_dump
from .adb_parsers import AdbError

GEN_RE = re.compile(r"^\s*gen\s+(ảnh|anh|video)\b", re.I)
BAM_X_SAU_RE = re.compile(r"b[ấa]m\s+x\b", re.I)
SAO_RE = re.compile(r"^\s*(?:ch[ọo]n|đ[ổo]i\s+sang|doi\s+sang)\s+([1-5])\s*sao\b(?P<rest>.*)$", re.I)
BAM_NUT_RE = re.compile(r"b[ấa]m\s+(?:button|n[úu]t|[\"“])", re.I)
X_RE = re.compile(r"^\s*b[ấa]m\s+(?:n[úu]t\s+|button\s+)?x\b", re.I)
# "Nhap "Test feedback QA <timestamp>"." (man Feedback cua rating, R02): go chu vao o nhap. Truoc day buoc nay ra
# needs_human -> o feedback trong, nut Submit khong bat, R02-03 khong bao gio thay toast (AIP893 17/11/2026, 4 vong).
NHAP_RE = re.compile(r"^\s*nh[ậa]p\s+[\"“”']([^\"“”']+)[\"“”']", re.I)
THOAT_RE = re.compile(r"^\s*(?:th[ựu]c\s+hi[ệe]n\s+(?:thao\s+t[áa]c\s+)?)?tho[áa]t\s+app\b", re.I)
BACK_RE = re.compile(r"^\s*b[ấa]m\s+(?:←|back|n[úu]t\s+back)\s+(?:tr[êe]n|t[ừu])\b", re.I)
SHORTCUT_RE = re.compile(r"^\s*nh[ấa]n\s+gi[ữu]\s+icon\s+app\b(?P<rest>.*)$", re.I)
CHON_RATING_RE = re.compile(r"ch[ọo]n\s+(?:option\s+)?rat", re.I)
BAM_GIO_POPUP_RE = re.compile(r"b[ấa]m\s+gi[ờo].*popup", re.I)

HOME_RE = re.compile(r"Main|Home", re.I)     # activity Home cua app (AIP892: MainActivity)
MAN_RESULT_CHU = "^Result$"                   # tieu de man Result cua app Compose (AIP893) - BACK ve Home truoc khi thoat
CHUP_GIAY = 6.0         # cua so chup lien tuc tu luc toi result / bam BACK: du cho show_rating_button_x toi 4-5s
CHO_POPUP = 8.0
KHOI_DONG_CHUP = 0.8
DO_LAI = 2              # so lan tu lam lai buoc rating khi buoc dung giua chung / lan do X khong du de cham
SAI_SO_X_CHUP = 0.6     # = assert_rating.SAI_SO_X: khung dau cach popup <= muc nay coi nhu chup tu luc popup hien
SAU_THAO_TAC = 1.5


@dataclass(frozen=True, slots=True)
class Rating:
    viec: str            # gen | sao | x | thoat | back | shortcut | da_do
    reason: str
    loai: str = ""
    sao: int = 0
    bam: bool = False
    chu: str = ""

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
    m = NHAP_RE.match(text)
    if m:
        return Rating("nhap", f"gõ {m.group(1)!r} vào ô nhập", chu=m.group(1))
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
    ket = await _lam_an_toan(client, serial, package, action, moc)
    # Chi PASS/FAIL: buoc dung giua chung hay lan do X khong du de cham thi tu lam lai (dong popup con mo, lam lai ca
    # buoc) chu khong tra viec cho nguoi. Het DO_LAI lan van vay thi assert_rating cham FAIL kem ly do.
    lam_lai: list[str] = []
    while len(lam_lai) < DO_LAI:
        if ket.get("dung"):
            if not _dung_lam_lai_duoc(ket["dung"]):
                break
            vi_sao = f"bước dừng: {ket['dung']}"
        elif action.viec in ("gen", "thoat") and ket.get("popup") and _do_x_chua_ro(ket.get("do_x")):
            vi_sao = _do_x_chua_ro(ket.get("do_x"))
        else:
            break
        lam_lai.append(vi_sao)
        await _dong_popup_rating(client, serial, package)
        moc = await log_moc.bay_gio(client, serial)
        ket = await _lam_an_toan(client, serial, package, action, moc)
    record["rating"] = {"viec": action.viec, **ket, "do_lai": len(lam_lai), "lam_lai_vi": lam_lai,
                        "su_kien": await rating_may.su_kien(client, serial, moc)}
    if ket.get("dung"):
        record["dung_lai"] = ket["dung"]


async def _lam_an_toan(client, serial: str, package: str, action: Rating, moc: str) -> dict:
    try:
        return await _lam(client, serial, package, action, moc)
    except (AdbError, OSError, ValueError, TypeError, KeyError) as exc:
        # Loi bat ngo trong mot buoc khong duoc lam sap ca luot (cac case sau van phai chay): dung case nay.
        return {"dung": f"lỗi khi làm bước rating {action.viec}: {type(exc).__name__}: {exc}"}


async def _dong_popup_rating(client, serial: str, package: str) -> None:
    """Truoc khi lam lai: popup Rating con mo thi bam X (khong co X thi BACK) de lan sau bat dau tu man sach."""
    try:
        pop = await rating_may.nhin(client, serial, package)
        if pop.get("x"):
            await device_app.tap(client, serial, *pop["x"])
        elif pop.get("hien"):
            await client.shell(serial, "input", "keyevent", "KEYCODE_BACK")
        await asyncio.sleep(SAU_THAO_TAC)
    except (AdbError, OSError, ValueError):
        pass


async def _lam(client, serial: str, package: str, action: Rating, moc: str) -> dict:
    if action.viec == "gen":
        ket = await _gen(client, serial, package, action, moc)
    elif action.viec == "sao":
        ket = await _sao(client, serial, package, action)
    elif action.viec == "x":
        ket = await _x(client, serial, package)
    elif action.viec == "nhap":
        ket = await _nhap(client, serial, package, action.chu)
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


def _do_x_chua_ro(do_x: dict | None) -> str:
    """Lan do X nay khong du de cham -> ly do (rong = do duoc). Ba truong hop:
    - khong co khung chup nao (loi doc khung / khong thay nut X luc do);
    - chup bat dau tre: khung dau da co X ma cach popup > SAI_SO_X_CHUP (AIP893 17/11/2026: 12.9s / 13.05s; lan chay
      lai do dung 2.0s) -> chi biet X hien <= khung dau;
    - hai khung ke nhau quanh luc X hien cach nhau > 2*SAI_SO_X_CHUP (may giat) -> khong biet X hien o giua luc nao."""
    do_x = do_x or {}
    hien, chua = do_x.get("x_hien_s"), do_x.get("x_chua_hien_luc_s")
    if not do_x.get("khung"):
        return f"không có khung chụp ({do_x.get('loi') or 'chưa chụp'})"
    if do_x.get("co_tu_khung_dau") and (hien or 0) > SAI_SO_X_CHUP:
        return f"khung chụp đầu đã có X ({hien}s sau popup) — chụp bắt đầu trễ"
    if hien is not None and chua is not None and hien - chua > 2 * SAI_SO_X_CHUP:
        return f"hở khung chụp từ {chua}s tới {hien}s quanh lúc X hiện"
    return ""


def _dung_lam_lai_duoc(dung: str) -> bool:
    """Buoc dung vi luc chay (gen khong toi result, popup chua len, loi adb) thi lam lai co the qua. Thieu cong thuc gen
    / app khong co shortcut Rating thi lam lai van vay."""
    return not re.search(r"chưa có công thức|không có shortcut Rating", dung)


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


def _chu_go(chu: str) -> str:
    """`<timestamp>` trong TC -> moc gio that (moi lan gui feedback mot noi dung khac)."""
    return re.sub(r"<\s*timestamp\s*>", time.strftime("%Y%m%d-%H%M%S"), chu, flags=re.I)


async def _nhap(client, serial: str, package: str, chu: str) -> dict:
    """Go chu vao o nhap dau tien cua man (EditText), roi dong ban phim (BACK luc ban phim mo chi dong ban phim)."""
    nodes = ui_dump.app_nodes(ui_dump.parse_dump(await ui_dump.dump(client, serial)), package)
    o = next((n for n in nodes if "EditText" in (n.cls or "") and not n.bounds.empty), None)
    if o is None:
        return {"dung": "không thấy ô nhập chữ trên màn"}
    await device_app.tap(client, serial, *o.bounds.center)
    await asyncio.sleep(1.0)
    go = _chu_go(chu)
    # `input text`: dau cach -> %s; chu dac biet cua shell may -> quote ca chuoi
    await client.shell(serial, "input", "text", shlex.quote(go.replace(" ", "%s")))
    await asyncio.sleep(0.8)
    ime, _, _ = await client.shell(serial, "dumpsys", "input_method")
    if "mInputShown=true" in (ime or ""):
        await client.shell(serial, "input", "keyevent", "KEYCODE_BACK")
        await asyncio.sleep(0.8)
    sau = ui_dump.app_nodes(ui_dump.parse_dump(await ui_dump.dump(client, serial)), package)
    da_go = any(go in (n.text or "") for n in sau if "EditText" in (n.cls or ""))
    _, act = await _act(client, serial)
    return {"chu": go, "da_go": da_go, "man": act} if da_go else {"dung": f"gõ {go!r} mà ô nhập không có chữ đó"}


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
    # App Compose (AIP893: Home / Result chung MainActivity): ten activity khop HOME_RE ca khi dang o Result -> nhan
    # Home bang chu `ve_chu` cua cong thuc gen anh (chu chi co o Home), khong co cong thuc thi theo ten activity.
    ds = rating_cong_thuc.cong_thuc(package, "anh") or []
    chu_home = next((b["ve_chu"] for b in ds if b.get("ve_chu")), None)
    for _ in range(3):
        pkg, act = await _act(client, serial)
        if pkg != package:
            break
        if HOME_RE.search(act):
            if not chu_home:
                break
            try:
                nodes = ui_dump.app_nodes(ui_dump.parse_dump(await ui_dump.dump(client, serial)), package)
            except (AdbError, ValueError):
                nodes = []
            # Chi BACK khi chac dang o Result (tieu de "Result"); khong thay chu Home vi popup che thi KHONG BACK
            # (BACK o Home la thoat app, mat buoc can do).
            # Tieu de "Result" thang chu Home: cay Compose cua AIP893 giu ca node Home an duoi Result (13:07 17/11/2026
            # R07-01: co chu Home trong dump ma man dang la Result -> khong BACK, FAIL gia "app thoat").
            if not rating_cong_thuc.tim(nodes, MAN_RESULT_CHU):
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


# "Rate on Google Play" mo trang app dang SHEET (TransparentMainActivityPrivate) chong len trang chu Store: BACK 1 dong
# sheet -> trang chu Play, BACK 2 moi ve app. QA chot 17/11/2026: back 2 lan moi ve app la DUNG (Store dang hien popup
# trang app), khong phai bug -> "Back tu Google Play" = BACK toi khi roi Store, toi da BACK_STORE_TOI_DA lan.
BACK_STORE_TOI_DA = 2


async def _back(client, serial: str, package: str) -> dict:
    _, truoc = await _act(client, serial)
    so_back, qua = 0, []
    while True:
        await client.shell(serial, "input", "keyevent", "KEYCODE_BACK")
        so_back += 1
        het = time.monotonic() + 8.0
        pkg, act = await _act(client, serial)
        while pkg != package and time.monotonic() < het:      # Google Play dong cham
            await asyncio.sleep(1.0)
            pkg, act = await _act(client, serial)
        await asyncio.sleep(SAU_THAO_TAC)
        pkg, act = await _act(client, serial)
        qua.append(f"{pkg}/{(act or '').rsplit('.', 1)[-1]}")
        if pkg != rating_may.GOOGLE_PLAY or so_back >= BACK_STORE_TOI_DA:
            break
    # App Compose (Home / Result chung mot activity): ten activity khong noi man nao -> giu chu tren man de cham
    # "Back ve man result" theo tieu de man, khong theo ten activity.
    chu: list[str] = []
    if pkg == package:
        try:
            nodes = ui_dump.app_nodes(ui_dump.parse_dump(await ui_dump.dump(client, serial)), package)
            chu = [n.text for n in nodes if getattr(n, "text", "")][:60]
        except (AdbError, ValueError):
            chu = []
    return {"truoc": truoc, "pkg": pkg, "man": act, "trong_app": pkg == package, "so_back": so_back, "qua": qua,
            "chu": chu}


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
