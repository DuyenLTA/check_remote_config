"""Them mot dong vao bang `docs/usage-log.md` khi report duoc publish."""

from __future__ import annotations

import sys
from pathlib import Path

DEFAULT_PATH = Path(__file__).resolve().parents[2] / "docs" / "usage-log.md"
TEST_TAY_PHUT = 180  # 3 gio test tay trung binh (tester uoc tinh)


def _cell(text: str) -> str:
    return " ".join(str(text).split()).replace("|", "\\|") or "—"


def saving(tool_minutes: float | None) -> str:
    if tool_minutes is None:
        return "?"
    return f"{round(TEST_TAY_PHUT - tool_minutes)} phút"


def build_row(*, date: str, app: str, version: str, cases: str, result: str, bugs: str,
              report: str, tool_minutes: float | None) -> str:
    tool = f"{round(tool_minutes)} phút" if tool_minutes is not None else "?"
    cells = [date, app, version, cases, result, bugs, report, tool, "3 giờ", saving(tool_minutes)]
    return "| " + " | ".join(_cell(c) for c in cells) + " |"


def append_row(row: str, path: Path | None = None) -> bool:
    """Chen `row` ngay sau dong cuoi cua bang (truoc doan van theo sau). Khong dong cac dong khac."""
    path = path or DEFAULT_PATH
    try:
        raw = path.read_bytes().decode("utf-8")
        eol = "\r\n" if "\r\n" in raw else "\n"
        lines = raw.split(eol)
        sep = next((i for i, l in enumerate(lines) if l.startswith("|") and "---" in l), None)
        if sep is None:
            print(f"usage-log: không thấy bảng trong {path}, bỏ qua", file=sys.stderr)
            return False
        last = sep
        while last + 1 < len(lines) and lines[last + 1].startswith("|"):
            last += 1
        lines.insert(last + 1, row)
        path.write_bytes(eol.join(lines).encode("utf-8"))
        return True
    except (OSError, UnicodeDecodeError) as exc:
        print(f"usage-log: không ghi được {path}: {type(exc).__name__}", file=sys.stderr)
        return False
