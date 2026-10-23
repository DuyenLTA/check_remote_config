"""Tin Discord cuoi mot luot `rcr-check --case`: quyet dinh kind/title/dong tu ket qua.

Ham thuan (`build_run_message`) tach rieng de test khong can mang / may that.
"""

from __future__ import annotations

from collections import Counter

from . import report_row

TOI_DA_CASE = 10
HANH_DONG_FAIL = "Chạy §5d: xác nhận lại từng FAIL trước khi báo dev"


def summarize(records: list[dict], *, app: str, package: str, sdk: str,
              duration_s: float | None, report: str) -> dict:
    """records (report_data.case_record) -> summary dung cho build_run_message."""
    nhan = [report_row.nhan_cua(r.get("verdict", "")) for r in records]
    dem = Counter(nhan)
    ly_do: list[str] = []
    for r, n in zip(records, nhan):
        if n != "BLOCKED":
            continue
        for t in r.get("precondition_thieu") or []:
            if t not in ly_do:
                ly_do.append(t)
    return {
        "app": app or package, "package": package, "sdk": sdk,
        "counts": {k: dem.get(k, 0) for k in ("PASS", "FAIL", "BLOCKED", "NA")},
        "fail_ids": [str(r.get("key", "")) for r, n in zip(records, nhan) if n == "FAIL"],
        "blocked_reasons": ly_do,
        "duration_s": duration_s, "report": report,
    }


def _duration(seconds: float | None) -> str:
    if seconds is None:
        return "?"
    minutes = max(1, round(seconds / 60))
    return f"{minutes // 60} giờ {minutes % 60} phút" if minutes >= 60 else f"{minutes} phút"


def build_run_message(summary: dict) -> tuple[str, str, list[str], str | None]:
    """-> (kind, title, lines, action). FAIL > 0 -> stop, con lai -> done."""
    c = summary["counts"]
    fails = summary.get("fail_ids") or []
    lines = [
        f"App: {summary['app']} ({summary['package']})",
        f"SDK: {summary.get('sdk') or '—'}",
        f"Case: {c['PASS']} PASS · {c['FAIL']} FAIL · {c['BLOCKED']} BLOCKED · "
        f"{c['NA']} NOT_VERIFIABLE",
        f"Thời gian: {_duration(summary.get('duration_s'))}",
    ]
    if c["FAIL"] > 0:
        shown = fails[:TOI_DA_CASE]
        more = f" (+{len(fails) - len(shown)} case nữa)" if len(fails) > len(shown) else ""
        lines.append("FAIL: " + ", ".join(shown) + more)
    if c["BLOCKED"] > 0:
        why = "; ".join(summary.get("blocked_reasons") or []) or "chưa rõ lý do, xem report"
        lines.append(f"BLOCKED: config bị ghi đè / chưa tạo được điều kiện — {why[:300]}")
    if summary.get("report"):
        lines.append(f"Report: {summary['report']}")
    if c["FAIL"] > 0:
        return "stop", f"Có {c['FAIL']} FAIL cần audit lại", lines, HANH_DONG_FAIL
    return "done", f"Hoàn tất · {summary['app']}", lines, None
