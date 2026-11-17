"""Chay cong thuc lai app toi man result cua tab TC rating (`data/rating_gen.yaml`) - buoc "Gen anh / gen video".

Gen anh moi app mot kieu (chon style, chon anh, xem reward ad...) nen khong doan: cong thuc ghi tung buoc theo chu tren
man, them app moi la them muc vao file YAML. Dong quang cao dung lai `fo_flow.dong_ad_dang_che` cua rc-check (chi bam
dung nut dong, ad test khong co node nut thi BACK sau thoi gian toi thieu).
"""

from __future__ import annotations

import asyncio
import re
import time
from pathlib import Path

from . import device_app, fo_flow, ui_dump

DATA = Path(__file__).parent / "data" / "rating_gen.yaml"
TOI_DA_MAC_DINH = 30.0
# Bam "Watch Ads" bay nhieu lan lien ma khong mo AdActivity -> ad thuong khong load (kho khong fill): dung, khong cho het
# 150-300s cua buoc (dem 16/11/2026 may R58 khong load duoc reward, moi lan gen ton toi da 5 phut).
BAM_KHONG_MO_TOI_DA = 2
KHONG_FILL_THUONG = "bấm Watch Ads 2 lần không mở quảng cáo thưởng — ad thưởng không load (kho không fill)"
NHIP = 1.0
DONG_TOI_DA = 4
LUONG_FO_RE = re.compile(r"Splash|AdActivity|Language|Onboarding|Question|Billing", re.I)
GOI_SUB = "weekly"      # goi test ngan nhat (chu ky test 5 phut)
# Mua sub qua nut tren sheet xem ads (AIP893 "Unlock Now"): user chot 17/11/2026 CHI mua weekly hoac monthly, KHONG
# BAO GIO yearly. Goi test weekly het han sau ~30 phut (5 phut x 6 lan gia han) -> xem MUA_LAI_SAU.
GOI_SUB_UU_TIEN = ("weekly", "monthly")
# Sau chung nay giay ke tu lan mua truoc, sheet xem ads hien lai = goi test da het han -> mua lai, khong lui ve xem ads
# (may khong fill rewarded thi moi lan gen mat 5-10 phut roi hong).
MUA_LAI_SAU = 25 * 60
# (serial, package) -> luc da mua (hoac da thu mua) qua nut trong tien trinh nay: sub gan voi tai khoan Play, clear
# data van con -> trong MUA_LAI_SAU chi mua mot lan, mua hong cung khong thu lai moi case.
_DA_MUA_QUA_NUT: dict[tuple[str, str], float] = {}


def nen_mua_qua_nut(serial: str, package: str, bay_gio: float | None = None) -> bool:
    """Chua mua lan nao trong tien trinh, hoac lan truoc da qua MUA_LAI_SAU (goi test weekly da het han)."""
    luc = _DA_MUA_QUA_NUT.get((serial, package))
    return luc is None or (time.monotonic() if bay_gio is None else bay_gio) - luc >= MUA_LAI_SAU
# Trinh chon anh he thong: o anh co desc "Photo taken on ..." (photopicker Android 13+), nut xac nhan Done / Add.
ANH_RE = re.compile(r"^(?:Photo|Ảnh|Anh)\b.*(?:taken|chụp|chup)", re.I)
XAC_NHAN_ANH_RE = re.compile(r"^(?:Done|Add|Select|Xong|Thêm|Chọn)$", re.I)
TRINH_CHON_RE = re.compile(r"(?:providers\.media|photopicker|documentsui|com\.google\.android\.apps\.photos"
                           r"|gallery|android\.media)", re.I)


def cong_thuc(package: str, loai: str, nodes=None) -> list[dict] | None:
    """Danh sach buoc cua app `package` cho `loai` ("anh" / "video"); app chua khai -> khuon khop chu Home
    (`nodes`), khong khop -> None."""
    import yaml
    from . import cong_thuc_khuon
    data = yaml.safe_load(DATA.read_text(encoding="utf-8")) or {}
    return (cong_thuc_khuon.chon(data, package, nodes)[1] or {}).get(loai)


def ep_cau_hinh(package: str) -> dict[str, str]:
    """Config tool phai TU DAT cho moi case tab rating cua app (muc `ep_cau_hinh` trong rating_gen.yaml).

    App gen ngam (AIP893): man cho tu ve Home truoc khi anh xong -> result mo tu History khong ban popup
    `placement=result`; phai giu `generating_wait_*` dai de result mo thang tu man cho. Dat bang `--set --keep`
    khong duoc: moi lenh rcr-check doc baseline la go het gia tri testvsl. Key cua case van thang (gop sau)."""
    import yaml
    data = yaml.safe_load(DATA.read_text(encoding="utf-8")) or {}
    muc = data.get(package) or {}
    return {str(k): str(v) for k, v in (muc.get("ep_cau_hinh") or {}).items()}


async def cong_thuc_tren_may(client, serial: str, package: str, loai: str, log: list[str]) -> list[dict] | None:
    """Nhu cong_thuc; app chua khai thi ve Home, doc chu tren Home roi chon khuon dung chung."""
    buoc = cong_thuc(package, loai)
    if buoc:
        return buoc
    await _mot_buoc(client, serial, package, {"ve_man": "MainActivity|HomeActivity", "toi_da": 60}, log)
    buoc = cong_thuc(package, loai, await _nodes(client, serial, package))
    if buoc:
        log.append(f"app chưa có công thức riêng — dùng khuôn chung khớp chữ Home ({loai})")
    return buoc


def _khop(n, mau: str) -> bool:
    return any(re.search(mau, s or "", re.I) for s in (n.text, n.content_desc))


def tim(nodes, mau: str):
    return next((n for n in nodes if _khop(n, mau) and not n.bounds.empty), None)


def tim_duoi(nodes, mau: str, thu: int = 1):
    """Node bam duoc thu `thu` (dem tu trai) o hang dau tien nam duoi node co chu khop (the anh mau / the template
    khong co chu). The cuoi hang chi lo mot mep van tap duoc: tap vao giua phan dang hien."""
    moc = tim(nodes, mau)
    if moc is None:
        return None
    # The anh co content-desc nhung KHONG clickable (Pixel 4, AIP893 13/11/2026: 'Vertical 9:16 ...'): chi tinh
    # clickable thi hang dau tien thanh View quang cao ben duoi -> bam nham ad.
    duoi = [n for n in nodes if (n.clickable or (n.content_desc and not n.text)) and not n.bounds.empty
            and n.bounds.top >= moc.bounds.bottom]
    if not duoi:
        return None
    hang = min(n.bounds.top for n in duoi)
    cung_hang: list = []
    for n in sorted((n for n in duoi if abs(n.bounds.top - hang) <= 8), key=lambda n: (n.bounds.left, not n.clickable)):
        if not cung_hang or abs(n.bounds.left - cung_hang[-1].bounds.left) > 8:   # the + anh trong the: 1 o
            cung_hang.append(n)
    return cung_hang[thu - 1] if 0 < thu <= len(cung_hang) else None


async def _nodes(client, serial: str, package: str):
    return ui_dump.app_nodes(ui_dump.parse_dump(await ui_dump.dump(client, serial)), package)


async def _bam(client, serial: str, node) -> None:
    await device_app.tap(client, serial, *node.bounds.center)
    await asyncio.sleep(NHIP)


def o_trong(png: bytes, bounds, nguong: int = 60) -> bool:
    """O anh con trong (khung net dut tren nen toi): mot hang diem ngang o 1/4 chieu cao deu toi (hang giua trung icon
    anh xam cua o trong). O da co anh thi co diem sang."""
    from io import BytesIO
    from PIL import Image
    im = Image.open(BytesIO(png)).convert("L")
    y = min(max(bounds.top + (bounds.bottom - bounds.top) // 4, 0), im.height - 1)
    xs = range(max(bounds.left + 20, 0), min(bounds.right - 20, im.width - 1), 15)
    return all(im.getpixel((x, y)) < nguong for x in xs)


def nut_bat(nodes, mau: str) -> bool:
    """Nut co chu khop `mau` dang bat: node chu hoac node bam duoc chua no phai enabled (Compose de enabled o node cha)."""
    chu = tim(nodes, mau)
    if chu is None:
        return False
    cha = [n for n in nodes if n.clickable and n.bounds.left <= chu.bounds.left and n.bounds.right >= chu.bounds.right
           and n.bounds.top <= chu.bounds.top and n.bounds.bottom >= chu.bounds.bottom]
    return all(n.enabled for n in cha) and chu.enabled


async def _dien_o_anh(client, serial: str, package: str, buoc: dict, het: float, log: list[str]) -> bool:
    """Template nhieu o anh (AIP927 Pictifaze: 'Cinematic Crossfade' co 5 o, phai dien DU moi bat 'Generate with
    Ads'; o nam trong carousel ngang duoi chu moc, o thu 3 tro di phai cuon moi thay). Lap: nut xong da bat -> xong; o trong
    dang hien -> bam, chon nguon (`nguon`, vd Gallery), chon anh thu k (moi o mot anh khac); khong con o trong -> cuon."""
    from . import screencap
    k = 0
    while time.monotonic() < het:
        nodes = await _nodes(client, serial, package)
        if nut_bat(nodes, buoc["xong"]):
            log.append(f"điền {k} ảnh — nút {buoc['xong']!r} đã bật")
            return True
        moc, nut = tim(nodes, buoc["dien_o_anh"]), tim(nodes, buoc["xong"])
        if moc is None or nut is None:
            await asyncio.sleep(NHIP)
            continue
        png = await screencap.raw(client, serial)
        o = next((n for n in nodes if n.clickable and n.bounds.top >= moc.bounds.bottom
                  and n.bounds.bottom <= nut.bounds.top and n.bounds.right - n.bounds.left >= 150
                  and o_trong(png, n.bounds)), None)
        if o is None:
            await client.shell(serial, "input", "swipe", "900", str(moc.bounds.bottom + 800),
                               "150", str(moc.bounds.bottom + 800), "1500")
            await asyncio.sleep(NHIP)
            continue
        await _bam(client, serial, o)
        await asyncio.sleep(2.0)
        if buoc.get("nguon"):
            nguon = tim(await _nodes(client, serial, package), buoc["nguon"])
            if nguon:
                await _bam(client, serial, nguon)
                await asyncio.sleep(2.0)
        k += 1
        if not await _chon_anh(client, serial, min(het, time.monotonic() + 30), log, thu=k):
            return False
        await asyncio.sleep(2.0)
    log.append(f"điền {k} ảnh mà nút {buoc['xong']!r} chưa bật")
    return False


async def _chon_anh(client, serial: str, het: float, log: list[str], thu: int = 1) -> bool:
    """Trinh chon anh he thong (photopicker / Google Photos): bam anh thu `thu` (mac dinh anh dau tien) roi nut xac
    nhan neu co."""
    da_bam = False
    while time.monotonic() < het:
        if not da_bam:
            # Bam template co the bat inter truoc trinh chon anh (AIP893 Pixel 4 13/11/2026) -> dong ad roi doi tiep.
            _pkg, act = await device_app.focus(client, serial)
            if "AdActivity" in (act or ""):
                log.append(await fo_flow.dong_ad_dang_che(client, serial, cho=45) or "chờ ad hết giờ")
                continue
        nodes = ui_dump.parse_dump(await ui_dump.dump(client, serial))
        if not da_bam:
            cac_anh = [n for n in nodes if ANH_RE.search(n.content_desc or "") and not n.bounds.empty]
            anh = cac_anh[min(thu, len(cac_anh)) - 1] if cac_anh else None
            if anh:
                await _bam(client, serial, anh)
                log.append("chọn ảnh đầu tiên" if thu == 1 else f"chọn ảnh thứ {thu}")
                da_bam = True
                continue
        else:
            nut = next((n for n in nodes if XAC_NHAN_ANH_RE.match(n.text or "") and not n.bounds.empty), None)
            if nut:
                await _bam(client, serial, nut)
                log.append(f"bấm {nut.text}")
                return True
            pkg, _ = await device_app.focus(client, serial)
            # So theo package trinh chon anh, khong so chu "photo": app AIP893 ten com.aiphotogenerator... (13/11/2026).
            if pkg and not TRINH_CHON_RE.search(pkg):
                return True                      # trinh chon dong ngay sau khi bam anh (chon 1 anh)
        await asyncio.sleep(NHIP)
    log.append("không chọn được ảnh trong trình chọn ảnh")
    return False


async def _mot_buoc(client, serial: str, package: str, buoc: dict, log: list[str]) -> bool:
    het = time.monotonic() + float(buoc.get("toi_da", TOI_DA_MAC_DINH))
    bam_khong_mo = 0                  # xem_ads: so lan bam nut lien ma chua thay AdActivity
    if "chon_anh" in buoc:
        return await _chon_anh(client, serial, het, log)
    if "dien_o_anh" in buoc:
        return await _dien_o_anh(client, serial, package, buoc, het, log)
    if "cho_chu" in buoc:
        while time.monotonic() < het:
            if tim(await _nodes(client, serial, package), buoc["cho_chu"]):
                return True
            await asyncio.sleep(NHIP)
        log.append(f"không thấy chữ {buoc['cho_chu']!r}")
        return False
    if "dong_neu_co" in buoc:
        # Home co the chong nhieu popup (Add Widget, Check-in...): dong toi khi het, toi da DONG_TOI_DA lan.
        for _ in range(DONG_TOI_DA):
            node = tim(await _nodes(client, serial, package), buoc["dong_neu_co"])
            if not node:
                break
            await _bam(client, serial, node)
            log.append(f"đóng {node.text or node.content_desc}")
            await asyncio.sleep(NHIP)
        return True
    while time.monotonic() < het:
        _pkg, act = await device_app.focus(client, serial)
        if "ve_man" in buoc:
            # Case noi tiep co the dang o result / Feedback: BACK ve toi man goc (Home) truoc khi gen lai.
            if re.search(buoc["ve_man"], act or ""):
                return True
            if _pkg and TRINH_CHON_RE.search(_pkg):
                # Trinh chon anh nam tren task cua app: am start app khong dua app len tren no -> BACK thoat.
                await client.shell(serial, "input", "keyevent", "KEYCODE_BACK")
            elif _pkg != package:
                await device_app.launch(client, serial, package)
                await device_app.wait_foreground(client, serial, package)
            elif LUONG_FO_RE.search(act or ""):
                # Vua mo lanh (sau mua sub / kill): dang o Splash / ad / LFO / OB -> lai qua FO bang trinh lai co san.
                walk = await fo_flow.walk_to(client, serial, package, buoc["ve_man"])
                log.append(f"lái FO tới {walk.get('activity', '').rsplit('.', 1)[-1]}")
            else:
                await client.shell(serial, "input", "keyevent", "KEYCODE_BACK")
                log.append(f"BACK từ {(act or '').rsplit('.', 1)[-1]}")
            await asyncio.sleep(1.5)
            continue
        if "cho_man" in buoc:
            if re.search(buoc["cho_man"], act or ""):
                log.append(f"tới {act.rsplit('.', 1)[-1]}")
                return True
        elif "xem_ads" in buoc:
            if re.search(buoc.get("toi", "$^"), act or ""):
                log.append(f"xem ads xong → {act.rsplit('.', 1)[-1]}")
                return True
            if "AdActivity" in (act or ""):
                bam_khong_mo = 0
                log.append(await fo_flow.dong_ad_dang_che(client, serial, cho=45) or "chờ ad hết giờ")
                continue
            if bam_khong_mo >= BAM_KHONG_MO_TOI_DA:
                log.append(KHONG_FILL_THUONG)
                return False
            nodes = await _nodes(client, serial, package)
            chan = tim(nodes, buoc["dung_neu"]) if buoc.get("dung_neu") else None
            if chan:
                log.append(f"app báo '{chan.text or chan.content_desc}'")
                raise HetLuot(chan.text or chan.content_desc)
            node = tim(nodes, buoc["xem_ads"])
            if node:
                log.append(f"bấm {node.text}")
                await _bam(client, serial, node)
                bam_khong_mo += 1
                await asyncio.sleep(3.0)      # cho ad mo len, tranh bam lai nut cu
                continue
        elif not ({"tap", "tap_duoi"} & set(buoc)):
            log.append(f"bước không hiểu trong data/rating_gen.yaml: {buoc}")
            return False
        else:
            nodes = await _nodes(client, serial, package)
            node = tim(nodes, buoc["tap"]) if "tap" in buoc else tim_duoi(nodes, buoc["tap_duoi"],
                                                                         int(buoc.get("thu", 1)))
            if node:
                log.append(f"bấm {node.text or node.content_desc or node.label}")
                await _bam(client, serial, node)
                return True
        await asyncio.sleep(NHIP)
    log.append(f"hết giờ ở bước {buoc}")
    return False


class HetLuot(Exception):
    """App bao het luot gen (vd "Daily Limit Reached")."""


async def _mua_sub(client, serial: str, package: str, log: list[str]) -> bool:
    """Het luot gen free -> mua sub test bang flow co san cua rc-check (`sub_thao_tac.mua`, user chot 12/11/2026:
    moi may la License Tester, mua khong hoi). Billing chi cap nhat khi kill app -> mo lanh lai sau khi mua."""
    from . import sub_thao_tac
    from .models import RcError
    await client.shell(serial, "input", "keyevent", "KEYCODE_BACK")      # dong dialog het luot
    await asyncio.sleep(NHIP)
    # `mo_paywall` di tu Home: dang o man chon anh -> BACK ve Home truoc (walk_to khong lui ve duoc).
    await _mot_buoc(client, serial, package, {"ve_man": "MainActivity", "toi_da": 20}, log)
    try:
        kq = await sub_thao_tac.mua(client, serial, package, GOI_SUB, "approves", True)
    except RcError as exc:
        log.append(f"mua sub lỗi: {exc}")
        return False
    log.append(f"mua sub {GOI_SUB}: popup {'test' if (kq.get('popup') or {}).get('la_test') else 'không thấy'}")
    await sub_thao_tac.mo_lanh(client, serial, package)
    return True


class MuaSub(Exception):
    """Sheet xem ads co nut mua (`mua_sub_chu`): bo xem ads, mua sub qua nut nay roi gen lai."""

    def __init__(self, nut):
        super().__init__(nut.text or nut.content_desc)
        self.nut = nut


async def _mua_qua_nut(client, serial: str, package: str, nut, log: list[str]) -> bool:
    """Gen bi chan sau reward ad (AIP893 'Watch Ads (0/2)'): may khong co fill rewarded thi moi lan gen cho het 300s
    roi NEEDS_HUMAN. Bam nut mo Paywall ngay tren sheet do (user chot 16/11/2026: tab rating mua sub cho nhanh) roi mua
    bang flow co san `sub_thao_tac.mua` (dang o Paywall thi doc luon, khong can profile). Mua xong mo lanh de billing
    cap nhat; cong thuc chay lai tu dau (buoc dau ve Home, tu lai qua FO)."""
    from . import sub_thao_tac
    from .models import RcError
    log.append(f"bấm {nut.text or nut.content_desc} (mua sub thay vì xem ads)")
    await _bam(client, serial, nut)
    await asyncio.sleep(3.0)
    for goi in GOI_SUB_UU_TIEN:
        try:
            kq = await sub_thao_tac.mua(client, serial, package, goi, "approves", True)
        except RcError as exc:
            if "không có gói" in str(exc):
                continue
            log.append(f"mua sub lỗi: {exc} — gen theo đường xem ads")
            await client.shell(serial, "input", "keyevent", "KEYCODE_BACK")
            return False
        lanh = await sub_thao_tac.mo_lanh(client, serial, package)
        log.append(f"mua sub {goi}: popup {'test' if (kq.get('popup') or {}).get('la_test') else 'không thấy'}"
                   f" · premium={lanh.get('premium')}")
        return True
    log.append("Paywall không có gói weekly/monthly — gen theo đường xem ads (không mua yearly)")
    await client.shell(serial, "input", "keyevent", "KEYCODE_BACK")
    return False


async def _buoc(client, serial: str, package: str, b: dict, log: list[str]) -> bool:
    """Mot buoc cong thuc qua bo chay cua IAA (`iaa_lai.buoc`): them cac buoc cho app Compose moi man chung mot
    activity (ve_chu / cho_chu / xem_ads_chu / dong_ad / nhap / tap_neu_co...), buoc cu thi roi ve `_mot_buoc`.
    AIP893 (16/11/2026): Home / chon anh / loading / result deu la MainActivity -> cong thuc theo activity khong lai duoc."""
    from . import iaa_lai
    if b.get("bo_qua_neu"):
        # Buoc chi can khi man KHONG co chu nay (AIP893: result mo thang tu man cho -> bo duong vao History).
        if tim(await _nodes(client, serial, package), b["bo_qua_neu"]):
            return True
        b = {k: v for k, v in b.items() if k != "bo_qua_neu"}
    return await iaa_lai.buoc(client, serial, package, b, log)


async def chay_ds(client, serial: str, package: str, ds: list[dict], log: list[str], bien: dict | None = None) -> bool:
    """Chay mot danh sach buoc cong thuc bat ky (dung chung cho tab daily checkin). `bien`: thay "{ten}" trong gia tri."""
    for b in ds:
        if bien:
            b = {k: (v.format(**bien) if isinstance(v, str) and "{" in v else v) for k, v in b.items()}
        if not await _buoc(client, serial, package, b, log):
            return False
    return True


async def chay(client, serial: str, package: str, loai: str) -> dict:
    """{"co_cong_thuc", "xong", "log", "mua_sub"}: lai toi man result theo cong thuc; het luot gen thi mua sub
    roi chay lai cong thuc tu dau (mot lan)."""
    log: list[str] = []
    buoc = await cong_thuc_tren_may(client, serial, package, loai, log)
    if not buoc:
        return {"co_cong_thuc": False, "xong": False, "log": log}
    da_mua = False
    while True:
        try:
            for b in buoc:
                if "mua_sub_chu" in b and nen_mua_qua_nut(serial, package):
                    b = {**b, "mua_sub": True}        # chi luong rating mua; IAA (chay_ds / iaa_lai) khong bao gio
                if not await _buoc(client, serial, package, b, log):
                    return {"co_cong_thuc": True, "xong": False, "log": log, "mua_sub": da_mua}
            return {"co_cong_thuc": True, "xong": True, "log": log, "mua_sub": da_mua}
        except MuaSub as e:
            _DA_MUA_QUA_NUT[(serial, package)] = time.monotonic()
            da_mua = await _mua_qua_nut(client, serial, package, e.nut, log) or da_mua
        except HetLuot:
            if da_mua or not await _mua_sub(client, serial, package, log):
                return {"co_cong_thuc": True, "xong": False, "log": log, "mua_sub": da_mua}
            da_mua = True
