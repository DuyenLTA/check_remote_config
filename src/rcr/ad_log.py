"""Doc log quang cao cua app: unit nao duoc request, load duoc, show duoc.

VI SAO CHAM BANG LOG CHU KHONG BANG MAT: inter load nhanh hon banner nen no
nhay len de mat banner truoc khi kip nhin. Test tay cung phai chay vai lan moi
thay banner. Co dong log request/load la du ket luan logic dung.

Grammar do THAT tren may 2026-09-25 (Piclux 2.8.0 / FO SDK 3.5.4-alpha02).
Ban nay KHONG co tag `FOR_TESTER_*` nao - chi co hai nguon:

    BannerAdHelper: SplashActivity: adBannerState(Loading)
    AdEventLogger: trackAdRequest adPlatform:Admob  - adUnitId: *****495  -  adType: BANNER
    AdEventLogger: trackAdLoadSuccess - adUnitId: *****588  -  adType: interstitial  - ...
    AdEventLogger: trackAdLoadFailed  - adUnitId: *****825  -  adType: banner  -  errorCode: 3 ...
    AdEventLogger: trackAdShowSuccess - adUnitId: *****588  -  adType: interstitial  - ...

ID BI CHE, chi con 3 so cuoi (`*****825`) -> doi chieu voi ID trong remote config
PHAI theo duoi. Ba so cuoi co the trung nhau giua 2 unit; luc do tra ca hai va
noi ro la mo ho, khong chon bua mot cai.
"""

from __future__ import annotations

import re

from .app_sandbox import guard

LOGCAT_TIMEOUT = 30.0
TAGS = ("AdEventLogger", "BannerAdHelper")

EVENT_RE = re.compile(
    r"track(?P<event>AdRequest|AdMatchedRequest|AdLoadSuccess|AdLoadFailed|AdShowSuccess|AdShowFailed)"
    r".*?adUnitId:\s*(?P<id>[*\w]+).*?adType:\s*(?P<type>\w+)",
    re.I,
)
BANNER_STATE_RE = re.compile(r"BannerAdHelper:\s*(?P<screen>\w+):\s*adBannerState\((?P<state>\w+)\)")
ERROR_RE = re.compile(r"errorMessage:\s*(?P<msg>[^-]+?)\s*-\s*errorDomain|errorType:\s*(?P<etype>\w+)")
MASK_RE = re.compile(r"^\*+(?P<tail>\d{2,})$")
# "occurred for ad unit *****588 from ad network ..." - moi lan ad tinh tien
# la mot impression. Dong nay di kem logPaidAdImpression.
IMPRESSION_RE = re.compile(r"occurred for ad unit\s+(?P<id>[*\w]+)")


async def clear(client, serial: str) -> None:
    """Xoa buffer truoc khi mo app - khong thi nhat log cua luot truoc."""
    guard(serial)
    await client._run("-s", serial, "logcat", "-c", timeout=LOGCAT_TIMEOUT)


async def read(client, serial: str, pid: str) -> str:
    """Log cua RIENG tien trinh app. Tag nay app nao co SDK ads cung in."""
    guard(serial)
    spec = [f"{t}:V" for t in TAGS]
    out, _, _ = await client._run(
        "-s", serial, "logcat", "-d", "--pid", pid, "-s", *spec, timeout=LOGCAT_TIMEOUT
    )
    return out


def parse(log_text: str) -> dict:
    """-> {events: [...], banner_states: [...]} theo dung thu tu xay ra."""
    events, states, impressions = [], [], []
    for line in (log_text or "").splitlines():
        seen = IMPRESSION_RE.search(line)
        if seen:
            impressions.append(seen.group("id"))
            continue
        state = BANNER_STATE_RE.search(line)
        if state:
            states.append({"screen": state.group("screen"), "state": state.group("state")})
            continue
        hit = EVENT_RE.search(line)
        if not hit:
            continue
        err = ERROR_RE.search(line)
        events.append({
            "event": hit.group("event"),
            "unit": hit.group("id"),
            "type": hit.group("type").lower(),
            "error": (err.group("msg") or err.group("etype")).strip() if err else "",
        })
    return {"events": events, "banner_states": states, "impressions": impressions}


def summary(parsed: dict) -> dict:
    """Gom theo (loai ad, unit): request/load/show - dung de doi chieu 2 luot."""
    out: dict[str, dict] = {}
    for unit in parsed.get("impressions", []):
        out.setdefault(f"?:{unit}", {
            "type": "?", "unit": unit, "requested": 0, "loaded": 0,
            "load_failed": 0, "shown": 0, "impressions": 0, "errors": [],
        })
    for e in parsed["events"]:
        row = out.setdefault(f"{e['type']}:{e['unit']}", {
            "type": e["type"], "unit": e["unit"], "requested": 0, "loaded": 0,
            "load_failed": 0, "shown": 0, "impressions": 0, "errors": [],
        })
        name = e["event"].lower()
        if name == "adrequest":
            row["requested"] += 1
        elif name == "adloadsuccess":
            row["loaded"] += 1
        elif name == "adloadfailed":
            row["load_failed"] += 1
            if e["error"]:
                row["errors"].append(e["error"])
        elif name == "adshowsuccess":
            row["shown"] += 1
    # Gan impression vao dung unit; unit chi thay o dong impression thi giu rieng.
    for unit in parsed.get("impressions", []):
        for key, row in out.items():
            if key.endswith(f":{unit}"):
                row["impressions"] += 1
    # Bo dong "?" neu unit do da co dong co loai ro rang.
    typed = {v["unit"] for v in out.values() if v["type"] != "?"}
    return {k: v for k, v in out.items() if v["type"] != "?" or v["unit"] not in typed}


def match_rc_id(masked: str, rc_ids: dict[str, str]) -> list[str]:
    """Unit bi che (`*****825`) -> cac key remote config co ID cung duoi.

    Tra NHIEU key la mo ho, khong chon bua. Tra rong nghia la unit nay khong
    den tu remote config - app hardcode, hoac tu key ma app khong doc.
    """
    m = MASK_RE.match(masked.strip())
    if not m:
        return []
    tail = m.group("tail")
    return sorted(k for k, v in rc_ids.items() if v.rsplit("/", 1)[-1].endswith(tail))
