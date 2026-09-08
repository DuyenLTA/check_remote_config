#!/usr/bin/env bash
# Tu tao venv + cai thu vien lan dau (~30s), cac lan sau ~1s.
# Doi cong: PORT=9000 ./start.sh     Khong tu mo browser: RCR_NO_BROWSER=1
set -euo pipefail
cd "$(dirname "$0")"

VENV=.venv
if [ ! -x "$VENV/bin/python" ]; then
  echo "Lan dau: tao moi truong ao..."
  python3 -m venv "$VENV"
  "$VENV/bin/pip" install -q --upgrade pip
  "$VENV/bin/pip" install -q -e ".[dev]"
fi

PORT="${PORT:-8000}"
# Cong bi chiem thi nhay sang cong trong ke tiep.
for _ in $(seq 0 20); do
  if "$VENV/bin/python" -c "
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
  (sleep 1.5; (xdg-open "$URL" >/dev/null 2>&1 || open "$URL" >/dev/null 2>&1 || true) &) &
fi
# Chi bind 127.0.0.1: tool khong co auth ma dieu khien duoc adb.
exec "$VENV/bin/uvicorn" rcr.main:app --host 127.0.0.1 --port "$PORT"
