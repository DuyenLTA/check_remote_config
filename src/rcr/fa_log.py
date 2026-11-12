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

from . import adb_client, log_moc

import re
import time

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
BUFFER_LOG = "16M"
# Tag rac (WebView, okhttp, he thong ROM) tat truoc moi lan mo app: ROM vivo gioi han log moi process ("ratelimit:
# Single process limit 50/s drop N lines") nen log rac dan dap day mat AdEventLogger / FA cua app -> FAIL gia hang
# loat (AIP918 Linguza 12/11/2026: 21 case phai chay lai). Khong tag nao o day duoc tool doc.
TAG_RAC = ("okhttp.Http2", "okhttp.TaskRunner", "okhttp.OkHttpClient", "VelocityTracker", "VivoConfigStore",
           "AdvertisingIdClient", "FragmentManager", "chromium", "cr_media", "cr_ChildProcessConn",
           "cr_AwAutofillManager", "TrafficStats", "adservices", "CustomTabsClient", "AdrenoGLES-0", "CursorWindow",
           "nativeloader", "TRuntime.SQLiteEventStore", "TRuntime.JobInfoScheduler", "CompatibilityChangeReporter",
           "DynamiteModule")


async def bat(client, serial: str) -> None:
    """Bat log verbose cho FA-SVC. Phai goi TRUOC khi mo lai app."""
    guard(serial)
    for key in (f"log.tag.{TAG}", "log.tag.FA"):
        await client.shell(serial, "setprop", key, "VERBOSE")
    # FA-SVC verbose in rat nhieu (dump ca lo upload): buffer mac dinh (~256K) troi sau khoang 1 phut, `logcat -d`
    # cuoi case mat event dau case (Pixel 6 09/11/2026: mat sach request / view luc vao OB1).
    await client.shell(serial, "logcat", "-G", BUFFER_LOG)
    # ROM vivo: tat han gioi han log moi process (khong can root). Chi tat tag rac van con mat dong AdEventLogger / FA
    # (AIP918 Linguza 12/11/2026, vivo V2143 log.ratelimit.level=1: case "khong co request native nao" la FAIL gia).
    # May khong co prop nay thi setprop vo hai.
    await client.shell(serial, "setprop", "log.ratelimit.level", "0")
    for tag in TAG_RAC:
        await client.shell(serial, "setprop", f"log.tag.{tag}", "S")


async def doc(client, serial: str) -> list[dict]:
    """Cac event da ban ra trong buffer hien tai."""
    guard(serial)
    out, _, _ = await client.shell(serial, "logcat", "-d", *log_moc.them(), "-v", "epoch", "-s", TAG, "FA:V")
    return parse(out)


async def doc_input(client, serial: str) -> list[float] | None:
    """Gio may cua tung lenh `input` tool gui qua adb, None neu may khong in log adbd."""
    guard(serial)
    out, _, _ = await client.shell(serial, "logcat", "-d", *log_moc.them(), "-v", "epoch", "-s", "adbd")
    ra = parse_input(out)
    if ra is not None:
        return ra
    # May khong in log adbd: lay gio tool tu ghi luc gui lenh `input`, doi sang dong ho may.
    gio = adb_client.gio_input(serial)
    if not gio:
        return None
    lech = await _lech_dong_ho(client, serial)
    return None if lech is None else [t + lech for t in gio]


async def _lech_dong_ho(client, serial: str) -> float | None:
    """Gio may tru gio may tinh (giay); None khi doc khong duoc -> khong duoc tha click nao."""
    t0 = time.time()
    out, _, _ = await client.shell(serial, "date", "+%s.%N")
    t1 = time.time()
    try:
        return float(out.strip()) - (t0 + t1) / 2
    except ValueError:
        return None


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
