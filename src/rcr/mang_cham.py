"""Tao precondition "ad VE MUON" bang tuong lua theo app cua Android 13+ - khong can root.

VI SAO: bo TC co cac case doi ad chua ve luc user roi man ("Di qua LFO2 ngay khi vao man de 202 chua
kip show", "Roi OB3 truoc khi 303 ve"). Ad duoc preload tu man truoc (202 tu luc inter splash hien, 303 tu
OB1) nen tren mang that no nam san khi user toi man dich (AIP872 1.9.0: S03-01, S04-01 BLOCKED).

Tung thu proxy HTTP lam cham domain quang cao (`slow_ads_proxy.py`): KHONG co tac dung - GMA tai ad bang
QUIC (UDP 443) di thang, khong qua `http_proxy`; proxy giu / cat thi ad van load sau ~2s (do Pixel 4,
09/11/2026). Tuong lua theo app (`cmd connectivity set-package-networking-enabled`, chain OEM_DENY_3, shell
dung duoc tu Android 13) chan ca TCP lan QUIC cua rieng app va CHI DROP goi tin: request dang chay treo lai,
mo ra thi ve (do Pixel 6 Android 17: request 14:11:59 treo 38s, mo luc 14:12:37 -> load xong 14:12:51).
Mo xong ad con mat ~15s moi ve, GMA cat request o 60s -> giu toi da ~45s (`mang_cham_cua_so`).

KHONG dung cho no-fill: chan tu dau thi SDK khong gui request nao (= mat mang, luat QA: khong phai no-fill);
chan giua chung thi request treo chu khong fail ngay. No-fill van la doi `id_*` / Private DNS (run_batch).

Tao dieu kien la CHUA DU: ket qua case chi duoc nhan khi log cho thay ad that su chua show o man do
(`kiem_dieu_kien`) - run_batch kiem va ha BLOCKED neu chua dat.
"""
from __future__ import annotations

import re

from . import assert_ad_screen
from .app_sandbox import guard

SDK_TOI_THIEU = 33          # Android 13: shell moi duoc dat luat chain OEM_DENY_3
# Chan app thoi chua du: request 303 gui 32.5s van load luc 42.9s khi app dang bi chan (Pixel 6 09/11/2026) -
# GMA co duong du phong qua Google Play services (uid khac). Chan kem trong luc giu, tra lai ngay sau.
CHAN_KEM = ("com.google.android.gms",)

# Ma man trong cau precondition: LFO2, OB3...
_MAN = r"(LFO\s*\d|OB\s*\d)"
_CHUA_SHOW_O = re.compile(r"ch[ưu]a\s+(?:k[ịi]p\s+)?show\s+(?:ở|o|tại|tai)\s+" + _MAN, re.I)
# "Di qua LFO2 ngay khi vao man de 202 chua kip show" (TC 3.5.4 S03-01): man nam truoc cum "chua kip show".
_QUA_MAN_CHUA_SHOW = re.compile(r"qua\s+" + _MAN + r"\b.{0,60}?ch[ưu]a\s+(?:k[ịi]p\s+)?show", re.I)
_ROI_TRUOC_KHI_VE = re.compile(r"r[ờo]i\s+" + _MAN + r"\s+tr[ưu][ớo]c\s+khi\s+.{0,60}?\bv[ềe]\b", re.I)
_THROTTLE = re.compile(r"throttle|charles\s*proxy|m[ạa]ng\s+ch[ậa]m|\d+\s*kbps|m[ạa]ng\s+v[ừu]a\s+ph[ảa]i|show\s+mu[ộo]n"
                       r"|show\s+sau\s+~?\s*\d", re.I)


def _ma_man(s: str) -> str:
    return re.sub(r"\s+", "", s).lower()


def can_lam_cham(precondition: str) -> tuple[bool, str]:
    """(precondition can ad ve muon?, man ma ad KHONG duoc show tai do - '' neu cau khong noi man)."""
    text = precondition or ""
    for mau in (_CHUA_SHOW_O, _QUA_MAN_CHUA_SHOW, _ROI_TRUOC_KHI_VE):
        m = mau.search(text)
        if m:
            return True, _ma_man(m.group(1))
    if _THROTTLE.search(text):
        return True, ""
    return False, ""


async def _cmd(client, serial: str, *args: str) -> str:
    out, err, _ = await client.shell(serial, "cmd", "connectivity", *args)
    return (out or "") + (err or "")


async def bat(client, serial: str, package: str) -> dict:
    """Bat chain tuong lua (app van co mang). Tra trang thai de `tat` tra ve dung nhu cu.

    Raise RuntimeError khi may khong lam duoc (Android < 13) - run_batch ghi ly do, case ra BLOCKED.
    """
    guard(serial, package)
    sdk_txt, _, _ = await client.shell(serial, "getprop", "ro.build.version.sdk")
    sdk = int((sdk_txt or "0").strip() or 0)
    if sdk < SDK_TOI_THIEU:
        raise RuntimeError(f"máy Android API {sdk} không có tường lửa theo app (cần Android 13+); GMA tải ad bằng "
                           "QUIC nên proxy cũng không giữ được — cắm máy Android 13+ để tạo điều kiện ad về muộn")
    cu = "enabled" in (await _cmd(client, serial, "get-chain3-enabled"))
    trang_thai = {"package": package, "chain_cu": cu}
    if not cu:
        await _cmd(client, serial, "set-chain3-enabled", "true")
    try:
        await chan(client, serial, package, False)
    except BaseException:
        await tat(client, serial, trang_thai)    # loi giua chung: khong de chain bat lai tren may
        raise
    return trang_thai


async def chan(client, serial: str, package: str, chan_mang: bool) -> None:
    """chan_mang=True: drop moi goi tin cua app (request dang chay treo lai); False: tra mang."""
    guard(serial, package)
    for goi in (package, *CHAN_KEM):
        ra = await _cmd(client, serial, "set-package-networking-enabled", "false" if chan_mang else "true", goi)
        # Tra mang cho uid chua tung bi chan: "sUidOwnerMap does not have entry for uid" = dang co mang san
        # (Pixel 6 09/11/2026 - truoc day loi nay lam case BLOCKED va bo chain bat lai tren may).
        if "networking for" not in ra and not (not chan_mang and "does not have entry" in ra):
            raise RuntimeError(f"không đặt được tường lửa cho {goi}: {ra.strip()[:200]}")


async def tat(client, serial: str, trang_thai: dict) -> None:
    """Tra mang cho app + tat chain neu truoc do tat. Luon chay, ke ca khi case hong: quen la app mat mang."""
    package = trang_thai.get("package", "")
    try:
        if package:
            await chan(client, serial, package, False)
    finally:
        if not trang_thai.get("chain_cu"):
            await _cmd(client, serial, "set-chain3-enabled", "false")


def _unit_cua_man(units, man: str) -> list[dict]:
    return [u for u in units
            if any((v := assert_ad_screen._man_cua_key(k)) and v[1] == man for k in (u.get("rc_keys") or ()))]


def _ad_man_co_ve(events, units, man: str) -> bool:
    """Ad cua `man` co ve khong. Log AdEventLogger chi giu 3 so cuoi ID: 202 (…2764762034) va 303
    (…8588924034) gop chung mot unit `*****034`, co `loaded` cua 202 la tuong 303 da ve (AIP872 09/11/2026).
    Tin: `ad_show` co ID day du cua vi tri man do, hoac unit CHI thuoc man do co load."""
    if any(man in s["nha"] for s in assert_ad_screen.show_theo_man(events, units)):
        return True
    # Event Firebase `ad_load` co ID day du: ad ve muon roi khong show (OB5 khong hien) van la "da ve".
    ids = {i for u in _unit_cua_man(units, man) for k, v in (u.get("ids") or {}).items()
           if (m := assert_ad_screen._man_cua_key(k)) and m[1] == man for i in v}
    if any(e.get("name") == "ad_load" and (e.get("params") or {}).get("ad_unit_id") in ids
           and (e.get("params") or {}).get("load_status", "success") == "success" for e in events or ()):
        return True
    for u in _unit_cua_man(units, man):
        mans = {v[1] for k in (u.get("rc_keys") or ()) if (v := assert_ad_screen._man_cua_key(k))}
        if mans == {man} and (u.get("loaded") or u.get("shown")):
            return True
    return False


def kiem_dieu_kien(runs: list[dict], man: str, da_bat: bool, loi: str = "",
                   cach: str = "") -> tuple[list[str], str]:
    """(ly do chua tao duoc precondition, ghi chu cach da tao) sau khi case chay voi mang bi giu theo man.

    Dat = ad cua man `man` CO ve (load) nhung KHONG show ngay tai `man`. Ad khong ve lan nao la
    nhanh no-fill / timeout chu khong phai "ve muon" -> chua dat (FAIL "OB5 khong hien 303" luc do la FAIL gia).
    """
    cach = cach or "giữ mạng quảng cáo theo màn"
    if not man:
        return ["precondition không nêu màn (throttle băng thông): tường lửa chỉ chặn/mở, không bóp băng thông "
                "được — chưa tạo được điều kiện"], ""
    if not da_bat:
        return [loi or "không bật được tường lửa giữ mạng ad"], ""
    ten = man.upper()
    show_som, co_ve = [], False
    for run in runs or ():
        units = list(((run.get("ads") or {}).get("units") or {}).values())
        show_som += assert_ad_screen.ad_man_nha_da_show(run.get("events"), units, man)
        co_ve = co_ve or _ad_man_co_ve(run.get("events"), units, man)
    if show_som:
        return [f"{cach} nhưng ad {ten} ({', '.join(sorted(set(show_som)))}) vẫn show ngay ở {ten} "
                f"— chưa tạo được điều kiện ad về muộn"], ""
    if not co_ve:
        return [f"{cach} nhưng log không thấy ad {ten} về lần nào (fail / timeout, hoặc unit gộp đuôi ID mà ad "
                "chưa show), không phải về muộn"], ""
    return [], f"{cach}; log xác nhận ad {ten} có về nhưng không show ngay ở {ten}"
