"""Tach unit ad bi GOP vi trung 3 so cuoi ID, bang event Firebase co ID day du.

VI SAO: log AdEventLogger chi in `*****034`, nen 202 high (…2764762034) va 303 high (…8588924034) cua AIP872
thanh MOT unit voi rc_keys ca hai vi tri. Dong "native 303 load/show" doc unit gop thi 202 show la tuong 303 da
show (PASS gia), va nguoc lai (AIP872 1.9.0, 09/11/2026). App ban event Firebase `track_ad_request`
(`adunitid`), `ad_load` (`ad_unit_id`, `load_status`), `ad_show` (`ad_unit_id`) co ID DAY DU -> dem lai
request / load / show cho tung vi tri.

Chi tach khi unit that su gop nhieu vi tri VA biet ID day du cua tung key (`ids`, case_evidence). Loai event nao
app khong ban trong ca luot thi giu so dem cu cua unit gop cho truong do (khong bia so 0).
"""
from __future__ import annotations

from .assert_ad_screen import _man_cua_key

# (ten event, ten param ID, truong cua unit)
DEM = (("track_ad_request", "adunitid", "requested"),
       ("ad_load", "ad_unit_id", "loaded"),
       ("ad_show", "ad_unit_id", "shown"))


def _dem(events, ten: str, param: str, ids: set) -> int:
    n = 0
    for e in events:
        p = e.get("params") or {}
        if e.get("name") == ten and p.get(param) in ids and (ten != "ad_load" or p.get("load_status", "success")
                                                               == "success"):
            n += 1
    return n


def tach(units: dict, events) -> dict:
    """{key: unit} -> {key: unit}, unit gop thanh nhieu unit (key `<cu>#<ma vi tri>`), moi unit mot vi tri."""
    ev = list(events or ())
    co = {ten for ten, _, _ in DEM if any(e.get("name") == ten for e in ev)}
    if not co or not units:
        return units
    ra: dict = {}
    for k, u in units.items():
        nhom: dict[str, list[str]] = {}
        chung = []
        for key in u.get("rc_keys") or ():
            m = _man_cua_key(key)
            (nhom.setdefault(m[0], []) if m else chung).append(key)
        ids_cua = u.get("ids") or {}
        if len(nhom) < 2 or any(not any(ids_cua.get(x) for x in keys) for keys in nhom.values()):
            ra[k] = u
            continue
        for ma, keys in nhom.items():
            ids = {i for x in keys for i in ids_cua.get(x) or ()}
            row = {**u, "rc_keys": keys + chung, "ids": {x: ids_cua.get(x) or [] for x in keys},
                   "tach_tu": u.get("unit", "")}
            for ten, param, truong in DEM:
                if ten in co:
                    row[truong] = _dem(ev, ten, param, ids)
            ra[f"{k}#{ma}"] = row
    return ra
