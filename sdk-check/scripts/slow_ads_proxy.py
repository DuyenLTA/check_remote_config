"""HTTP CONNECT proxy that simulates a slow network (KT-02, HV-07).

usage: python3 -I slow_ads_proxy.py PORT CONNECT_DELAY_S KBPS [HOST_REGEX]
Every tunnel waits CONNECT_DELAY_S before connecting upstream and is throttled to KBPS KB/s
per direction. With HOST_REGEX only matching hosts are slowed, the rest pass straight through.

Wire it to the phone (always undo afterwards, or the phone loses network):
  adb reverse tcp:PORT tcp:PORT
  adb shell settings put global http_proxy 127.0.0.1:PORT
  ... test ...
  adb shell settings put global http_proxy :0 ; adb reverse --remove-all ; kill <proxy pid>
Ad hosts regex used so far:
  'doubleclick|googlesyndication|googleads|admob|googleadservices|facebook|fbcdn|applovin|mtgglobals|rayjump|pangle|vungle|byteoversea'
Note: GMA socket timeout is ~10 s; a delay >= 10 s makes ads fail instead of arriving late.
"""
import asyncio
import re
import sys
import time

PORT = int(sys.argv[1])
DELAY = float(sys.argv[2])
KBPS = float(sys.argv[3])
PATTERN = re.compile(sys.argv[4]) if len(sys.argv) > 4 else None


async def pipe(reader, writer, slow):
    try:
        while True:
            data = await reader.read(4096)
            if not data:
                break
            writer.write(data)
            await writer.drain()
            if slow and KBPS > 0:
                await asyncio.sleep(len(data) / (KBPS * 1024))
    except Exception:
        pass
    finally:
        try:
            writer.close()
        except Exception:
            pass


async def handle(cr, cw):
    try:
        head = await cr.readuntil(b"\r\n\r\n")
    except Exception:
        cw.close()
        return
    parts = head.split(b"\r\n")[0].decode(errors="replace").split()
    if len(parts) < 2 or parts[0].upper() != "CONNECT":
        cw.write(b"HTTP/1.1 405 Only CONNECT\r\n\r\n")
        await cw.drain()
        cw.close()
        return
    host, _, port = parts[1].rpartition(":")
    slow = PATTERN is None or bool(PATTERN.search(host))
    print(f"{time.strftime('%H:%M:%S')} {'SLOW' if slow else 'pass'} {host}", flush=True)
    if slow and DELAY > 0:
        await asyncio.sleep(DELAY)
    try:
        ur, uw = await asyncio.open_connection(host, int(port))
    except Exception:
        cw.write(b"HTTP/1.1 502 Bad Gateway\r\n\r\n")
        await cw.drain()
        cw.close()
        return
    cw.write(b"HTTP/1.1 200 Connection established\r\n\r\n")
    await cw.drain()
    await asyncio.gather(pipe(cr, uw, slow), pipe(ur, cw, slow))


async def main():
    server = await asyncio.start_server(handle, "127.0.0.1", PORT)
    async with server:
        await server.serve_forever()


asyncio.run(main())
