"""Doc event Firebase Analytics tu logcat.

Dong Expected "Log event complete_ob2 (co engagement_time)" truoc day phai bo
cho nguoi, trong khi may CO in ra - chi can bat log verbose truoc khi app khoi
dong.

Ba diem lay tu `auto_check_event_tracking` (da do that tren AIP922, 67/67 dong):
  - event nam o tag `FA-SVC`; tag `FA` chi in "Logging telemetry" khong kem params
  - property doc luc process START -> phai `setprop` TRUOC khi mo lai app
  - param KHONG tach bang `split(", ")`: gia tri chuoi co the chua dau phay.
    Cat o `, ` nao DUNG TRUOC mot `key=`.

Dong FA-SVC do Google Play Services in ra, PID khac PID app -> khong loc theo PID.
"""

from __future__ import annotations

import re

from .app_sandbox import guard

TAG = "FA-SVC"
_SVC = re.compile(
    r"Logging event: origin=(?P<origin>\w+),name=(?P<name>[^,]+),"
    r"params=Bundle\[\{(?P<body>.*)\}\]\s*$")
_FE = re.compile(r"Logging event \(FE\): (?P<name>[^,]+), Bundle\[\{(?P<body>.*)\}\]\s*$")
_SPLIT = re.compile(r",\s+(?=[A-Za-z_][\w.]*(?:\([^)]*\))?=)")
_SHORT = re.compile(r"\(.*\)$")
_EPOCH = re.compile(r"^\s*(\d{9,}\.\d+)\s")
# adbd in moi lenh adb shell kem gio may: dong nay la lenh tool GUI THAO TAC vao may.
_ADB_INPUT = re.compile(r"adbd service requested '.*raw:input (tap|swipe|keyevent|text)\b")
# ad_click nam trong bay nhieu giay sau mot thao tac cua tool thi tinh la do tool.
# Do 2026-10-24: Piclux BACK tren inter -> click sau 2,2s.
CUA_SO_CLICK = 5.0


async def bat(client, serial: str) -> None:
    """Bat log verbose cho FA-SVC. Phai goi TRUOC khi mo lai app."""
    guard(serial)
    for key in (f"log.tag.{TAG}", "log.tag.FA"):
        await client.shell(serial, "setprop", key, "VERBOSE")


async def doc(client, serial: str) -> list[dict]:
    """Cac event da ban ra trong buffer hien tai."""
    guard(serial)
    out, _, _ = await client.shell(serial, "logcat", "-d", "-v", "epoch", "-s", TAG, "FA:V")
    return parse(out)


async def doc_input(client, serial: str) -> list[float] | None:
    """Gio may cua tung lenh `input` tool gui qua adb, None neu may khong in log adbd."""
    guard(serial)
    out, _, _ = await client.shell(serial, "logcat", "-d", "-v", "epoch", "-s", "adbd")
    return parse_input(out)


def parse_input(text: str) -> list[float] | None:
    dong = [d for d in (text or "").splitlines() if "adbd service requested" in d]
    if not dong:
        return None   # khong biet tool da thao tac luc nao -> khong duoc tha click nao
    return [float(m.group(1)) for d in dong if _ADB_INPUT.search(d) and (m := _EPOCH.match(d))]


def parse(text: str) -> list[dict]:
    """[{name, origin, params}] tu log. Dong trung (FA + FA-SVC) chi tinh mot."""
    ra: list[dict] = []
    for dong in (text or "").splitlines():
        m = _SVC.search(dong)
        origin = m.group("origin") if m else "app"
        if not m:
            m = _FE.search(dong)
        if not m:
            continue
        e = {"name": m.group("name").strip(), "origin": origin, "params": _params(m.group("body"))}
        if t := _EPOCH.match(dong):
            e["t"] = float(t.group(1))
        ra.append(e)
    # Cung event in o ca hai tag -> bo ban trung lien tiep.
    gon: list[dict] = []
    for e in ra:
        if not gon or (e["name"], e["params"]) != (gon[-1]["name"], gon[-1]["params"]):
            gon.append(e)
    return gon


def ad_clicks(events: list[dict]) -> int:
    """So lan SDK quang cao bao `ad_click` (origin=am, ten in ra `ad_click(_ac)`).

    Tool chi duoc dong ad, khong duoc bam vao no: mot click tren ad that la traffic
    khong hop le. Do 2026-10-24 (Piclux 2.4.0): bam BACK tren inter that, 2,2s sau
    log co 2 `ad_click` - tool luc do khong doc event nay nen khong ai biet.
    """
    return sum(1 for e in events if e["name"].split("(", 1)[0] == "ad_click")


def chia_click(events: list[dict], inputs: list[float] | None) -> tuple[int, int]:
    """(ad_click do tool, ad_click app/ad tu ban khi tool khong thao tac gi).

    Do 2026-10-24 (Lingix 1.5.0, inter 102 …443): 3/3 lan GMA ghi 2 `ad_click`
    ~10,2s sau khi ad show, ke ca khi khong gui lenh nao vao may. Click do khong
    phai tool bam nen khong dung luot, chi ghi lai de bao dev. Khong co gio (log
    khong -v epoch, may khong in adbd) thi tinh het la do tool - an toan.
    """
    tool = tu_ban = 0
    for e in events:
        if e["name"].split("(", 1)[0] != "ad_click":
            continue
        t = e.get("t")
        if inputs is None or t is None or any(0 <= t - x <= CUA_SO_CLICK for x in inputs):
            tool += 1
        else:
            tu_ban += 1
    return tool, tu_ban


def _params(body: str) -> dict:
    ra = {}
    for phan in _SPLIT.split(body or ""):
        key, _, gia_tri = phan.partition("=")
        key = _SHORT.sub("", key.strip())
        if key:
            ra[key] = gia_tri.strip()
    return ra


_THREADTIME = re.compile(r"^(\d\d-\d\d \d\d:\d\d:\d\d\.\d+)\s+\d+\s+\d+\s+[VDIWEF]\s+(\S+)\s*: ?(.*)$")


def gio_threadtime(t: str) -> float:
    """'10-24 16:09:48.901' -> giay (nam co dinh 2000: 29/02 khong bi lech)."""
    import datetime
    return datetime.datetime.strptime("2000-" + t, "%Y-%m-%d %H:%M:%S.%f").timestamp()


def parse_co_gio(text: str) -> list[dict]:
    """Event FA-SVC tu file `logcat -v threadtime`, KEM GIO: [{t, ts, name, origin, params}].

    Bundle dai bi logcat cat thanh nhieu dong cung tag: dong sau khong bat dau
    bang chu "Logging"/"Upload"… thi noi vao event dang mo (giong cach skill
    nextgen-sdk-check doc, da do tren LingoSpeak). Dung de cham thu tu / cap
    event (EV-xx) - can gio, khac `parse` chi can ten + params.
    """
    tho: list[list[str]] = []
    for dong in (text or "").splitlines():
        m = _THREADTIME.match(dong.rstrip("\r"))
        if not m or m.group(2) != TAG:
            continue
        t, than = m.group(1), m.group(3)
        if than.startswith("Logging event:"):
            tho.append([t, than])
        elif tho and not tho[-1][1].rstrip().endswith("}]") and not re.match(r"^[A-Z][a-z]+ ", than):
            tho[-1][1] += than
    ra = []
    for t, than in tho:
        m = _SVC.search(than)
        if m:
            ra.append({"t": t, "ts": gio_threadtime(t), "name": _SHORT.sub("", m.group("name").strip()),
                       "origin": m.group("origin"), "params": _params(m.group("body"))})
    return ra
