"""Chuan hoa event quang cao tu log de cham checklist SDK Next-Gen.

Event cua lib Apero ghi ad unit va dinh dang khong dong nhat (do tren Sorapix
1.6.0, 24/10/2026): `ad_show` / `ad_load` dung `ad_unit_id` + `native`,
`track_ad_request` / `paid_ad_impression` dung `adunitid` + `NATIVE`. Moi luat
cham so unit va dinh dang qua `unit()` / `fmt()` de khong chấm Sai oan vi lech
ten param.
"""

from __future__ import annotations

import re

from . import fa_log

AD_EVENTS = ("track_ad_request", "track_ad_matched_request", "ad_load", "ad_show",
             "paid_ad_impression", "paid_ad_impression_value", "event_user_click_ads",
             "ad_impression", "ad_click")
# Cua so ghep hai event cung mot luot (giay). Do thuc te: matched -> load < 1 s,
# show -> paid < 0,3 s; de rong hon cho may cham.
CUA_SO_MATCHED_LOAD = 3.0
CUA_SO_SHOW_PAID = 3.0
CUA_SO_PAID_VALUE = 1.0

_CLASS_ERR = re.compile(r"NoClassDefFoundError|ClassNotFoundException|NoSuchMethodError")
# Lib chan request khi offline, khong goi SDK -> khong co ad_load failed (skill nextgen, LingoSpeak 10/2026).
_FAST_FAIL = re.compile(r"no internet|failing ad request fast|MobileAds ready but no internet", re.I)


def unit(e: dict) -> str:
    """Phan so cuoi cua ad unit ('…/9997937842'). Khong co unit -> '' (va `gan` khong ghep no voi ai)."""
    p = e["params"]
    return (p.get("adunitid") or p.get("ad_unit_id") or "").split("/")[-1]


def fmt(e: dict) -> str:
    """Dinh dang chuan: banner | interstitial | native | rewarded | rewarded_interstitial | app_open."""
    f = e["params"].get("ad_format", "").strip().lower().replace(" ", "_")
    return {"inter": "interstitial", "appopen": "app_open", "open": "app_open",
            "reward": "rewarded"}.get(f, f)


def ok(e: dict) -> bool:
    """ad_load / ad_show thanh cong."""
    p = e["params"]
    return (p.get("load_status") or p.get("show_status") or "").lower() == "success"


def doc_events(text: str) -> list[dict]:
    """Event quang cao (co gio) tu mot file logcat threadtime."""
    return [e for e in fa_log.parse_co_gio(text) if e["name"] in AD_EVENTS]


def loc(events, name: str, *, thanh_cong: bool | None = None, dinh_dang: str = "") -> list[dict]:
    ra = [e for e in events if e["name"] == name]
    if thanh_cong is not None:
        ra = [e for e in ra if ok(e) == thanh_cong]
    if dinh_dang:
        ra = [e for e in ra if fmt(e) == dinh_dang]
    return ra


def gan(events, name: str, moc: dict, truoc: float, sau: float, cung_unit: bool = True) -> list[dict]:
    """Event `name` trong [moc.ts - truoc, moc.ts + sau], cung unit voi `moc` (unit rong khong ghep)."""
    if cung_unit and not unit(moc):
        return []
    return [e for e in events if e["name"] == name and moc["ts"] - truoc <= e["ts"] <= moc["ts"] + sau
            and (not cung_unit or unit(e) == unit(moc))]


def ghep_mot_mot(nguon: list[dict], dich: list[dict], hop) -> tuple[list[tuple[dict, dict]], list[dict], list[dict]]:
    """Ghep 1-1 theo thu tu thoi gian: moi `dich` chi duoc dung cho MOT `nguon`.

    Tranh hai ad_show cung dua vao mot paid, hay mot lan reload muon request cua
    lan load truoc. -> (cap, nguon_le, dich_le).
    """
    con = sorted(dich, key=lambda e: e["ts"])
    cap, le = [], []
    for a in sorted(nguon, key=lambda e: e["ts"]):
        b = next((x for x in con if hop(a, x)), None)
        if b is None:
            le.append(a)
        else:
            con.remove(b)
            cap.append((a, b))
    return cap, le, con


def dong(e: dict) -> str:
    """Mot dong bang chung ngan cho report."""
    p = e["params"]
    them = p.get("load_status") or p.get("show_status") or ""
    return f"{e['t']} {e['name']} {fmt(e) or '-'} …{unit(e)}" + (f" {them}" if them else "")


_TT = re.compile(r"^\d\d-\d\d \d\d:\d\d:\d\d\.\d+\s+(\d+)\s+\d+\s+[VDIWEF]\s+(\S+?)\s*:")


def pid_app(text: str, package: str) -> set[str]:
    """PID cua app trong log (moi lan mo mot PID): `am_proc_start` (buffer events) va `Start proc`."""
    ra = set()
    pk = re.escape(package)
    for m in re.finditer(rf"am_proc_start: \[\d+,(\d+),\d+,{pk}[,\]]|Start proc (\d+):{pk}[/:\s]", text or ""):
        ra.add(m.group(1) or m.group(2))
    return ra


def dong_cua_app(text: str, package: str) -> list[str]:
    """Chi dong do CHINH app in (loc PID): may test co the cai nhieu app Apero cung in tag AperoAdmob."""
    pids = pid_app(text, package)
    ra = []
    for d in (text or "").splitlines():
        m = _TT.match(d)
        if m and m.group(1) in pids:
            ra.append(d)
    return ra


def loi_thieu_lop(text: str, package: str) -> list[str]:
    """NoClassDefFoundError / ClassNotFoundException / NoSuchMethodError tu tien trinh app."""
    return [d.strip() for d in dong_cua_app(text, package) if _CLASS_ERR.search(d)]


def crash(text: str, package: str) -> list[str]:
    """FATAL EXCEPTION / ANR cua app (khoi FATAL phai co dong `Process: <pkg>`)."""
    ra = []
    dongs = (text or "").splitlines()
    for i, d in enumerate(dongs):
        if "FATAL EXCEPTION" in d and any(f"Process: {package}," in x for x in dongs[i:i + 4]):
            ra.append(d.strip())
        elif ("ANR in " + package) in d or ("am_anr" in d and f",{package}," in d):
            ra.append(d.strip())
    return ra


def chan_khi_offline(text: str, package: str) -> bool:
    """CHINH app (loc PID) bao chan request luc mat mang - khong lay dong 'no internet' cua he thong."""
    return any(_FAST_FAIL.search(d) for d in dong_cua_app(text, package))


def tach_moc(text: str, tag: str, chu: str) -> tuple[str, str]:
    """(doan truoc, doan sau) dong moc `tag` co chu `chu` (dung cot tag, khong lay dong adbd)."""
    dongs = (text or "").splitlines()
    for i, d in enumerate(dongs):
        m = _TT.match(d)
        if m and m.group(2) == tag and chu in d:
            return "\n".join(dongs[:i]), "\n".join(dongs[i + 1:])
    return text or "", ""
