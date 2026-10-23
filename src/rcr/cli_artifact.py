"""Ghi lai link artifact cua luot chay vua publish.

Tool khong publish duoc artifact (chay o 127.0.0.1, khong co duong toi
claude.ai) - Claude publish roi goi lenh nay de ghi lai. Xem artifact_link.

    rcr-artifact --url https://claude.ai/... --generated-at 2026-09-25T21:40:00+0700
    rcr-artifact                      # in link da luu cua luot truoc

Ghi link xong thi gui tin Discord "Report da publish". Kem `--app` thi them mot
dong vao docs/usage-log.md (cac co con lai chi de dien cot cho dong do).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from . import discord_notify, usage_log
from .artifact_link import doc, ghi


def _log_usage(args: argparse.Namespace, url: str) -> None:
    row = usage_log.build_row(
        date=time.strftime("%d/%m/%Y"), app=args.app, version=args.version or "—",
        cases=args.cases or "—", result=args.result or "—", bugs=args.bugs or "—",
        report=args.report or url, tool_minutes=args.tool_minutes)
    usage_log.append_row(row, Path(args.usage_log) if args.usage_log else None)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="rcr-artifact",
        description="Ghi/đọc link artifact của lượt chạy đã publish.")
    parser.add_argument("--url", default="", help="link artifact vừa publish")
    parser.add_argument("--generated-at", default="",
                        help="mốc `generated_at` của lượt đã publish")
    parser.add_argument("--out", default="out", help="thư mục chứa artifact.json")
    parser.add_argument("--app", default="",
                        help="tên app + version; có thì ghi thêm một dòng vào docs/usage-log.md")
    parser.add_argument("--version", default="", help="cột Version của usage-log")
    parser.add_argument("--cases", default="", help="cột Số case, vd `54 (4 nhóm)`")
    parser.add_argument("--result", default="", help="cột Kết quả, vd `35 PASS · 11 FAIL`")
    parser.add_argument("--bugs", default="", help="cột Bug app xác nhận")
    parser.add_argument("--report", default="", help="cột Report (mặc định: link artifact)")
    parser.add_argument("--tool-minutes", type=float, default=None,
                        help="phút máy chạy; thiếu thì cột Tiết kiệm ghi `?`")
    parser.add_argument("--usage-log", default="", help="đường dẫn usage-log.md (mặc định docs/)")
    args = parser.parse_args(argv)

    goc = Path(args.out)
    if not args.url:
        print(json.dumps(doc(goc), ensure_ascii=False))
        return 0
    if not args.generated_at:
        # Thieu moc thi khong biet link dang tro toi luot nao - mot bao cao cu
        # se duoc gui di nhu bao cao cua lan chay vua roi.
        print("Lỗi: có --url thì phải có --generated-at.", file=sys.stderr)
        return 1
    ban = ghi(args.url, args.generated_at, goc)
    if args.app:
        _log_usage(args, args.url)
    discord_notify.send("done", f"Report đã publish · {args.app or 'rc-check'}", [],
                      link=args.url)
    print(json.dumps(ban, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
