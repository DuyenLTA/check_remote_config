"""Moc gio doc logcat cho che do chay chuoi (`--chuoi`).

Che do chuoi chay nhieu case "Tiep noi" trong MOT lan mo app nen logcat khong duoc xoa giua cac case. Moi
case cham hai lan: log RIENG cua case (tu luc case bat dau) va log DON tu dau chuoi. `TU` la moc dang dung:
None = doc het buffer (che do thuong / log don), "<epoch giay>" = chi doc tu moc do (`logcat -T`).
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar

TU: ContextVar[str | None] = ContextVar("log_tu", default=None)


def them() -> list[str]:
    """Doi so `-T <moc>` chen vao lenh `logcat -d` khi dang doc theo moc; khong co moc -> []."""
    tu = TU.get()
    return ["-T", tu] if tu else []


@contextmanager
def doc_tu(moc: str | None):
    """`with doc_tu(moc):` moi lenh doc log ben trong chi lay dong sau `moc`."""
    token = TU.set(moc)
    try:
        yield
    finally:
        TU.reset(token)


async def bay_gio(client, serial: str) -> str:
    """Gio may (epoch giay, 3 so le) - moc bat dau mot case trong chuoi."""
    out, _, _ = await client.shell(serial, "echo", "$EPOCHREALTIME")
    s = (out or "").strip()
    return f"{float(s):.3f}" if s else ""
