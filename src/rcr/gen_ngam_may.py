"""Nhin may cho tab TC "gen ngam" (`rcr-gen-ngam`): cay node app, thong bao he thong, log GenerationWorker, History,
MediaStore. Chi doc - thao tac (bam, tao, xoa...) o `gen_ngam_tao`.

Chu tren man theo app: `data/gen_ngam_cong_thuc.yaml` (CT). Moi moc gio la gio MAY (`$EPOCHREALTIME`), khong phai gio
may tinh (lech ~0,8s) - popup giay 12 / ve Home giay 15 do bang hieu hai moc may.
"""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from pathlib import Path

from . import device_app, ui_dump

DATA = Path(__file__).parent / "data" / "gen_ngam_cong_thuc.yaml"
NHIP = 0.4
# `logcat -v epoch`: "1794589829.448  3792  3792 D WM-WorkerWrapper: Starting work for ...GenerationWorker"
WORKER_RE = re.compile(r"^\s*(\d{9,}\.\d+).*WM-WorkerWrapper: (?:(Starting work)|Worker result (\w+)).*?GenerationWorker")
START_RE = re.compile(r"^\s*(\d{9,}\.\d+).*ActivityTaskManager: START u0 .*?cmp=([\w.]+)/([\w.$]+)")
AD_RE = re.compile(r"\.AdActivity|ads\.AdActivity")
# Moi lan nhin deu ghi co thay toast "tao xong" khong (gio may, co/khong): toast ~8s hien de len MOI man (Home, man chon
# style...), nen dem toast cua nhieu luot chay chong lay tu day thay vi phai dung yen o Home (luot 16/11 R06-02 hut).
MAU_TOAST: list[str] = []
NHAT_KY_TOAST: list[tuple[float, bool]] = []
# App Compose (moi man chung mot activity, AIP893 18/11/2026): CLI nap `man_theo_chu` cua cong thuc vao day ->
# `nhin` dat ten man AO (vd "ProcessingScreen") theo chu tren man, de cac regex man_cho / man_ket_qua / man_lich_su
# van dung nhu app nhieu activity. Rong = app nhieu activity, giu ten activity that.
MAN_THEO_CHU: dict[str, str] = {}
# Nut khong chu / khong desc (uiautomator NAF): CLI nap `nut_ao` cua cong thuc vao day -> `nhin` them node ao co
# content-desc = `desc` tai `khung` [l, t, r, b] khi man co chu `khi_chu`. AIP919 (21/11/2026): icon History o goc tren
# phai Home la View NAF khong chu, cac buoc mo History tim theo desc "History".
NUT_AO: list[dict] = []
# Regex chu nut thanh tab duoi (tab_home|tab_anh|tab_video): man Compose khong khop man nao ma cung khong co thanh tab
# (Text to Image, Image to Image...) -> "ManKhac", de ve_main BACK thay vi coi la Home.
THANH_TAB: list[str] = []
TRINH_CHON_RE = re.compile(r"photopicker|documentsui|providers\.media|gallery", re.I)
# `logcat -v epoch` system_server: "WindowManager: Changing focus from Window{c2fc6fe u0 a/a.X} to Window{43eebab u0
# b/b.Y}" va "WindowManager: Remove Window{38933a0 u0 b/b.Y}: ..." (Samsung A13 Android 14 in muc V).
FOCUS_RE = re.compile(r"^\s*(\d{9,}\.\d+).*WindowManager: Changing focus from Window\{(\w+) u0 ([\w.]+)[^}]*\}"
                      r" to Window\{(\w+) u0 ([\w.]+)")
REMOVE_RE = re.compile(r"^\s*(\d{9,}\.\d+).*WindowManager: Remove Window\{(\w+) u0 ([\w.]+)")


def cong_thuc(package: str) -> dict | None:
    """Khuon chung + muc rieng cua app (de len). App chua co muc rieng -> khuon chung, co co `_khuon_chung`."""
    import yaml
    data = yaml.safe_load(DATA.read_text(encoding="utf-8")) or {}
    chung, rieng = data.get("khuon_chung") or {}, data.get(package)
    if rieng is None:
        return {**chung, "_khuon_chung": True} if chung else None
    return {**chung, **rieng}


@dataclass
class Man:
    """Mot lan nhin: gio may, activity foreground, node cua app."""
    t: float
    pkg: str
    act: str
    nodes: list

    def chu(self) -> list[str]:
        return [s for n in self.nodes for s in (n.text, n.content_desc) if s]

    def tim(self, mau: str):
        return next((n for n in self.nodes if not n.bounds.empty
                     and any(re.search(mau, s or "", re.I) for s in (n.text, n.content_desc))), None)

    def tat_ca(self, mau: str) -> list:
        return [n for n in self.nodes if not n.bounds.empty
                and any(re.search(mau, s or "", re.I) for s in (n.text, n.content_desc))]

    def o(self, mau_act: str) -> bool:
        return bool(re.search(mau_act, self.act or ""))


def ten_man_ao(m: Man, package: str) -> str:
    """App Compose: ten man theo chu (CHI text, khong desc - nut History o Home chi co desc 'History', tieu de man
    History la text). Trinh chon anh he thong -> 'PhotoPicker'. App nhieu activity (MAN_THEO_CHU rong): giu nguyen."""
    if not MAN_THEO_CHU:
        return m.act
    if m.pkg and m.pkg != package and TRINH_CHON_RE.search(m.pkg):
        return "PhotoPicker"
    if m.pkg != package:
        return m.act
    chu = [n.text for n in m.nodes if n.text and not n.bounds.empty]
    ten = next((ten for ten, mau in MAN_THEO_CHU.items() if any(re.search(mau, s) for s in chu)), "")
    if ten:
        return ten
    if THANH_TAB and m.nodes and not any(re.search(THANH_TAB[0], n.text) and n.bounds.top > 1500
                                         for n in m.nodes if n.text and not n.bounds.empty):
        return "ManKhac"
    return m.act


async def cua_so(client, serial: str) -> tuple[str, str]:
    """(ma cua so, package) dang giu focus - `dumpsys window` ~0,05s. Popup dem nguoc la cua so dialog rieng cung
    activity: ma cua so khac cua so chinh."""
    out, _, _ = await client.shell(serial, "dumpsys", "window", "|", "grep", "mCurrentFocus")
    m = re.search(r"Window\{(\w+) u0 ([\w.]+)", out or "")
    return (m.group(1), m.group(2)) if m else ("", "")


def moc_cua_so(dong: list[str], package: str, tu: float, vao_san: float = 0.0) -> dict:
    """App Compose - moc tu log WindowManager sau `tu`: vao (focus tu trinh chon anh sang cua so app), popup (focus
    sang cua so app KHAC cua so chinh = dialog dem nguoc), ra (dialog bi Remove = ve Home). 0 = khong co."""
    vao = popup = ra = 0.0
    chinh = dlg = ""
    if vao_san:
        # Khong qua trinh chon anh (T2I): vao da biet; cua so chinh = cua so app dang focus truoc dialog.
        vao, chinh = vao_san, "?"
    for d in dong:
        f = FOCUS_RE.search(d)
        if f and float(f.group(1)) >= tu:
            t, tu_pkg, toi_ma, toi_pkg = float(f.group(1)), f.group(3), f.group(4), f.group(5)
            if not vao and toi_pkg == package and TRINH_CHON_RE.search(tu_pkg):
                vao, chinh = t, toi_ma
            elif vao and not popup and toi_pkg == package and toi_ma != chinh and \
                    (chinh != "?" or (tu_pkg == package and f.group(2) != toi_ma)):
                popup, dlg = t, toi_ma
            continue
        r = REMOVE_RE.search(d)
        if r and dlg and not ra and r.group(2) == dlg:
            ra = float(r.group(1))
    return {"vao": vao, "popup": popup, "ra": ra}


async def gio(client, serial: str) -> float:
    out, _, _ = await client.shell(serial, "echo", "$EPOCHREALTIME")
    try:
        return float((out or "0").strip())
    except ValueError:
        return 0.0


async def nhin(client, serial: str, package: str) -> Man:
    from .adb_parsers import AdbError
    for lan in range(5):
        t = await gio(client, serial)
        try:
            xml = await ui_dump.dump(client, serial)
            break
        except AdbError:
            # uiautomator thinh thoang khong ghi file dump ("No such file", Pixel 6) hoac khong cho duoc man dung yen
            # ("could not get idle state", Pixel 4 luc anh dong) -> nhin lai cham dan, dung chet ca nhom.
            if lan == 4:
                raise
            await asyncio.sleep(0.5 + lan)
    pkg, act = await device_app.focus(client, serial)
    m = Man(t, pkg, (act or "").rsplit(".", 1)[-1], ui_dump.app_nodes(ui_dump.parse_dump(xml), package))
    them_nut_ao(m, package)
    m.act = ten_man_ao(m, package)
    if MAU_TOAST:
        NHAT_KY_TOAST.append((t, m.tim(MAU_TOAST[0]) is not None))
    return m


def them_nut_ao(m: Man, package: str) -> None:
    """Them node ao cho nut NAF da khai trong `NUT_AO` (chi khi man dang co chu `khi_chu` va chua co node desc do)."""
    for nut in NUT_AO:
        if m.tim(f"^{re.escape(nut['desc'])}$") is not None:
            continue
        if not any(re.search(nut["khi_chu"], n.text or "") for n in m.nodes if not n.bounds.empty):
            continue
        l, t, r, b = (int(v) for v in nut["khung"])
        m.nodes.append(ui_dump.DeviceNode(f"ao.{nut['desc']}", "", "android.view.View", "", nut["desc"],
                                          ui_dump.Bounds(l, t, r, b), True, True, True, package, None, 0))


def cum_toast(tu: float) -> list[tuple[float, float, float, float]]:
    """Cac lan toast hien sau moc `tu`: [(lan cuoi KHONG thay truoc do, lan dau thay, lan cuoi thay, lan dau KHONG
    thay sau do (0 = chua))]. Toast dung trong [cuoi - dau, mat - truoc] giay (nhin ~2,1s/lan)."""
    ra: list[list[float]] = []
    truoc = 0.0
    for t, co in sorted(x for x in NHAT_KY_TOAST if x[0] >= tu):
        if co and (not ra or ra[-1][3]):
            ra.append([truoc, t, t, 0.0])
        elif co:
            ra[-1][2] = t
        else:
            if ra and not ra[-1][3]:
                ra[-1][3] = t
            truoc = t
    return [tuple(x) for x in ra]


async def cho(client, serial: str, package: str, dk, giay: float) -> Man | None:
    """Nhin lap toi khi `dk(man)` dung; het `giay` -> None."""
    het = await gio(client, serial) + giay
    while True:
        m = await nhin(client, serial, package)
        if dk(m):
            return m
        if m.t >= het:
            return None
        await asyncio.sleep(NHIP)


def badge(man: Man, ct: dict) -> int:
    """So tren nut History (node chi co so, nam sat nut). Khong co -> 0."""
    ls = man.tim(ct["lich_su"])
    if ls is None:
        return 0
    for n in man.nodes:
        if re.fullmatch(r"\d{1,2}", n.text or "") and abs(n.bounds.top - ls.bounds.top) < 60 \
                and ls.bounds.left - 20 <= n.bounds.left <= ls.bounds.right + 30:
            return int(n.text)
    return 0


def o_lich_su(man: Man, ct: dict) -> list[dict]:
    """O History tu tren xuong (trai -> phai): {ten, dang_tao, moi, loi, video, xy}. O = node desc co ten style, khong
    text; nhan Generating / New / Failed nam trong khung o."""
    o = [n for n in man.nodes if n.content_desc and not n.text and n.bounds.bottom - n.bounds.top > 200
         and not re.search(r"^(?:Back|History|Settings)$", n.content_desc)]
    o.sort(key=lambda n: (n.bounds.top, n.bounds.left))
    if not o:
        return _o_lich_su_theo_nhan(man, ct)
    ra = []
    for n in o:
        trong = [x for x in man.nodes if x is not n and n.bounds.left <= x.bounds.left < n.bounds.right
                 and n.bounds.top <= x.bounds.top < n.bounds.bottom]
        chu = " | ".join(s for x in trong for s in (x.text, x.content_desc) if s)
        ra.append({"ten": n.content_desc, "dang_tao": bool(re.search(ct["o_dang_tao"], chu, re.M) or
                                                          re.search(r"(?:^|\| )Generating", chu)),
                   "moi": bool(re.search(r"(?:^|\| )New(?: |$)", chu)), "loi": bool(re.search(r"Failed", chu)),
                   "video": bool(re.search(r"\bPlay\b", chu)), "chu": chu, "xy": n.bounds.center})
    return ra


def _o_lich_su_theo_nhan(man: Man, ct: dict) -> list[dict]:
    """App Compose AIP893 (18/11/2026): o History khong co desc; moi o = anh nho + nhan 'Image'/'Video' o goc duoi
    trai anh + tieu de ('Untitled creation') + gio duoi anh; o dang tao co chu 'Generating…' tren anh. Ten = tieu
    de; bam vao giua anh (tren nhan)."""
    nhan = sorted((n for n in man.nodes if re.fullmatch(r"Image|Video", n.text or "") and not n.bounds.empty
                   and n.bounds.top > 250), key=lambda n: (n.bounds.top, n.bounds.left))
    ra = []
    for n in nhan:
        rong = 400
        # Nhan "Video" rong hon "Image" nen lech phai ~75px so voi tieu de (do 18/11/2026) -> khung trai rong 110px.
        trong = [x for x in man.nodes if x is not n and x.text and n.bounds.left - 110 <= x.bounds.left < n.bounds.left + rong
                 and n.bounds.top - 620 <= x.bounds.top <= n.bounds.bottom + 200]
        tieu_de = next((x.text for x in sorted(trong, key=lambda x: x.bounds.top)
                        if x.bounds.top > n.bounds.bottom and not re.search(r"ago$|^just now$", x.text, re.I)), "")
        chu = " | ".join(x.text for x in sorted(trong, key=lambda x: x.bounds.top))
        ra.append({"ten": tieu_de, "dang_tao": bool(re.search(ct["o_dang_tao"], chu, re.M) or re.search(r"Generating", chu)),
                   "moi": bool(re.search(r"(?:^|\| )New(?: |$)", chu)), "loi": bool(re.search(r"Failed", chu)),
                   "video": n.text == "Video", "chu": f"{n.text} | {chu}",
                   "xy": (n.bounds.left + 150, max(n.bounds.top - 250, 300))})
    return ra


# ---- thong bao he thong ----

_REC_RE = re.compile(r"NotificationRecord\(0x[0-9a-f]+: pkg=(\S+) .*?id=(\d+)")


async def push(client, serial: str, package: str) -> list[dict]:
    """Thong bao dang co cua app: [{id, title, text, ongoing}] (dumpsys notification --noredact)."""
    out, _, _ = await client.shell(serial, "dumpsys", "notification", "--noredact")
    ra, cur = [], None
    for dong in (out or "").splitlines():
        m = _REC_RE.search(dong)
        if m:
            cur = {"id": m.group(2), "title": "", "text": "", "ongoing": "ONGOING_EVENT" in dong} \
                if m.group(1) == package else None
            if cur is not None:
                ra.append(cur)
            continue
        if cur is None:
            continue
        t = re.search(r"android\.(title|text)=\w+ \((.*)\)\s*$", dong)
        if t and not cur[t.group(1)]:
            cur[t.group(1)] = t.group(2)
    return ra


# ---- log ----

async def log(client, serial: str, tu: float) -> list[str]:
    out, _, _ = await client.shell(serial, "logcat", "-d", "-v", "epoch", "-T", f"{tu:.3f}", timeout=60)
    return (out or "").splitlines()


def worker(dong: list[str]) -> list[tuple[float, str]]:
    """[(gio, "bat_dau" | "SUCCESS" | "FAILURE" ...)] cua GenerationWorker."""
    ra = []
    for d in dong:
        m = WORKER_RE.search(d)
        if m:
            ra.append((float(m.group(1)), "bat_dau" if m.group(2) else m.group(3)))
    return ra


def mo_man(dong: list[str], package: str) -> list[tuple[float, str]]:
    """[(gio, Activity)] cua app (ca AdActivity) theo log START."""
    return [(float(m.group(1)), m.group(3).rsplit(".", 1)[-1]) for m in map(START_RE.search, dong)
            if m and m.group(2) == package]


def co_ad(dong: list[str], package: str) -> bool:
    return any(AD_RE.search(a) for _, a in mo_man(dong, package))


async def tep_moi(client, serial: str, thu_muc: str, tu_giay: int) -> list[dict]:
    """File MediaStore moi trong `thu_muc` tu `tu_giay`: [{ten, mime, bang}] - bang "images"/"video"."""
    ra = []
    for bang in ("images", "video"):
        out, _, _ = await client.shell(
            serial, "content", "query", "--uri", f"content://media/external/{bang}/media", "--projection",
            "_display_name:mime_type:relative_path:date_added", "--where", f"\"date_added>={tu_giay}\"")
        for d in (out or "").splitlines():
            if thu_muc in d:
                ten = re.search(r"_display_name=([^,]+)", d)
                mime = re.search(r"mime_type=([^,]+)", d)
                rel = re.search(r"relative_path=([^,]+)", d)
                tep = {"ten": ten.group(1) if ten else "", "mime": mime.group(1) if mime else "", "bang": bang}
                if ten and rel:
                    tep["noi_dung"] = await loai_noi_dung(client, serial, f"/sdcard/{rel.group(1)}{ten.group(1)}")
                ra.append(tep)
    return ra


async def loai_noi_dung(client, serial: str, duong_dan: str) -> str:
    """Loai file theo byte dau (khong theo duoi / mime MediaStore): 'mp4' / 'jpeg' / 'png' / ''.
    AIP892 16/11/2026: video luu ra BeautyGenie_x.jpg, MediaStore ghi image/jpeg nhung noi dung la MP4 -> Thu vien
    hien anh tinh, bam vao khong phat duoc."""
    out, _, _ = await client.shell(serial, "head", "-c", "12", f"'{duong_dan}'", "|", "od", "-An", "-tx1")
    b = "".join((out or "").split())
    if b[8:16] == "66747970":          # "ftyp" o byte 4-7: ISO Media (MP4 / MOV)
        return "mp4"
    if b.startswith("ffd8ff"):
        return "jpeg"
    if b.startswith("89504e47"):
        return "png"
    return ""


async def toast_he_thong(client, serial: str, package: str) -> bool:
    """Toast he thong (Toast.makeText - KHONG nam trong uiautomator dump) cua app dang hien: Android 11+ giu trong
    `dumpsys notification` muc "Toast Queue" (ToastRecord ... pkg=<package>)."""
    out, _, _ = await client.shell(serial, "dumpsys", "notification")
    phan = (out or "").split("Toast Queue", 1)
    return len(phan) == 2 and package in phan[1].split("\n\n", 1)[0]
