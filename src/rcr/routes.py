"""Route API. Logic nam o cac module rc_*; day chi dieu phoi va tra JSON.

Tach khoi main.py de main chi con app + middleware + error handler: phase sau
con them route (chay case, cham, report) ma module phai duoi 200 LOC.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from . import app_state, rc_baseline, rc_extract, rc_patch, rc_verify, tc_loader
from .adb_parsers import AdbError

router = APIRouter(prefix="/api")

MAX_TC_BYTES = 20 * 1024 * 1024
TC_SUFFIXES = (".xlsx", ".xlsm")


@router.get("/devices")
async def devices() -> dict:
    ds = await app_state.client().devices()
    return {
        "devices": [
            {"serial": d.serial, "state": d.state, "label": d.label, "ready": d.ready}
            for d in ds
        ]
    }


@router.get("/packages")
async def packages(serial: str) -> dict:
    """App ben thu 3 + co debuggable khong.

    Tra ca app khong debuggable (kem co) de tester thay ro vi sao khong chon
    duoc, thay vi app bien mat khoi danh sach ma khong hieu tai sao.
    """
    c = app_state.client()
    out = []
    for name in await c.packages(serial):
        try:
            dbg = await c.is_debuggable(serial, name)
        except AdbError:
            dbg = False
        out.append({"package": name, "debuggable": dbg})
    return {"packages": out}


@router.post("/baseline")
async def baseline(serial: str, package: str) -> dict:
    bl = await rc_baseline.read(app_state.client(), serial, package)
    app_state.put_baseline(bl)
    return bl.summary


@router.get("/baseline/keys")
async def baseline_keys(serial: str, package: str, q: str = "", limit: int = 200) -> dict:
    """Danh sach key (loc theo `q`) - de doi chieu voi file testcase."""
    bl = app_state.need_baseline(serial, package)
    ql = q.strip().lower()
    keys = sorted(k for k in bl.configs if not ql or ql in k.lower())
    mirrored = bl.mirrored_keys
    return {
        "total": len(keys),
        "keys": [
            {"key": k, "value": bl.configs[k][:200], "mirrored": k in mirrored}
            for k in keys[:limit]
        ],
    }


@router.post("/patch")
async def patch(serial: str, package: str, overrides: dict[str, str]) -> dict:
    """Dat gia tri. Ghi mirror -> settings -> activate.json (sau cung)."""
    bl = app_state.need_baseline(serial, package)
    res = await rc_patch.patch(app_state.client(), bl, overrides)
    return res.summary | {
        "note": "Tat HAN app (recent apps -> swipe) roi mo lai de app doc config moi, "
        "sau do bam 'Verify'."
    }


@router.post("/verify")
async def verify(serial: str, package: str, expected: dict[str, str]) -> dict:
    """Doc lai config sau khi mo app. Lech -> BLOCKED, khong phai FAIL."""
    bl = app_state.need_baseline(serial, package)
    res = await rc_verify.verify(app_state.client(), bl, expected)
    out = res.summary
    if not res.ok:
        out["hint"] = (
            "Config bi thay doi sau khi mo app. Thuong la build dev dat "
            "minimumFetchInterval = 0 nen throttle vo hieu, app fetch that va de mat patch.\n"
            "Day la BLOCKED (chua test duoc), KHONG phai FAIL (app sai)."
        )
    return out


@router.post("/restore")
async def restore(serial: str, package: str) -> dict:
    """Tra nguyen trang + moc fetch cu -> app tu lay lai config that."""
    bl = app_state.need_baseline(serial, package)
    res = await rc_patch.restore(app_state.client(), bl)
    return res.summary


@router.post("/testcases")
async def testcases(serial: str, package: str, file: UploadFile = File(...)) -> dict:
    """Nap file testcase -> bang case kem key/value da boc va co needs_human.

    Loc bang whitelist = key THAT cua app (tu baseline) -> param analytics tu
    roi ra, tester khong phai khai gi.
    """
    bl = app_state.need_baseline(serial, package)
    name = file.filename or "(khong ten)"
    if Path(name).suffix.lower() not in TC_SUFFIXES:
        raise HTTPException(400, f"{name}: chi nhan file {' / '.join(TC_SUFFIXES)}.")
    payload = await file.read(MAX_TC_BYTES + 1)
    if not payload:
        raise HTTPException(400, f"{name}: file rong.")
    if len(payload) > MAX_TC_BYTES:
        raise HTTPException(413, f"{name}: file qua lon (toi da {MAX_TC_BYTES // 1024 // 1024}MB).")

    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        tmp.write(payload)
        tmp_path = Path(tmp.name)
    try:
        cases = tc_loader.load(tmp_path)
    finally:
        tmp_path.unlink(missing_ok=True)

    wl = rc_extract.whitelist_of(bl)
    rows, runnable = [], 0
    for c in cases:
        d = rc_extract.extract(c, wl)
        runnable += d.runnable
        rows.append({
            "n": c.n,
            "label": c.label,
            "feature": c.feature,
            "test_data": c.test_data,
            "steps": len(c.actions),
            "assertions": len(c.expects),
            **d.summary,
        })
    return {
        "file": name,
        "total": len(cases),
        "runnable": runnable,
        "whitelist_size": len(wl),
        "cases": rows,
    }
