"""Do nen splash theo `splash_ui_config.media_url`: anh co phu kin man khong, GIF chay lap hay chay mot lan roi dung.

Truoc day cac dong "Nen anh theo media_url, phu kin man", "Nen GIF chay lap lien tuc (video_loop=true)", "Nen GIF
chay 1 lan roi dung o frame cuoi" ra NOT_VERIFIABLE "phai nhin mat" (AIP886 31/10/2026 R01-02, R02-01, R03-01).
Do duoc: tai dung file media cua case, chup man lien tuc tu luc mo app, so tung khung man voi tung khung cua file
goc o do phan giai nho (che cac view chong len nen: chu, progress, vung ad).

  - khung man khop file goc (tuong quan >= NGUONG_TQ) = dang o splash; khung inter / man trang khong khop thi bo.
  - GIF lap: man VAN DOI sau khi da qua het thoi luong GIF tinh tu khung splash dau tien thay duoc.
  - GIF mot lan: man dung yen o cuoi, khung dung yen khop khung cuoi cua GIF hon khung dau.
  - Anh phu kin: cac dai sat mep man (tren / trai / phai) deu khop anh goc - khong co vien trong / letterbox.
Chi dung Pillow (repo khong co numpy): anh nho 54x120 nen vong lap Python van nhanh.
"""

from __future__ import annotations

import asyncio
import hashlib
import io
import json
import logging
import re
import time
import urllib.request
from pathlib import Path

from . import screencap, ui_dump

log = logging.getLogger(__name__)

KICH = (54, 120)          # so o do phan giai nho: nhanh, va chiu duoc lech vai pixel do scale
THEO_DOI_GIAY = 10.0      # splash sau pm clear ~3-8s (cho fetch RC + load inter splash)
NGUONG_DOI = 2.5          # hai khung man lien tiep lech hon muc nay = nen dang chuyen dong
VUNG_PHU = 0.5            # view chiem it hon nua man = view chong len nen (chu, nut, vung ad) -> che
TOP_CHE = 0.04            # thanh trang thai
HET_SPLASH = 3            # bao nhieu khung lien tiep khong khop (sau khi da khop) thi coi la da roi splash


def cau_hinh(overrides: dict) -> dict:
    """splash_ui_config cua case ({} neu khong co / khong co media_url)."""
    try:
        cfg = json.loads((overrides or {}).get("splash_ui_config") or "{}")
    except ValueError:
        return {}
    return cfg if isinstance(cfg, dict) and cfg.get("media_url") else {}


def _tai(url: str, thu_muc: Path) -> bytes:
    thu_muc.mkdir(parents=True, exist_ok=True)
    tep = thu_muc / hashlib.sha1(url.encode()).hexdigest()
    if tep.exists():
        return tep.read_bytes()
    req = urllib.request.Request(url, headers={"User-Agent": "rcr-check (splash media)"})
    data = urllib.request.urlopen(req, timeout=30).read()
    tep.write_bytes(data)
    return data


def _khung_media(data: bytes):
    """-> ([anh RGB], [thoi luong ms]) - GIF nhieu khung, anh tinh mot khung."""
    from PIL import Image

    img = Image.open(io.BytesIO(data))
    anh, ms = [], []
    for i in range(getattr(img, "n_frames", 1)):
        img.seek(i)
        anh.append(img.convert("RGB"))
        ms.append(int(img.info.get("duration") or 0))
    return anh, ms


def _dat_len_man(src, w: int, h: int, che_do: str):
    """Ve khung media len man w x h theo kieu scale, tra anh KICH."""
    from PIL import Image

    mw, mh = src.size
    if che_do == "fit_xy":
        return src.resize(KICH, Image.BILINEAR)
    if che_do == "center_crop":
        s = max(w / mw, h / mh)
        cw, ch = w / s, h / s
        x0, y0 = (mw - cw) / 2, (mh - ch) / 2
        return src.crop((round(x0), round(y0), round(x0 + cw), round(y0 + ch))).resize(KICH, Image.BILINEAR)
    s = min(w / mw, h / mh)                        # fit_center: vien den hai ben
    nen = Image.new("RGB", (w, h))
    nw, nh = round(mw * s), round(mh * s)
    nen.paste(src.resize((nw, nh), Image.BILINEAR), ((w - nw) // 2, (h - nh) // 2))
    return nen.resize(KICH, Image.BILINEAR)


CHE_DO = ("center_crop", "fit_xy", "fit_center")


def _mat_na(hop_che: list, w: int, h: int) -> list[bool]:
    """True = pixel nen duoc so (khong bi view nao che)."""
    kw, kh = KICH
    na = [True] * (kw * kh)
    for y in range(kh):
        for x in range(kw):
            px, py = (x + 0.5) * w / kw, (y + 0.5) * h / kh
            if py < TOP_CHE * h or any(l <= px < r and t <= py < b for l, t, r, b in hop_che):
                na[y * kw + x] = False
    return na


def _lech(a, b, na: list[bool], chon=None) -> float:
    """Lech trung binh moi kenh tren cac pixel duoc so (`chon` loc them theo chi so pixel)."""
    tong = dem = 0
    du = lambda im: getattr(im, "get_flattened_data", im.getdata)()  # noqa: E731
    for i, (p, q) in enumerate(zip(du(a), du(b))):
        if na[i] and (chon is None or chon(i)):
            tong += abs(p[0] - q[0]) + abs(p[1] - q[1]) + abs(p[2] - q[2])
            dem += 3
    return tong / dem if dem else 999.0


def _xam(img, na: list[bool], chon=None) -> list[float]:
    du = getattr(img, "get_flattened_data", img.getdata)()
    return [0.299 * p[0] + 0.587 * p[1] + 0.114 * p[2] for i, p in enumerate(du) if na[i] and (chon is None or chon(i))]


def _chuan(x: list[float]) -> list[float]:
    """Tru trung binh, chia do lech: tuong quan Pearson cua hai vector chuan = tich vo huong."""
    n = len(x)
    if n < 20:
        return [0.0] * n
    m = sum(x) / n
    d = [v - m for v in x]
    s = sum(v * v for v in d) ** 0.5
    return [v / s for v in d] if s > 0 else [0.0] * n


def _tuong_quan(a, b, na: list[bool], chon=None) -> float:
    """He so tuong quan Pearson do xam tren vung duoc so: chiu duoc lop mo / gradient app phu len anh nen
    (AIP886 2.7.0 phu trang dan xuong duoi - lech tuyet doi 22-90/255 du dung anh), con man khac thi ~0."""
    x, y = _xam(a, na, chon), _xam(b, na, chon)
    n = len(x)
    if n < 20:
        return 0.0
    mx, my = sum(x) / n, sum(y) / n
    sxy = sum((p - mx) * (q - my) for p, q in zip(x, y))
    sxx = sum((p - mx) ** 2 for p in x)
    syy = sum((q - my) ** 2 for q in y)
    return sxy / (sxx * syy) ** 0.5 if sxx > 0 and syy > 0 else 0.0


def hop_che_tu_dump(xml: str, package: str, w: int, h: int) -> tuple[list, bool | None, bool]:
    """(cac hop view chong len nen, co ImageView nen phu kin man khong, dump co phai man splash khong)."""
    try:
        nodes = ui_dump.app_nodes(ui_dump.parse_dump(xml), package)
    except Exception:  # noqa: BLE001 - dump hong thi che theo mac dinh
        return [], None, False
    hop, nen_full = [], None
    la_splash = any(n.resource_id.lower().startswith("spl") for n in nodes)
    for n in nodes:
        b = n.bounds
        if not n.visible or b.empty:
            continue
        dt = (b.right - b.left) * (b.bottom - b.top) / (w * h)
        if dt < VUNG_PHU:
            hop.append((b.left, b.top, b.right, b.bottom))
        elif n.cls.endswith("ImageView") and dt >= 0.95:
            nen_full = True
    return hop, nen_full, la_splash


async def chup(client, serial: str, giay: float = THEO_DOI_GIAY) -> dict:
    """Chup man lien tuc tu luc vua mo app (anh nho + moc giay + PNG goc).

    KHONG dump song song: buoc lai cung dump vao chung mot file tren may, hai lenh de nhau -> "Khong doc duoc
    dump UI" (AIP886 31/10/2026). Cay node cua splash lay tu dump buoc lai (`dump_splash`)."""
    from PIL import Image

    t0, khung, size, goc = time.monotonic(), [], None, []
    while time.monotonic() - t0 < giay:
        png = await screencap.raw(client, serial)
        if not png:
            continue
        try:
            img = Image.open(io.BytesIO(png)).convert("RGB")
        except Exception:  # noqa: BLE001
            continue
        size = img.size
        khung.append((round(time.monotonic() - t0, 2), img.resize(KICH, Image.BILINEAR)))
        goc.append(png)
    # PNG goc giu lai de do mau chu tren chinh cac khung splash (`khung_do_mau`).
    return {"khung": khung, "size": size, "png": goc}


def dump_splash(drive: dict) -> str:
    """Dump man splash (co view `spl*`) trong cac buoc da lai, "" neu khong co."""
    for st in (drive or {}).get("steps") or []:
        xml = st.get("dump") or ""
        if "plash" in (st.get("activity") or "") and 'resource-id="' in xml and ":id/spl" in xml:
            return xml
    return ""


NGUONG_TQ = 0.7           # tuong quan toi thieu de coi khung man la file media nay
MEP_TQ = 0.5              # dai sat mep (tren / trai / phai) toi thieu phai tuong quan nhu vay voi anh goc
DUOI_SO = 0.45            # chi so phan tren man: duoi nua man app phu lop mo + chu + progress + vung ad


def phan_tich(cfg: dict, chup_duoc: dict, package: str, thu_muc: Path) -> dict:
    """So khung man voi file media -> ket qua gon (luu duoc vao file luot)."""
    loai = str(cfg.get("type") or "").lower()
    ra = {"loai": loai, "media_url": cfg["media_url"], "video_loop": cfg.get("video_loop")}
    khung, size = chup_duoc.get("khung") or [], chup_duoc.get("size")
    if not khung or not size:
        return ra | {"loi": "không chụp được khung màn nào"}
    try:
        media, ms = _khung_media(_tai(cfg["media_url"], thu_muc))
    except Exception as exc:  # noqa: BLE001
        return ra | {"loi": f"không tải được media_url: {exc}"}
    w, h = size
    hop, nen_full, la_splash = hop_che_tu_dump(chup_duoc.get("xml") or "", package, w, h)
    # Dump chay song song co the roi vao luc inter da len: khi do khong biet chu nam dau -> chi so dai tren cung.
    duoi = DUOI_SO if la_splash else 0.25
    na = _mat_na((hop if la_splash else []) + [(0, int(h * duoi), w, h)], w, h)
    mau = {cd: [_dat_len_man(m, w, h, cd) for m in media] for cd in CHE_DO}
    # Vector xam da chuan hoa tinh SAN mot lan: tuong quan = tich vo huong. Truoc day tinh lai tung cap
    # (300 khung raw x 3 kieu x 24 khung GIF) mat vai phut moi case, may dung im (AIP886 31/10/2026).
    vec = {cd: [_chuan(_xam(m, na)) for m in mau[cd]] for cd in CHE_DO}
    vk = [_chuan(_xam(img, na)) for _, img in khung]

    def tot_nhat(v, cd):
        tq = [sum(p * q for p, q in zip(v, m)) for m in vec[cd]]
        i = max(range(len(tq)), key=tq.__getitem__)
        return i, tq[i], tq
    mau_thu = vk[::max(1, len(vk) // 12)]
    che_do = max(CHE_DO, key=lambda cd: max(tot_nhat(v, cd)[1] for v in mau_thu))
    dong, da_khop, ngoai, tot = [], False, 0, 0.0
    for k, (t, img) in enumerate(khung):
        i, tq, moi = tot_nhat(vk[k], che_do)
        tot = max(tot, tq)
        if tq < NGUONG_TQ:
            ngoai += da_khop
            if da_khop and ngoai >= HET_SPLASH:
                break
            continue
        da_khop, ngoai = True, 0
        dong.append({"t": t, "chup": k, "khung": i, "tq": round(tq, 3), "tq_cuoi": round(moi[-1], 3),
                     "tq_dau": round(moi[0], 3), "img": img})
    ra |= {"che_do": che_do, "so_khung_media": len(media), "thoi_luong_ms": sum(ms), "so_khung_chup": len(khung),
           "nen_full_node": nen_full, "khung_chup_t": [t for t, _ in khung]}
    if not dong:
        return ra | {"loi": f"không khung màn nào khớp media ({len(khung)} khung chụp, tương quan tốt nhất "
                            f"{tot:.2f} < {NGUONG_TQ})"}
    # Nen co doi giua hai khung splash lien tiep khong (chi tren vung nen).
    for a, b in zip(dong, dong[1:]):
        b["doi"] = round(_lech(a["img"], b["img"], na), 1)
    if che_do != "fit_center":
        kw, kh = KICH
        dai = {"trên": lambda i: i // kw < kh * 0.15, "trái": lambda i: i % kw < kw * 0.12,
               "phải": lambda i: i % kw >= kw * 0.88}
        tot_dong = max(dong, key=lambda d: d["tq"])
        ra["mep"] = {k: round(_tuong_quan(tot_dong["img"], mau[che_do][tot_dong["khung"]], na, f), 3)
                     for k, f in dai.items()}
    for d in dong:
        d.pop("img")
    return ra | {"splash": dong}


SO_KHUNG_DO_MAU = 4


def khung_do_mau(chup_duoc: dict, sm: dict) -> list[bytes]:
    """PNG goc cua vai khung DA KHOP splash (rai deu) - do mau chu tren do thay vi mot anh chup luc inter co the da
    de len (AIP886 R01-02 31/10/2026: anh buoc "Quan sat Splash" chup tre, 0 pixel mau chu -> FAIL gia)."""
    png = chup_duoc.get("png") or []
    dong = sm.get("splash") or []
    if not dong or not png:
        return []
    buoc = max(1, len(dong) // SO_KHUNG_DO_MAU)
    return [png[d["chup"]] for d in dong[::buoc][:SO_KHUNG_DO_MAU] if d["chup"] < len(png)]


DONG_ADS_RE = re.compile(r"\bads?\b|qu[ảa]ng\s*c[áa]o|\binter|native|banner|request|impression|\bshow", re.I)
RAW_W, RAW_H = 108, 240   # khung raw nho: ~77 khung/giay qua USB (do that Pixel 6)
QUAY_GIAY = 13.0
LAY_MOI = 3               # lay 1/3 so khung: ~25 khung/giay, du bat tung khung GIF 100ms


async def quay_lan_mo_lai(client, serial: str, package: str, giay: float = QUAY_GIAY) -> dict:
    """Tat app -> bat `screenrecord --output-format=raw-frames` -> mo lai app (config da cache) -> khung + moc giay.

    Lan mo dau sau pm clear GIF chi hien ~0,4-1,5s roi inter splash de len (cho fetch RC ~4s), khong bao gio het
    mot vong 2,4s; `screencap` chi ~1 khung/giay. Lan mo lai config co san: GIF hien tu giay ~2,5 toi ~7, du thay
    het vong va doan sau (AIP886 R02-01 / R03-01 31/10/2026)."""
    from PIL import Image

    await client.shell(serial, "am", "force-stop", package)
    proc = await asyncio.create_subprocess_exec(
        client.adb, "-s", serial, "exec-out", "screenrecord", "--output-format=raw-frames",
        "--size", f"{RAW_W}x{RAW_H}", "--time-limit", str(int(giay) + 2), "-",
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
    n, khung, t0, dem = RAW_W * RAW_H * 3, [], time.monotonic(), 0

    async def doc():
        nonlocal dem
        while True:
            try:
                b = await proc.stdout.readexactly(n)
            except (asyncio.IncompleteReadError, ConnectionError):
                return
            dem += 1
            if dem % LAY_MOI == 0:
                khung.append((round(time.monotonic() - t0, 2),
                              Image.frombytes("RGB", (RAW_W, RAW_H), b).resize(KICH, Image.BILINEAR)))

    task = asyncio.create_task(doc())
    try:
        await asyncio.sleep(0.5)
        await client.shell(serial, "monkey", "-p", package, "-c", "android.intent.category.LAUNCHER", "1")
        await asyncio.sleep(giay)
    finally:
        task.cancel()
        try:
            proc.kill()
        except ProcessLookupError:
            pass
        await client.shell(serial, "pkill", "-f", "screenrecord")
    return {"khung": khung, "size": (RAW_W * 10, RAW_H * 10), "png": [], "lan_mo_lai": True}


# ID inter splash: `id_102*` hoac (AIP886) `splash_inter_high_n_id`, `splash_inter_n_id`...
ID_INTER_SPLASH_RE = re.compile(r"^(?:id_102\w*|splash_inter\w*_id)$")
CHO_LAN_DAU = 25.0        # lan mo dau sau pm clear: fetch RC + qua splash


def id_inter_splash_trong(configs: dict) -> dict[str, str]:
    """ID inter splash -> slot khong ton tai (inter khong bao gio fill).

    Do that AIP886 31/10/2026: lan mo lai, inter splash tai xong o giay 4-5 -> GIF moi toi khung 11-17/24, khong
    thay het vong (lan do tay may man inter tai cham thi thay). Inter khong fill thi lan mo lai splash giu toi
    timeout (~10s): GIF chay het vong va doan sau ro rang (R03-01: 1->23 roi dung 23 suot 7s)."""
    from .precond_guards import SLOT_KHONG_TON_TAI

    return {k: str(v).rsplit("/", 1)[0] + "/" + SLOT_KHONG_TON_TAI for k, v in (configs or {}).items()
            if ID_INTER_SPLASH_RE.match(k) and str(v).startswith("ca-app-pub")}
