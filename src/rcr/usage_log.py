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


# --- Log luot bot -----------------------------------------------------------------------------------------------
# Bot ghi vao out/ (khong theo git) chu khong vao docs/usage-log.md: may bot sua file da commit thi lan `git pull`
# cap nhat bot sau do bi chan vi xung dot. Moi may bot co file rieng; gop vao docs/ khi tong ket.
FILE_BOT = "usage-log-bot.md"
DAU_BANG_BOT = (
    "# Log lượt bot — rc-check\n\n"
    "Bot tự ghi một dòng mỗi lượt chạy tới bước báo kết quả (XONG / DUNG / LOI / HET_GIO); lượt cài hỏng, thiếu\n"
    "testvsl hoặc QA bấm Dừng không có dòng. \"Thời gian tool\" là thời gian Claude chạy\n"
    "/rc-check, không tính lúc cài app. Tiết kiệm = 3 giờ test tay − thời gian tool, chỉ tính lượt Xong của bộ TC.\n\n"
    "| Ngày | Máy | Loại | App | Version | Package | Người duyệt | Trạng thái | Kết quả | Bug | Report "
    "| Thời gian tool | Tiết kiệm |\n"
    "|---|---|---|---|---|---|---|---|---|---|---|---|---|\n"
)


def dong_luot_bot(job: dict, kq: dict, ngay: str) -> str:
    phut = kq.get("phut")
    tool = f"{round(phut)} phút" if isinstance(phut, (int, float)) and phut > 0 else "?"
    loai = job.get("loai_job") or "check"
    tinh = loai == "check" and kq.get("trang_thai") == "XONG" and tool != "?"
    cells = [ngay, job.get("ten_may") or "?", loai, f"{job.get('ma', '')} {job.get('ten', '')}".strip(),
             job.get("version", ""), job.get("package", ""), job.get("nguoi_duyet_ten") or "?",
             kq.get("trang_thai", "?"), (kq.get("tom_tat") or "")[:160], str(len(kq.get("bugs") or [])),
             kq.get("link") if str(kq.get("link", "")).startswith("https://") else "file đính kèm Discord",
             tool, saving(phut) if tinh else "—"]
    return "| " + " | ".join(_cell(c) for c in cells) + " |"


def ghi_luot_bot(job: dict, kq: dict, out_dir: Path, ngay: str) -> bool:
    """Them dong cua luot vao `out_dir/usage-log-bot.md` (tao bang neu chua co). Loi ghi khong lam hong luot."""
    path = Path(out_dir) / FILE_BOT
    try:
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(DAU_BANG_BOT, encoding="utf-8")
    except OSError as exc:
        print(f"usage-log bot: không tạo được {path}: {type(exc).__name__}", file=sys.stderr)
        return False
    return append_row(dong_luot_bot(job, kq, ngay), path)
