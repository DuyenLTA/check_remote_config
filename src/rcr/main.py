"""FastAPI app. CHI bind 127.0.0.1 - tool khong co auth ma dieu khien duoc adb.

Middleware chan them o day de khong phu thuoc cach khoi dong: chay bang
`uvicorn --host 0.0.0.0` cung khong phoi ra LAN duoc.
"""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import rc_baseline, rc_patch, rc_verify
from .adb_client import AdbClient
from .adb_parsers import AdbError, AdbTransportError
from .models import RcError

log = logging.getLogger(__name__)
WEB = Path(__file__).parent / "web"

ALLOWED_HOSTS = {"127.0.0.1", "localhost", "[::1]"}

app = FastAPI(title="Remote Config Case Runner")

_client: AdbClient | None = None
_baselines: dict[tuple[str, str], object] = {}  # (serial, package) -> RcBaseline


def client() -> AdbClient:
    global _client
    if _client is None:
        _client = AdbClient()
    return _client


@app.middleware("http")
async def only_localhost(request: Request, call_next):
    host = (request.headers.get("host") or "").rsplit(":", 1)[0]
    if host not in ALLOWED_HOSTS:
        return JSONResponse({"detail": "Chi truy cap qua 127.0.0.1"}, status_code=403)
    return await call_next(request)


@app.exception_handler(AdbTransportError)
async def _transport(_r, exc: AdbTransportError):
    return JSONResponse({"detail": f"Mat ket noi may: {exc}"}, status_code=503)


@app.exception_handler(AdbError)
async def _adb(_r, exc: AdbError):
    return JSONResponse({"detail": str(exc)}, status_code=400)


@app.exception_handler(RcError)
async def _rc(_r, exc: RcError):
    return JSONResponse({"detail": str(exc)}, status_code=400)


@app.get("/api/devices")
async def devices() -> dict:
    ds = await client().devices()
    return {
        "devices": [
            {"serial": d.serial, "state": d.state, "label": d.label, "ready": d.ready}
            for d in ds
        ]
    }


@app.get("/api/packages")
async def packages(serial: str) -> dict:
    """Danh sach app ben thu 3 + co debuggable khong.

    Tra ca app khong debuggable (kem co) de tester thay ro vi sao khong chon duoc,
    thay vi app bien mat khoi danh sach ma khong hieu tai sao.
    """
    names = await client().packages(serial)
    out = []
    for name in names:
        try:
            dbg = await client().is_debuggable(serial, name)
        except AdbError:
            dbg = False
        out.append({"package": name, "debuggable": dbg})
    return {"packages": out}


@app.post("/api/baseline")
async def baseline(serial: str, package: str) -> dict:
    """Doc baseline remote config. Ket qua giu trong bo nho cho phase sau dung."""
    bl = await rc_baseline.read(client(), serial, package)
    _baselines[(serial, package)] = bl
    return bl.summary


@app.get("/api/baseline/keys")
async def baseline_keys(serial: str, package: str, q: str = "", limit: int = 200) -> dict:
    """Tra danh sach key (loc theo `q`) - de tester doi chieu voi file testcase."""
    bl = _baselines.get((serial, package))
    if bl is None:
        raise HTTPException(400, "Chua doc baseline cho app nay.")
    ql = q.strip().lower()
    keys = sorted(k for k in bl.configs if not ql or ql in k.lower())
    mirrored = bl.mirrored_keys
    return {
        "total": len(keys),
        "keys": [
            {
                "key": k,
                "value": bl.configs[k][:200],
                "mirrored": k in mirrored,
            }
            for k in keys[:limit]
        ],
    }


def _need_baseline(serial: str, package: str):
    bl = _baselines.get((serial, package))
    if bl is None:
        raise HTTPException(400, "Chua doc baseline cho app nay. Bam 'Doc baseline' truoc.")
    return bl


@app.post("/api/patch")
async def patch(serial: str, package: str, overrides: dict[str, str]) -> dict:
    """Dat gia tri remote config. Ghi mirror -> settings -> activate (sau cung)."""
    bl = _need_baseline(serial, package)
    res = await rc_patch.patch(client(), bl, overrides)
    return res.summary | {
        "note": "Tat HAN app (recent apps -> swipe) roi mo lai de app doc config moi, "
        "sau do bam 'Verify'.",
    }


@app.post("/api/verify")
async def verify(serial: str, package: str, expected: dict[str, str]) -> dict:
    """Doc lai config sau khi mo app. Lech -> BLOCKED, khong phai FAIL."""
    bl = _need_baseline(serial, package)
    res = await rc_verify.verify(client(), bl, expected)
    out = res.summary
    if not res.ok:
        out["hint"] = (
            "Config bi thay doi sau khi mo app. Thuong la build dev dat "
            "minimumFetchInterval = 0 nen throttle vo hieu, app fetch that va de mat patch.\n"
            "Day la BLOCKED (chua test duoc), KHONG phai FAIL (app sai)."
        )
    return out


@app.post("/api/restore")
async def restore(serial: str, package: str) -> dict:
    """Tra app ve nguyen trang baseline, kem moc fetch cu (app tu lay lai config that)."""
    bl = _need_baseline(serial, package)
    res = await rc_patch.restore(client(), bl)
    return res.summary


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(WEB / "index.html")


app.mount("/web", StaticFiles(directory=WEB), name="web")
