"""FastAPI app: middleware, error handler, static. Route nam o routes.py.

CHI bind 127.0.0.1 - tool khong co auth ma dieu khien duoc adb. Middleware chan
them o day de khong phu thuoc cach khoi dong: chay bang `uvicorn --host 0.0.0.0`
cung khong phoi ra LAN duoc.
"""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .adb_parsers import AdbError, AdbTransportError
from .models import RcError
from .routes import router

log = logging.getLogger(__name__)
WEB = Path(__file__).parent / "web"

ALLOWED_HOSTS = {"127.0.0.1", "localhost", "[::1]"}

app = FastAPI(title="Remote Config Case Runner")
app.include_router(router)


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


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(WEB / "index.html")


app.mount("/web", StaticFiles(directory=WEB), name="web")
