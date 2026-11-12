"""Precondition doi PHIEN BAN ANDROID cua may ("Thiet bi Android < 8.0 (vd Android 7.x)").

AIP893 widget R03-01/02 12/11/2026: may lap la Pixel 4 Android 12, case doi Android < 8.0 (nhanh popup Tutorial).
Tool van chay roi tra NEEDS_HUMAN, Claude cham tay BLOCKED. User chot: khong co may do -> BLOCKED NGAY, khong chay /
khong chay lai (chay chi ton thoi gian, ket qua la cua nhanh khac).
Case "Tiep noi" case do cung BLOCKED: `run_batch` truyen precondition ca chuoi (`fo_ngon_ngu.tien_dk_chuoi`).
"""

from __future__ import annotations

import operator
import re

# "Android < 8.0", "Android ≥ 8", "Android >= 8.0", "API < 26". Khong co dau so sanh ("vd Android 7.x") -> bo qua.
ANDROID_RE = re.compile(r"\b(android|api)\s*(<=|>=|≤|≥|<|>)\s*(\d+(?:\.\d+)?)", re.I)
SO_SANH = {"<": operator.lt, "<=": operator.le, "≤": operator.le, ">": operator.gt, ">=": operator.ge,
           "≥": operator.ge}


async def doc(client, serial: str) -> tuple[str, int]:
    """(release, sdk) cua may, vd ("12", 31). Doc hong -> ("", 0): khong chan case nao."""
    try:
        rel, _, _ = await client.shell(serial, "getprop", "ro.build.version.release")
        sdk, _, _ = await client.shell(serial, "getprop", "ro.build.version.sdk")
    except Exception:                       # noqa: BLE001 - thieu phien ban chi lam mat mot luat chan som
        return "", 0
    sdk = (sdk or "").strip()
    return (rel or "").strip(), int(sdk) if sdk.isdigit() else 0


def _so(release: str) -> float | None:
    m = re.match(r"(\d+)(?:\.(\d+))?", release or "")
    return float(f"{m.group(1)}.{m.group(2) or 0}") if m else None


def thieu_android(precondition: str, release: str, sdk: int = 0) -> list[str]:
    """Dieu kien phien ban Android may nay KHONG dat -> ly do; dat / khong doi / khong doc duoc -> []."""
    ra = []
    co = _so(release)
    for loai, dau, so in ANDROID_RE.findall(precondition or ""):
        api = loai.casefold() == "api"
        gia_tri = float(sdk) if api else co
        if not gia_tri or SO_SANH[dau](gia_tri, float(so)):
            continue
        ly_do = (f"cần máy API {dau} {so}, máy lượt này API {sdk}" if api
                 else f"cần máy Android {dau} {so}, máy lượt này Android {release}")
        if ly_do not in ra:
            ra.append(ly_do)
    return ra


def record_blocked(key: str, row: dict, chosen: dict, thieu: list[str]) -> dict:
    """Case khong chay: moi dong Expected BLOCKED kem ly do, de report van liet ke du dong cua case."""
    from . import report_data
    ly_do = "; ".join(thieu)
    run = {"assert": {"lines": [{"verdict": "BLOCKED", "expected": " ".join((e or "").split()), "reason": ly_do}
                                for e in chosen.get("expects") or ()], "pending": 0, "po": 0},
           "drive": {"status": "—", "steps": []}}
    rec = report_data.case_record(key, row, {"verdict": "BLOCKED", "precondition_thieu": thieu, "runs": [run]})
    return rec | {"actual": f"không chạy — {ly_do}"}
