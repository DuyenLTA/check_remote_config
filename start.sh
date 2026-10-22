#!/usr/bin/env bash
# Tu tao venv + cai thu vien lan dau (~30s), cac lan sau ~1s.
# Chay duoc tren macOS, Linux va Windows (Git Bash).
# Doi cong: PORT=9000 ./start.sh     Khong tu mo browser: RCR_NO_BROWSER=1
set -euo pipefail
cd "$(dirname "$0")"

# Windows (Git Bash/MSYS/Cygwin): venv de file chay o Scripts/ chu khong phai bin/,
# va thuong chi co lenh `python` chu khong co `python3`.
case "$(uname -s)" in
  MINGW*|MSYS*|CYGWIN*) IS_WINDOWS=1; VENV_BIN="Scripts" ;;
  *)                    IS_WINDOWS=0; VENV_BIN="bin" ;;
esac

VENV=.venv
VPY="$VENV/$VENV_BIN/python"
if [ ! -x "$VPY" ] && [ ! -x "$VPY.exe" ]; then
  echo "Lan dau: tao moi truong ao..."
  PY=python3
  command -v python3 >/dev/null 2>&1 && python3 -c "import sys" >/dev/null 2>&1 || PY=python
  "$PY" -m venv "$VENV"
  "$VPY" -m pip install -q --upgrade pip
  "$VPY" -m pip install -q -e ".[dev]"
fi

PORT="${PORT:-8000}"
# Cong bi chiem thi nhay sang cong trong ke tiep.
for _ in $(seq 0 20); do
  if "$VPY" -c "
import socket,sys
s=socket.socket()
try: s.bind(('127.0.0.1',$PORT)); sys.exit(0)
except OSError: sys.exit(1)
finally: s.close()
" 2>/dev/null; then break; fi
  echo "Cong $PORT dang bi dung, thu $((PORT+1))..."
  PORT=$((PORT+1))
done

URL="http://127.0.0.1:$PORT"
echo "Mo $URL"
if [ -z "${RCR_NO_BROWSER:-}" ]; then
  if [ "$IS_WINDOWS" = "1" ]; then
    (sleep 1.5; cmd.exe //c start "" "$URL" >/dev/null 2>&1 || true) &
  else
    (sleep 1.5; (xdg-open "$URL" >/dev/null 2>&1 || open "$URL" >/dev/null 2>&1 || true) &) &
  fi
fi
# Chi bind 127.0.0.1: tool khong co auth ma dieu khien duoc adb.
if [ "$IS_WINDOWS" = "1" ]; then
  # adb_client goi lenh qua asyncio subprocess; tren Windows chi ProactorEventLoop
  # lam duoc viec do. Tao loop truoc roi bao uvicorn dung loop dang co.
  exec "$VPY" -c "
import asyncio, uvicorn
cfg = uvicorn.Config('rcr.main:app', host='127.0.0.1', port=$PORT, loop='none')
asyncio.run(uvicorn.Server(cfg).serve())
"
fi
exec "$VENV/$VENV_BIN/uvicorn" rcr.main:app --host 127.0.0.1 --port "$PORT"
