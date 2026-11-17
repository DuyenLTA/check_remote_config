"""Tu lai app theo DUONG LAI IAA cua tung app (`data/iaa_duong_lai.yaml`), vua lai vua ghi log FA-SVC.

Truoc 13/11/2026 tool khong lai duoc cau "Di toi vi tri X dung nhu mo ta" -> Claude lai tay 36 case IAA (AIP893, >3 gio).
Duong lai khai mot lan cho moi app (cung khuon cong thuc tab rating: tap / tap_duoi / cho_man / xem_ads / chon_anh /
dong_neu_co / cho_chu / ve_man - chay bang `rating_cong_thuc`), them buoc rieng cua IAA:
  cho: <giay>              dung yen (dem reload banner 10s / native loading 5s)
  back: <so lan>           bam BACK
  mo_lai: <regex man goc>  force-stop + mo icon (session moi, "1 ad/session") roi lai FO toi man goc
  dong_ad: <giay>          cho toi <giay> (mac dinh 6) xem ad co hien khong (inter hien tre 1-2s sau khi bam), co thi dong
  shortcut: <regex id>     shortcut launcher cua app theo ID (doc nhan that tu `dumpsys shortcut`: "uninstall" tren may
                           tieng Viet la "Go cai dat" - TRUNG chu lenh go cua launcher). Icon tim theo ten app doc tu APK
                           (aapt); `app: <regex>` de ghi de.
                           Bam xong ma thay trinh go cai dat he thong -> BACK huy, bao loi (khong bao gio go that)
  xem_ads_chu: <regex nut> man cung activity (Compose): bam nut xem ad toi khi thay `toi_chu: <regex>`, dong ad giua
                           chung; node co chu ma bounds rong (AIP893 'Watch Ads (0/2)') thi bam `tap_tai: [x, y]` (ty le man);
                           `dung_neu: <regex>` (vd "Daily Free limit Reached") -> dung doan, bao het luot (khong mua sub);
                           `mua_sub_chu: <regex>` = nut mo Paywall tren sheet (AIP893 "Unlock Now"): CHI luong rating bam
                           de mua sub thay vi xem ads (IAA khong mua: app Pro mat het ads)
  ve_chu: <regex>          ve man goc nhan theo CHU (app Compose: moi man chung mot activity, `ve_man` bao xong ngay):
                           lai FO / mo lai app neu can, dong ad, BACK toi khi thay chu. `man: <regex activity>`,
                           `tab: <regex>` = tab duoi ve man goc (bam truoc khi BACK)
  nhap: <chu>              go chu vao o nhap (tim theo `o: <regex chu goi y>`), ban phim dang mo thi an di
  tap_neu_co: <regex>      bam neu co (nut them cua mot so app cung khuon), `thu: n` = nut thu n cung chu; man da co chu
                           `khi_thieu: <regex>` thi bo qua
Duong lai chia DOAN; doan hong (het gio, khong thay nut) thi ghi lai va sang doan sau - mot nut doi chu khong lam
mat ca luot. Moi doan nen bat dau bang `ve_man` ve Home.
"""

from __future__ import annotations

import asyncio
import re
import shlex
import time
from pathlib import Path

from . import device_app, fo_flow, rating_cong_thuc, ui_dump

DATA = Path(__file__).parent / "data" / "iaa_duong_lai.yaml"
TRANG_LAUNCHER_TOI_DA = 15            # vivo V2143: icon AIP893 o trang 9
SHORTCUT_TOI_DA = 120.0               # ca buoc shortcut (tim icon + nhan giu): qua thi bo doan, khong treo luot
CAI_DAT_RE = re.compile(r"packageinstaller|uninstaller", re.I)
AD_TRUOC_BUOC = ("tap", "tap_duoi", "cho_chu", "chon_anh")


def duong_lai(package: str) -> list[dict] | None:
    """Duong lai da khai cho app (rieng / ghim khuon); app chua khai thi `iaa_khuon.chon` nhan khuon tren may."""
    from . import iaa_khuon
    return iaa_khuon.doan_khai_san(package)[1]


async def cac_nhan_shortcut(client, serial: str, package: str, sid: str) -> list[str]:
    """[shortLabel, longLabel] cua shortcut co id khop regex `sid` (vd "(?i)uninstall": app dat id uninstall /
    UNINSTALL / shortcut_uninstall), theo ngon ngu may. Launcher co cho du rong thi hien longLabel (vivo V2143,
    AIP921 16/11/2026: shortLabel "Uninstall", popup ghi "Uninstall app") -> phai khop ca hai."""
    out, _, _ = await client.shell(serial, "dumpsys", "shortcut")
    khoi = re.split(r"ShortcutInfo \{", out or "")
    for k in khoi:
        m_id = re.match(r"id=([^,]+),", k)
        if m_id and re.fullmatch(sid, m_id.group(1)) and f"packageName={package}\n" in k + "\n":
            nhan = [m.group(1).strip() for m in re.finditer(r"(?:short|long)Label=([^,]+), resId", k)]
            nhan = [n for n in nhan if n and n != "null"]
            if nhan:
                return nhan
    return []


async def nhan_shortcut(client, serial: str, package: str, sid: str) -> str:
    """Nhan (shortLabel) cua shortcut co id khop regex `sid`."""
    nhan = await cac_nhan_shortcut(client, serial, package, sid)
    return nhan[0] if nhan else ""


async def _shortcut(client, serial: str, package: str, nhan_app: str, sid: str, log: list[str]) -> bool:
    """Nhan giu icon app tren launcher roi bam muc shortcut. Activity cua shortcut thuong khong export ->
    `am start` bi chan (AIP893 13/11/2026), chi launcher mo duoc. Toi da SHORTCUT_TOI_DA giay: Pixel 6 16/11/2026
    ket 7+ phut o day (lat 15 trang man hinh chinh, nhan giu tung icon trung tien to ten) -> dung, bao hong doan."""
    try:
        return await asyncio.wait_for(_shortcut_lam(client, serial, package, nhan_app, sid, log), SHORTCUT_TOI_DA)
    except asyncio.TimeoutError:
        log.append(f"quá {SHORTCUT_TOI_DA:.0f}s chưa mở được shortcut {sid!r} — bỏ đoạn này")
        await client.shell(serial, "input", "keyevent", "KEYCODE_HOME")
        return False


async def _shortcut_lam(client, serial: str, package: str, nhan_app: str, sid: str, log: list[str]) -> bool:
    if not nhan_app:
        from . import iaa_khuon
        ten = await iaa_khuon.nhan_icon(client, serial, package)
        if not ten:
            log.append("không đọc được tên icon từ APK (cần aapt trong Android SDK) — khai `app:` cho bước shortcut")
            return False
        # Khop DUNG ten (khong chi tien to): may test cai nhieu app AI photo cung tien to -> nhan giu nham tung icon.
        nhan_app = f"^{re.escape(ten)}$"
    cac_nhan = await cac_nhan_shortcut(client, serial, package, sid)
    if not cac_nhan:
        log.append(f"app không có shortcut id={sid!r} (dumpsys shortcut)")
        return False
    muc = "^(" + "|".join(map(re.escape, cac_nhan)) + ")$"
    for _ in range(2):                                  # HOME 2 lan: ve trang dau cua launcher
        await client.shell(serial, "input", "keyevent", "KEYCODE_HOME")
        await asyncio.sleep(1.0)
    # Pixel: icon app thuong chi nam trong ngan keo ung dung -> tim bang o tim kiem cua ngan keo truoc.
    kq = await _shortcut_ngan_keo(client, serial, package, nhan_app, cac_nhan, muc, log)
    if kq is not None:
        return kq
    for _ in range(2):
        await client.shell(serial, "input", "keyevent", "KEYCODE_HOME")
        await asyncio.sleep(1.0)
    for trang in range(TRANG_LAUNCHER_TOI_DA):
        nodes = ui_dump.parse_dump(await ui_dump.dump(client, serial))
        # Launcher co the co nhieu icon cung ten (ban cai khac / app khac trung ten, Pixel 4 13/11/2026: hai icon
        # "Sorapix: AI Hair Changer") -> thu lan luot; shortcut chi tinh khi man mo ra dung package dang test.
        icons = _icon_app(nodes, nhan_app)
        for icon in icons:
            kq = await _thu_icon(client, serial, package, icon, cac_nhan, muc, log)
            if kq is not None:
                return kq
        await client.shell(serial, "input", "swipe", "900", "1200", "150", "1200", "300")   # sang trang launcher
        await asyncio.sleep(1.5)                                                             # cho truot xong
        log.append(f"chưa thấy icon ở trang {trang + 1}")
    return False


def _icon_app(nodes, nhan_app: str) -> list:
    """Icon app tren launcher (TextView ten app), BO widget: widget cua app cung mang ten app nhung nhan giu
    khong ra muc shortcut (Pixel 6 AIP893 16/11/2026 nhan giu widget o (413,412) -> hong doan Uninstall)."""
    theo_id = {n.node_id: n for n in nodes}

    def trong_widget(n) -> bool:
        while n is not None:
            # class "android.widget.*" cung co chu widget -> chi xet AppWidgetHostView va resource-id
            if "AppWidget" in n.cls or re.search(r"widget", n.resource_id, re.I):
                return True
            n = theo_id.get(n.parent_id)
        return False
    return [n for n in nodes if rating_cong_thuc._khop(n, nhan_app) and not n.bounds.empty
            and n.cls.endswith("TextView") and not trong_widget(n)]


async def _shortcut_ngan_keo(client, serial, package, nhan_app, cac_nhan, muc, log) -> bool | None:
    """Mo ngan keo ung dung (vuot len tu day), go ten app vao o tim kiem, nhan giu icon ket qua.
    None = launcher khong co o tim kiem / khong ra icon -> de cach lat trang man hinh chinh lam tiep."""
    w, h = await device_app.screen_size(client, serial)
    await client.shell(serial, "input", "swipe", str(w // 2), str(int(h * 0.92)), str(w // 2), str(int(h * 0.25)), "300")
    await asyncio.sleep(1.5)
    nodes = ui_dump.parse_dump(await ui_dump.dump(client, serial))
    o_tim = next((n for n in nodes if not n.bounds.empty and re.search(
        r"search", f"{n.resource_id} {n.text} {n.content_desc}", re.I)), None)
    if o_tim is None:
        log.append("ngăn kéo ứng dụng không có ô tìm kiếm — tìm trên màn hình chính")
        return None
    await device_app.tap(client, serial, *o_tim.bounds.center)
    await asyncio.sleep(1.0)
    ten = re.sub(r"^\^|\$$", "", nhan_app).replace("\\", "")
    await client.shell(serial, "input", "text", shlex.quote(ten.split(":")[0].strip().replace(" ", "%s")))
    await asyncio.sleep(2.0)
    nodes = ui_dump.parse_dump(await ui_dump.dump(client, serial))
    icons = _icon_app(nodes, nhan_app)
    for icon in icons:
        kq = await _thu_icon(client, serial, package, icon, cac_nhan, muc, log)
        if kq is not None:
            return kq
    log.append(f"tìm '{ten}' trong ngăn kéo ứng dụng không ra icon — tìm trên màn hình chính")
    return None


async def _thu_icon(client, serial, package, icon, cac_nhan, muc, log) -> bool | None:
    """Nhan giu mot icon, bam muc shortcut. True = da mo shortcut cua app; False = dung (mo trinh go / app khac);
    None = icon nay khong ra muc shortcut -> thu icon khac."""
    nhan = cac_nhan[0]
    x, y = icon.bounds.center
    nut = None
    for _lan in range(2):               # nhan giu luc launcher con truot trang thi khong ra popup -> thu lai
        await client.shell(serial, "input", "swipe", str(x), str(y), str(x), str(y), "1500")
        for _ in range(4):              # popup shortcut hien cham (Pixel 4: >1,5s) -> do lai toi ~4s
            await asyncio.sleep(1.0)
            nut = rating_cong_thuc.tim(ui_dump.parse_dump(await ui_dump.dump(client, serial)), muc)
            if nut:
                break
        if nut:
            break
        await client.shell(serial, "input", "keyevent", "KEYCODE_BACK")
        await asyncio.sleep(1.0)
        # Popup chi co vai cho: app dang co thong bao thi muc shortcut bi day ra ngoai (Pixel 4 AIP885
        # 13/11/2026: "Your photo is almost here" -> chi con Rate Us / Create an Image). Xoa thong bao roi thu lai.
        log.append(f"popup icon ({x},{y}) chưa có mục {nhan!r} — tạm ẩn thông báo của app rồi nhấn giữ lại")
        await _xoa_thong_bao(client, serial, package)
    if not nut:
        log.append(f"nhấn giữ icon ({x},{y}) không thấy mục shortcut {muc!r}")
        await client.shell(serial, "input", "keyevent", "KEYCODE_BACK")
        await asyncio.sleep(1.0)
        return None
    await device_app.tap(client, serial, *nut.bounds.center)
    await asyncio.sleep(2.0)
    pkg, act = await device_app.focus(client, serial)
    if CAI_DAT_RE.search(f"{pkg} {act}"):
        for _ in range(2):
            await client.shell(serial, "input", "keyevent", "KEYCODE_BACK")
            await asyncio.sleep(1.0)
        log.append(f"mục {nhan!r} mở trình gỡ cài đặt của hệ thống — đã huỷ, không gỡ")
        return False
    if pkg and pkg != package:
        # Shortcut cua app KHAC trung ten: thoat ra, khong lam gi tren app do (HOME ve trang 1 -> dung tim).
        log.append(f"icon ({x},{y}) mở app khác ({pkg}) — thoát, không lái app đó")
        await client.shell(serial, "input", "keyevent", "KEYCODE_HOME")
        return False
    log.append(f"shortcut {nhan}")
    return True


async def _xoa_thong_bao(client, serial: str, package: str) -> None:
    """Tam an (snooze 10 phut) thong bao cua app: khong bam gi trong app, khong dung toi thong bao app khac."""
    out, _, _ = await client.shell(serial, "cmd", "notification", "list")
    for key in (k.strip() for k in (out or "").splitlines()):
        if f"|{package}|" in key:
            # key co "|" -> phai quote, khong thi shell may coi la pipe
            await client.shell(serial, "cmd", "notification", "snooze", "--for", "600000", shlex.quote(key))
    await asyncio.sleep(1.0)


async def _dong_ad_neu_co(client, serial: str, log: list[str]) -> bool:
    """Dang o AdActivity (inter/reward vua hien) -> dong an toan. True neu da dong mot ad."""
    _pkg, act = await device_app.focus(client, serial)
    if "AdActivity" not in (act or ""):
        return False
    log.append(await fo_flow.dong_ad_dang_che(client, serial, cho=45) or "chờ ad hết giờ")
    await asyncio.sleep(1.0)
    return True


async def _ve_chu(client, serial: str, package: str, b: dict, log: list[str]) -> bool:
    het = time.monotonic() + float(b.get("toi_da", 150))
    back = 0
    while time.monotonic() < het:
        if back and back % 4 == 0:
            # Ket (trinh chon anh / man ngoai app nuot BACK): BACK mai chi phi thoi gian -> dua app len lai.
            # Lan 2 van ket thi force-stop + mo lai (phien moi - ghi vao log de biet doan sau khong cung phien).
            if back >= 8:
                await client.shell(serial, "am", "force-stop", package)
                log.append("mở lại app từ đầu (phiên mới) vì BACK không về được màn gốc")
            else:
                log.append("đưa app lên lại (BACK không về được màn gốc)")
            await client.shell(serial, "monkey", "-p", package, "-c", "android.intent.category.LAUNCHER", "1")
            await asyncio.sleep(3.0)
            back += 1
            continue
        if not await rating_cong_thuc._mot_buoc(client, serial, package,
                                                {"ve_man": b.get("man", "MainActivity"), "toi_da": 120}, log):
            return False
        if await _dong_ad_neu_co(client, serial, log):
            continue
        nodes = await rating_cong_thuc._nodes(client, serial, package)
        if rating_cong_thuc.tim(nodes, b["ve_chu"]):
            return True
        # App co thanh tab duoi (AIP885: Home / Image Studio / Video Studio): BACK o tab khac khong ve tab Home
        # ma thoat app -> bam tab truoc (`tab: <regex>`), chi BACK khi khong co tab.
        tab = rating_cong_thuc.tim(nodes, b["tab"]) if b.get("tab") else None
        if tab and not back % 2:
            await device_app.tap(client, serial, *tab.bounds.center)
            log.append(f"bấm tab {tab.text or tab.content_desc}")
            back += 1
            await asyncio.sleep(1.5)
            continue
        await client.shell(serial, "input", "keyevent", "KEYCODE_BACK")
        back += 1
        log.append("BACK (chưa thấy chữ màn gốc)")
        await asyncio.sleep(1.5)
    log.append(f"không về được màn có chữ {b['ve_chu']!r}")
    return False


async def _co_man(client, serial: str) -> tuple[int, int]:
    out, _, _ = await client.shell(serial, "wm", "size")
    m = re.findall(r"(\d+)x(\d+)", out or "")
    return (int(m[-1][0]), int(m[-1][1])) if m else (1080, 2400)


async def _xem_ads_chu(client, serial: str, package: str, b: dict, log: list[str]) -> bool:
    het = time.monotonic() + float(b.get("toi_da", 150))
    rong, cao = await _co_man(client, serial)
    bam_khong_mo = 0
    while time.monotonic() < het:
        _pkg, act = await device_app.focus(client, serial)
        if "AdActivity" in (act or ""):
            bam_khong_mo = 0
            log.append(await fo_flow.dong_ad_dang_che(client, serial, cho=45) or "chờ ad hết giờ")
            continue
        if bam_khong_mo >= rating_cong_thuc.BAM_KHONG_MO_TOI_DA:
            log.append(rating_cong_thuc.KHONG_FILL_THUONG)
            return False
        nodes = await rating_cong_thuc._nodes(client, serial, package)
        chan = rating_cong_thuc.tim(nodes, b["dung_neu"]) if b.get("dung_neu") else None
        if chan:
            # Het luot gen free trong ngay: KHONG mua sub (app Pro thi mat het ads, lam hong ca bo IAA).
            raise rating_cong_thuc.HetLuot(chan.text or chan.content_desc)
        if b.get("toi_chu") and rating_cong_thuc.tim(nodes, b["toi_chu"]):
            log.append("xem ads xong")
            return True
        mua = rating_cong_thuc.tim(nodes, b["mua_sub_chu"]) if b.get("mua_sub") and b.get("mua_sub_chu") else None
        if mua is not None:
            raise rating_cong_thuc.MuaSub(mua)        # chi luong rating bat `mua_sub`: mua thay vi cho reward ad
        nut = next((n for n in nodes if rating_cong_thuc._khop(n, b["xem_ads_chu"])), None)
        if nut is not None:
            if nut.bounds.empty and b.get("tap_tai"):
                x, y = (int(rong * float(b["tap_tai"][0])), int(cao * float(b["tap_tai"][1])))
            elif not nut.bounds.empty:
                x, y = nut.bounds.center
            else:
                log.append(f"nút {nut.text!r} không có toạ độ — khai tap_tai")
                return False
            log.append(f"bấm {nut.text or nut.content_desc}")
            await device_app.tap(client, serial, x, y)
            bam_khong_mo += 1
            await asyncio.sleep(4.0)
            continue
        await asyncio.sleep(rating_cong_thuc.NHIP)
    log.append(f"hết giờ ở {b}")
    return False


def co_chu(nodes, mau: str) -> bool:
    """Co node nao khop chu `mau` - KE CA node khong co toa do (Compose: nut "Continue", tab duoi tra bounds rong)."""
    return any(rating_cong_thuc._khop(n, mau) for n in nodes)


async def buoc(client, serial: str, package: str, b: dict, log: list[str]) -> bool:
    if "neu_co" in b:
        # Buoc tuy chon: chi lam khi man dang co chu `neu_co` (vd man thiet lap ho so chi hien lan dau sau pm clear).
        await _dong_ad_neu_co(client, serial, log)
        if not co_chu(await rating_cong_thuc._nodes(client, serial, package), b["neu_co"]):
            return True
        b = {k: v for k, v in b.items() if k != "neu_co"}
    if "cap_quyen" in b:
        # Hop thoai quyen he thong (permissioncontroller) khong thuoc package app -> buoc tap/cho_chu khong thay.
        # Cap truoc bang pm grant (AIP921: inter hien truoc hop quyen Camera cua AI Scan, 16/11/2026).
        for quyen in ([b["cap_quyen"]] if isinstance(b["cap_quyen"], str) else b["cap_quyen"]):
            await client.shell(serial, "pm", "grant", package, quyen)
        log.append(f"cấp quyền {b['cap_quyen']}")
        return True
    if "tap_toa_do" in b:
        # Nut Compose co chu nhung uiautomator tra bounds rong (AIP921: "Continue", tab Workout / Nutrition):
        # bam theo ti le man hinh [x, y].
        rong, cao = await _co_man(client, serial)
        fx, fy = b["tap_toa_do"]
        await device_app.tap(client, serial, int(rong * float(fx)), int(cao * float(fy)))
        await asyncio.sleep(float(b.get("cho_sau", 2.0)))
        log.append(f"bấm toạ độ {fx},{fy}")
        return True
    if "cho" in b:
        await asyncio.sleep(float(b["cho"]))
        log.append(f"chờ {b['cho']}s")
        return True
    if "back" in b:
        for _ in range(int(b["back"])):
            await client.shell(serial, "input", "keyevent", "KEYCODE_BACK")
            await asyncio.sleep(1.2)
        log.append(f"BACK ×{b['back']}")
        return True
    if "tap_neu_co" in b:
        # Buoc phu cua khuon chung: app co them nut (AIP885 tab Video Studio -> the "Image to Video" + nut Generate)
        # thi bam; man da co chu `khi_thieu` (app khac vao thang man tinh nang) thi bo qua. Khong thay nut = bo qua.
        await asyncio.sleep(float(b.get("cho_truoc", 2.0)))
        await _dong_ad_neu_co(client, serial, log)
        nodes = await rating_cong_thuc._nodes(client, serial, package)
        if b.get("khi_thieu") and rating_cong_thuc.tim(nodes, b["khi_thieu"]):
            return True
        khop = [n for n in nodes if rating_cong_thuc._khop(n, b["tap_neu_co"]) and not n.bounds.empty]
        thu = int(b.get("thu", 1))                # nut thu may (tren xuong) khi man co nhieu nut cung chu
        node = khop[thu - 1] if 0 < thu <= len(khop) else None
        if node:
            await device_app.tap(client, serial, *node.bounds.center)
            await asyncio.sleep(rating_cong_thuc.NHIP)
            log.append(f"bấm {node.text or node.content_desc}")
        return True
    if "dong_ad" in b:
        het = time.monotonic() + float(b["dong_ad"] if not isinstance(b["dong_ad"], bool) else 6)
        while time.monotonic() < het:
            if await _dong_ad_neu_co(client, serial, log):
                break
            await asyncio.sleep(0.5)
        return True
    if set(AD_TRUOC_BUOC) & set(b):
        # Ad (inter tre / app open resume khi ve app) co the hien GIUA luc cho nut: cu ~5s dong ad neu co roi thu lai,
        # toi het `toi_da` (vivo 13/11/2026: buoc tap o Home het gio vi app open che Home).
        het = time.monotonic() + float(b.get("toi_da", rating_cong_thuc.TOI_DA_MAC_DINH))
        while True:
            await _dong_ad_neu_co(client, serial, log)
            con = het - time.monotonic()
            tam: list[str] = []
            if await rating_cong_thuc._mot_buoc(client, serial, package, {**b, "toi_da": max(1.0, min(5.0, con))}, tam):
                log.extend(tam)
                return True
            if time.monotonic() >= het:
                log.extend(tam)
                return False
    if "mo_lai" in b:
        await device_app.force_stop(client, serial, package)
        await device_app.launch(client, serial, package)
        log.append("mở lại app (session mới)")
        return await rating_cong_thuc._mot_buoc(client, serial, package,
                                                 {"ve_man": b["mo_lai"], "toi_da": b.get("toi_da", 120)}, log)
    if "xem_ads_chu" in b:
        return await _xem_ads_chu(client, serial, package, b, log)
    if "ve_chu" in b:
        return await _ve_chu(client, serial, package, b, log)
    if "nhap" in b:
        await _dong_ad_neu_co(client, serial, log)
        node = rating_cong_thuc.tim(await rating_cong_thuc._nodes(client, serial, package), b.get("o", "."))
        if not node:
            log.append(f"không thấy ô nhập {b.get('o')!r}")
            return False
        await device_app.tap(client, serial, *node.bounds.center)
        await asyncio.sleep(1.0)
        await client.shell(serial, "input", "text", str(b["nhap"]).replace(" ", "%s"))
        await asyncio.sleep(0.8)
        ime, _, _ = await client.shell(serial, "dumpsys", "input_method")
        if "mInputShown=true" in (ime or ""):
            await client.shell(serial, "input", "keyevent", "KEYCODE_BACK")     # chi dong ban phim, khong roi man
            await asyncio.sleep(0.8)
        log.append(f"nhập {b['nhap']!r}")
        return True
    if "shortcut" in b:
        return await _shortcut(client, serial, package, b.get("app", ""), str(b["shortcut"]), log)
    return await rating_cong_thuc._mot_buoc(client, serial, package, b, log)


async def lai(client, serial: str, package: str, doan: list[dict], file_log: Path, log_fn=lambda _m: None) -> dict:
    """Chay moi doan cua duong lai, ghi `logcat -v epoch -s FA-SVC:V` vao `file_log` suot luot.
    -> {"doan": [{ten, xong, log}], "giay": ...}."""
    file_log.parent.mkdir(parents=True, exist_ok=True)
    adb = getattr(client, "adb", "adb") or "adb"
    await client.shell(serial, "setprop", "log.tag.FA-SVC", "VERBOSE")
    with open(file_log, "w", encoding="utf-8") as f:
        ghi = await asyncio.create_subprocess_exec(adb, "-s", serial, "logcat", "-v", "epoch", "-s", "FA-SVC:V",
                                                   stdout=f, stderr=asyncio.subprocess.DEVNULL)
        bat_dau, kq = time.monotonic(), []
        try:
            for d in doan:
                nhat_ky: list[str] = []
                xong = True
                for b in d.get("buoc") or []:
                    try:
                        if not await buoc(client, serial, package, b, nhat_ky):
                            xong = False
                            break
                    except rating_cong_thuc.HetLuot as exc:
                        nhat_ky.append(f"app báo hết lượt: {exc}")
                        xong = False
                        break
                    except Exception as exc:          # dump UI loi thoang qua (vivo: "No such file") -> hong doan nay
                        nhat_ky.append(f"lỗi ở bước {b}: {type(exc).__name__}: {str(exc)[:160]}")
                        xong = False
                        break
                kq.append({"ten": d.get("ten", ""), "xong": xong, "log": nhat_ky})
                log_fn(f"  đoạn '{d.get('ten', '')}': {'xong' if xong else 'HỎNG'} — {'; '.join(nhat_ky[-3:])}")
        finally:
            await asyncio.sleep(2.0)            # FA-SVC ghi event tre ~1s
            ghi.terminate()
            await ghi.wait()
    return {"doan": kq, "giay": round(time.monotonic() - bat_dau)}
