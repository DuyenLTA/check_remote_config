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


async def bat(client, serial: str) -> None:
    """Bat log verbose cho FA-SVC. Phai goi TRUOC khi mo lai app."""
    guard(serial)
    for key in (f"log.tag.{TAG}", "log.tag.FA"):
        await client.shell(serial, "setprop", key, "VERBOSE")


async def doc(client, serial: str) -> list[dict]:
    """Cac event da ban ra trong buffer hien tai."""
    guard(serial)
    out, _, _ = await client.shell(serial, "logcat", "-d", "-s", TAG, "FA:V")
    return parse(out)


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
        ra.append({"name": m.group("name").strip(), "origin": origin,
                   "params": _params(m.group("body"))})
    # Cung event in o ca hai tag -> bo ban trung lien tiep.
    gon: list[dict] = []
    for e in ra:
        if not gon or (e["name"], e["params"]) != (gon[-1]["name"], gon[-1]["params"]):
            gon.append(e)
    return gon


def _params(body: str) -> dict:
    ra = {}
    for phan in _SPLIT.split(body or ""):
        key, _, gia_tri = phan.partition("=")
        key = _SHORT.sub("", key.strip())
        if key:
            ra[key] = gia_tri.strip()
    return ra
