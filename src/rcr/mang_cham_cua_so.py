"""Giu / tra mang cua app THEO MAN dang hien, de ad cua man dich ve MUON (sau khi user roi man do).

VI SAO: tre co dinh khong du - ad duoc preload tu man truoc (202 tu luc inter splash hien, 303 tu OB1) nen den
man dich ad da nam san (AIP872 1.9.0: S03-01 202 show o LFO2, S04-01 303 load xong o OB1, show ngay khi vao OB3).

Cach o day: theo doi logcat truc tiep (event `<man>_view` cua app + ActivityTaskManager mo AdActivity), den dung
luc ad cua man dich sap duoc preload thi chan mang app (`mang_cham.chan` - tuong lua drop goi tin, request treo),
roi man dich (event `_view` cua man sau no) thi tra mang: request dang treo chay tiep, ad ve muon dung kich ban TC.
Ket qua chi duoc nhan khi log xac nhan (`mang_cham.kiem_dieu_kien`).
"""
from __future__ import annotations

import asyncio
import re
import time

from . import fa_log, mang_cham
from .app_sandbox import guard

# Thu tu man luong FO. `spl_inter` = luc inter splash hien (AdActivity mo).
THU_TU = ("splash", "spl_inter", "lfo1", "lfo2", "ob1", "ob2", "ob3", "ob4", "ob5")
# Ad cua man dich (tier high) duoc load TAI man nao - tab "Tong hop SDK" (sdk-check/references/
# logic-preload-load-ads-fo-co-ban.md): 202_high/high1 tu inter splash, 301 tu LFO1, 302/303 tu OB1...
LOAD_TAI = {"lfo1": "splash", "lfo2": "spl_inter", "ob1": "lfo1", "ob2": "ob1", "ob3": "ob1",
            "ob4": "ob3", "ob5": "ob4"}
# GMA cat request sau 60s; tra mang xong ad con mat ~15s moi ve (do Pixel 6: mo 12:37 -> load 12:51).
# Giu qua muc nay thi tu tra, ghi lai de bao.
GIU_TOI_DA_S = 45.0
# Vua tra mang: tool dung o man hung toi da chung nay cho ad hien - khong thi tool vuot qua OB1 truoc khi
# 202 kip ve, ad hien o OB2 (AIP872 09/11/2026: S03-01).
CHO_AD_HUNG_S = 30.0       # do: tra mang 49:22 -> 303 load 49:40 (18s, TCP lui dan khi bi drop)
_DANG_CHAY = None     # CuaSo dang chay (mot case mot luc; fo_flow.do_step hoi qua `cho_ad_ve_muon`)

_VIEW = re.compile(r"^(splash|lfo\d|ob\d)_view")
_AD_ACT = re.compile(r"START u0 .*cmp=[\w.]+/[\w.$]*(?:AdActivity|AppLovinFullscreen|Interstitial)", re.I)


def man_bat_dau(man_dich: str) -> str:
    """Man ma tu do phai chan mang: truoc luc ad cua man dich duoc load mot nhip (FA log tre vai tram ms,
    chan dung luc vao man load thi request co the da xong). Load tai inter splash thi chan ngay luc do -
    chan som hon nua la giu luon chinh inter splash."""
    load = LOAD_TAI.get(man_dich, "")
    if not load:
        return ""
    if load in ("splash", "spl_inter"):
        return load
    return THU_TU[THU_TU.index(load) - 1]


def ke_hoach(man_dich: str, ids=()) -> dict | None:
    """`ids`: ID day du cua ad man dich. Co ID thi chan NGAY khi app gui request do (event `track_ad_request`):
    SDK thay mat mang thi BO request (khong gui) - chan theo man truoc luc preload la ad dich khong bao gio
    duoc request (do Pixel 6 09/11/2026: S04-01 chan tu LFO2, 303 khong co request nao). Tuong lua chi giu
    duoc request da gui di."""
    bat_dau = man_bat_dau(man_dich)
    if not bat_dau or man_dich not in THU_TU:
        return None
    return {"man": man_dich, "bat_dau": bat_dau, "ids": sorted(set(ids or ()))}


def id_cua_man(ung_vien: dict, man: str) -> list[str]:
    """ID day du cua moi key `id_<ma>_<man>_*` (case_evidence.ung_vien_id: RC + checklist ID ads)."""
    from .assert_ad_screen import _man_cua_key
    return sorted({i for k, v in (ung_vien or {}).items()
                   if (m := _man_cua_key(k)) and m[1] == man for i in (v if isinstance(v, (list, tuple)) else (v,))})


def mo_ta(kh: dict) -> str:
    man = kh["man"].upper()
    bd = (f"lúc app gửi request ad {man}" if kh.get("ids")
          else "lúc inter splash hiện" if kh["bat_dau"] == "spl_inter" else kh["bat_dau"].upper())
    return (f"chặn mạng app bằng tường lửa Android từ {bd} tới khi rời {man} (request đang chạy treo lại, không "
            f"fail), rời {man} thì trả mạng để ad về muộn")


class CuaSo:
    """Mot tien trinh `adb logcat` theo doi man, chan / tra mang app. Moi lan app mo lai tu Splash (event
    splash_view) la mot luot moi -> ve trang thai dau (case chay lai nhieu lan trong mot lan bat)."""

    def __init__(self, client, serial: str, package: str, kh: dict) -> None:
        self.client, self.serial, self.package, self.kh = client, serial, package, kh
        self.che_do = "tha"
        self.dong_luc: float | None = None
        self.da_mo = False
        self.vua_mo = 0.0               # luc tra mang (monotonic), 0 = chua tra
        self.da_cho = False
        self.thay_show = False          # ad dich da ve sau luc tra mang (ad_load dung ID; khong biet ID: ad_show)
        self.man_cuoi = ""              # man moi nhat da thay trong luot nay
        self.lich: list[str] = []
        self._hang: asyncio.Queue | None = None
        self._proc = None
        self._tasks: list = []

    def _ghi(self, che_do: str, ly_do: str = "") -> None:
        if che_do != self.che_do:
            self.che_do = che_do
            if self._hang is not None:
                self._hang.put_nowait(che_do)
        if ly_do:
            self.lich.append(f"{time.strftime('%H:%M:%S')} {'chặn' if che_do == 'giu' else 'trả'} mạng: {ly_do}")

    def _dong(self, ly_do: str) -> None:
        if self.dong_luc is None:
            self.dong_luc = time.monotonic()
            self._ghi("giu", ly_do)

    def _mo(self, ly_do: str) -> None:
        if self.dong_luc is not None:
            giu = time.monotonic() - self.dong_luc
            self.dong_luc = None
            self._ghi("tha", f"{ly_do} (chặn {giu:.0f}s)")
            self.da_mo = True
            self.vua_mo = time.monotonic()

    def xu_ly(self, man: str) -> None:
        """`man`: man vua hien (THU_TU). Goi theo thu tu log."""
        if man == "splash":
            if self.dong_luc is not None:
                self._ghi("tha", "app mở lại từ Splash")
            self.dong_luc, self.da_mo = None, False
            self.vua_mo, self.da_cho, self.thay_show = 0.0, False, False
            self._ghi("tha")
        self.man_cuoi = man
        if self.da_mo:
            return
        i_bd, i_dich = THU_TU.index(self.kh["bat_dau"]), THU_TU.index(self.kh["man"])
        i = THU_TU.index(man)
        if self.dong_luc is None and i_bd <= i <= i_dich and not self.kh.get("ids"):
            self._dong(f"vào {man.upper()}")
        elif self.dong_luc is not None and i > i_dich:
            self._mo(f"rời {self.kh['man'].upper()} sang {man.upper()}")

    def _dong_log(self, dong: str) -> None:
        if _AD_ACT.search(dong):
            # Chi AdActivity mo ngay sau Splash moi la inter splash (inter OB5 / resume thi khong).
            if self.man_cuoi == "splash":
                self.xu_ly("spl_inter")
            return
        for e in fa_log.parse(dong):
            p = e.get("params") or {}
            if self.vua_mo and (p.get("ad_unit_id") in self.kh.get("ids", ()) and e.get("name") == "ad_load"
                                if self.kh.get("ids") else e.get("name") == "ad_show"):
                # Biet ID thi cho dung ad dich: ad_show cua ad khac (304 o OB4) khong phai ad bi giu
                # (Pixel 6 09/11/2026: tool di tiep khi 304 show, 303 ve sau 18s thi OB5 da bi bo qua).
                self.thay_show = True
            uid = (e.get("params") or {}).get("adunitid", "")
            if (e.get("name") == "track_ad_request" and uid in self.kh.get("ids", ()) and not self.da_mo
                    and (not self.man_cuoi or THU_TU.index(self.man_cuoi) <= THU_TU.index(self.kh["man"]))):
                self._dong(f"app gửi request …{uid[-10:]} ở {(self.man_cuoi or 'splash').upper()}")
            m = _VIEW.match(e.get("name", ""))
            if m and m.group(1) in THU_TU:
                self.xu_ly(m.group(1))

    async def _ap_dung(self) -> None:
        """Dat tuong lua theo thu tu che do da ghi (lenh adb khong chen nhau)."""
        while True:
            che_do = await self._hang.get()
            try:
                await mang_cham.chan(self.client, self.serial, self.package, che_do == "giu")
            except Exception as exc:  # noqa: BLE001 - ghi lai, report noi ro; tat() van tra mang
                self.lich.append(f"{time.strftime('%H:%M:%S')} LỖI đặt tường lửa ({che_do}): {exc}")

    async def _theo_doi(self) -> None:
        guard(self.serial)
        self._proc = await asyncio.create_subprocess_exec(
            self.client.adb, "-s", self.serial, "logcat", "-v", "epoch", "-T", "1",
            "ActivityTaskManager:I", f"{fa_log.TAG}:V", "FA:V", "*:S",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
        while True:
            try:
                raw = await asyncio.wait_for(self._proc.stdout.readline(), timeout=1.0)
            except asyncio.TimeoutError:
                raw = None
            if raw == b"":
                break
            if raw:
                self._dong_log(raw.decode("utf-8", "replace"))
            if self.dong_luc is not None and time.monotonic() - self.dong_luc > GIU_TOI_DA_S:
                self._mo(f"quá {GIU_TOI_DA_S:.0f}s chưa rời {self.kh['man'].upper()}, tự trả để ad không timeout")

    def bat(self) -> None:
        global _DANG_CHAY
        _DANG_CHAY = self
        self._hang = asyncio.Queue()
        self._tasks = [asyncio.ensure_future(self._ap_dung()), asyncio.ensure_future(self._theo_doi())]

    async def tat(self) -> None:
        global _DANG_CHAY
        if _DANG_CHAY is self:
            _DANG_CHAY = None
        if self._proc is not None and self._proc.returncode is None:
            self._proc.kill()
        for t in self._tasks:
            t.cancel()
            try:
                await t
            except (asyncio.CancelledError, Exception):
                pass


async def cho_ad_ve_muon() -> float:
    """Goi truoc moi thao tac lai app. Ngay sau khi tra mang: cho toi khi thay `ad_show` hoac het
    CHO_AD_HUNG_S - mot lan moi luot. Tra so giay da cho (0 neu khong can)."""
    w = _DANG_CHAY
    if w is None or not w.vua_mo or w.da_cho:
        return 0.0
    w.da_cho = True
    bat_dau = time.monotonic()
    while not w.thay_show and time.monotonic() - w.vua_mo < CHO_AD_HUNG_S:
        await asyncio.sleep(0.3)
    cho = time.monotonic() - bat_dau
    w.lich.append(f"{time.strftime('%H:%M:%S')} chờ ad về muộn ở màn hứng {cho:.0f}s"
                  + (" (ad đã về)" if w.thay_show else " (hết giờ, ad chưa về)"))
    return cho
