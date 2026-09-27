"""Ghi lai link artifact cua luot chay vua publish.

Tool khong publish duoc artifact (chay o 127.0.0.1, khong co duong toi
claude.ai) - Claude publish roi goi lenh nay de ghi lai. Xem artifact_link.

    rcr-artifact --url https://claude.ai/... --generated-at 2026-09-25T21:40:00+0700
    rcr-artifact                      # in link da luu cua luot truoc
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .artifact_link import doc, ghi


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="rcr-artifact",
        description="Ghi/đọc link artifact của lượt chạy đã publish.")
    parser.add_argument("--url", default="", help="link artifact vừa publish")
    parser.add_argument("--generated-at", default="",
                        help="mốc `generated_at` của lượt đã publish")
    parser.add_argument("--out", default="out", help="thư mục chứa artifact.json")
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
    print(json.dumps(ghi(args.url, args.generated_at, goc), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
