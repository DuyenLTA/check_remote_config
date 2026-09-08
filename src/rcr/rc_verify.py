"""Doc lai config sau khi mo app -> gia tri minh dat con song khong?

VI SAO BAT BUOC: neu build dev dat `minimumFetchInterval = 0` thi throttle vo
hieu, app fetch that va DE MAT patch. Khong verify thi tool bao FAIL hang loat
ma tester khong hieu vi sao - di tim bug trong app suot buoi chieu trong khi
app chay dung, chi la config da bi thay tu duoi chan.

Lech -> BLOCKED, KHONG phai FAIL. Day la hai ket luan khac han nhau:
  FAIL    = app chay sai so voi expected
  BLOCKED = chua test duoc, vi config khong duoc giu
"""

from __future__ import annotations

import json

from . import app_sandbox
from .mirror_xml import parse_nodes
from .models import Mismatch, RcBaseline, RcError, VerifyResult

FILES_DIR = "files"
PREFS_DIR = "shared_prefs"


async def verify(client, baseline: RcBaseline, expected: dict[str, str]) -> VerifyResult:
    """So `expected` voi gia tri THUC TE dang nam tren may.

    Doc ca activate.json va cac file mirror lien quan: mot key co the dung o
    activate ma sai o mirror (hoac nguoc lai) - luc do app doc mirror se hanh xu
    theo gia tri cu.
    """
    raw, problem = await app_sandbox.cat(
        client,
        baseline.serial,
        baseline.package,
        app_sandbox.quote(f"{FILES_DIR}/{baseline.activate_name}"),
        mode=baseline.write_mode,
    )
    if problem:
        raise RcError(f"Khong doc lai duoc {baseline.activate_name}: {problem}")
    try:
        configs = json.loads(raw).get("configs_key") or {}
    except json.JSONDecodeError as exc:
        raise RcError(f"{baseline.activate_name} khong con la JSON hop le: {exc}") from exc

    out: list[Mismatch] = []
    for key, want in expected.items():
        got = configs.get(key)
        if got != want:
            out.append(Mismatch(key, want, got, where="activate"))

    out += await _verify_mirrors(client, baseline, expected)
    fetch_ms = _fetch_time(raw)
    return VerifyResult(mismatches=tuple(out), fetch_time_ms=fetch_ms)


async def _verify_mirrors(client, baseline: RcBaseline, expected: dict[str, str]):
    out: list[Mismatch] = []
    for name, nodes in baseline.mirrors.items():
        touched = {k: v for k, v in expected.items() if k in nodes}
        if not touched:
            continue
        raw, problem = await app_sandbox.cat(
            client,
            baseline.serial,
            baseline.package,
            app_sandbox.quote(f"{PREFS_DIR}/{name}"),
            mode=baseline.write_mode,
        )
        if problem:
            out.append(Mismatch("(doc file)", "", problem, where=name))
            continue
        live = parse_nodes(raw)
        for key, want in touched.items():
            node = live.get(key)
            got = node.value if node else None
            # Mirror luu co kieu; so sanh theo dang da chuan hoa cua kieu do.
            if got is None or not _same(nodes[key].kind, got, want):
                out.append(Mismatch(key, want, got, where=name))
    return out


def _same(kind: str, got: str, want: str) -> bool:
    from .mirror_xml import coerce

    try:
        return got == coerce(kind, want)
    except ValueError:
        return False


def _fetch_time(raw: str) -> int:
    try:
        return int(json.loads(raw).get("fetch_time_key") or 0)
    except (json.JSONDecodeError, TypeError, ValueError):
        return 0
