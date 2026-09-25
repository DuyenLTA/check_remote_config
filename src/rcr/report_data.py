"""Gom ket qua chay thanh du lieu cho report. Thuan du lieu, khong I/O.

Tach khoi cli_check de cli chi con doc tham so; tach khoi report_html de doi
bo cuc trang khong dung toi phan gom du lieu.

KHONG mang theo `dump` XML: moi dump vai tram KB, 14 case la report vai chuc MB.
Dump chi dung luc cham (`assert_check`), cham xong thi bo.
"""

from __future__ import annotations


def actual_text(run: dict, drive: dict) -> str:
    """Mot cau ta lai luot chay that - de doc canh cot Expected."""
    parts = []
    units = (run.get("ads") or {}).get("units") or {}
    for u in sorted(units.values(), key=lambda x: (x["type"], x["unit"])):
        got = "đã show" if u["shown"] else ("load được" if u["loaded"] else "không fill")
        parts.append(f'{u["type"]} {u["unit"]} {got}')
    states = [s["state"] for s in (run.get("ads") or {}).get("banner_states", [])]
    if states:
        parts.append("adBannerState " + " → ".join(states))
    steps = drive.get("steps") or []
    if steps:
        stopped = drive.get("stopped_at") or 0
        parts.append(
            f'lái {len(steps)} bước' + (f", dừng ở bước {stopped}" if stopped else ", đi hết")
        )
    verify = run.get("verify") or {}
    if verify and not verify.get("ok", True):
        parts.append("config KHÔNG sống qua lần mở app")
    return " · ".join(parts) or "không thu được dữ liệu nào"


def error_record(key: str, row: dict, message: str) -> dict:
    """Case khong chay duoc (config khong dat duoc, adb loi...) - van len report.

    Bo qua im lang la tester tuong case do da chay va dat.
    """
    return {
        "key": key,
        "tab": (row.get("tab") or "").replace("TC SDK", "").strip(),
        "group": row.get("feature") or "Không chạy được",
        "label": row.get("label", ""),
        "precondition": row.get("precondition", ""),
        "actual": message,
        "overrides": {},
        "verdict": "BLOCKED",
        "reset": "—",
        "drive": "—",
        "keys_not_used": [],
        "lines": [],
        "ads": [],
        "banner_states": [],
        "steps": [],
    }


def case_record(key: str, row: dict, result: dict) -> dict:
    """Mot case -> mot the tren report."""
    run = (result.get("runs") or [{}])[0]
    drive = run.get("drive") or {}
    ads = (run.get("ads") or {}).get("units") or {}
    return {
        "key": key,
        "tab": (row.get("tab") or "").replace("TC SDK", "").strip(),
        # Nhom theo TINH NANG (cot Feature cua file TC), khong theo tab: tester
        # doc theo man hinh/chuc nang chu khong theo ban SDK.
        "group": row.get("feature") or (row.get("tab") or "").replace("TC SDK", "").strip(),
        "label": row.get("label", ""),
        "precondition": row.get("precondition", ""),
        "actual": actual_text(run, drive),
        "overrides": run.get("overrides") or {},
        "verdict": result.get("verdict", ""),
        "reset": (result.get("reset") or {}).get("mode", ""),
        "drive": drive.get("status", "—"),
        "keys_not_used": result.get("keys_not_used") or [],
        "lines": [
            {"v": l["verdict"], "e": l["expected"], "r": l["reason"]}
            for l in (run.get("assert") or {}).get("lines", [])
        ],
        "pending": (run.get("assert") or {}).get("pending", 0),
        "ads": [
            {"t": u["type"], "u": u["unit"], "req": u["requested"], "load": u["loaded"],
             "show": u["shown"], "keys": u.get("rc_keys") or []}
            for u in ads.values()
        ],
        "banner_states": [s["state"] for s in (run.get("ads") or {}).get("banner_states", [])],
        "steps": [
            {"n": s["n"], "s": s["step"], "k": s["action"]["kind"],
             "blocked": bool(s.get("screen_blocked")),
             "shot": s.get("shot", ""), "shot_warning": s.get("shot_warning", "")}
            for s in drive.get("steps", [])
        ],
    }


def page_data(baseline, tc: dict, records: list[dict], app_label: str = "") -> dict:
    """Du lieu day du cho `report_html.build`."""
    name = app_label or baseline.package.split(".")[-1]
    sdk = tc.get("sdk") or "—"
    notes = tc.get("notes") or []
    # Ghi chu kieu "app moi hon delta moi nhat" phai len dau trang: doc so lieu
    # ma khong biet bo TC lech ban la hieu sai ca luot.
    warn = " · ".join(n for n in notes if "moi hon" in n or "Bo qua" in n)
    tabs = ", ".join(sorted({c.get("tab", "") for c in records if c.get("tab")}))
    return {
        "title": f"Lượt chấm {name} {sdk}",
        "eyebrow": f"Remote Config Case Runner · TC SDK {tabs or sdk}",
        "warn": warn,
        "subtitle": (
            f"{len(records)} case lấy từ bộ TC chung, chạy trên máy thật — mỗi case tự đặt "
            "remote config, mở lại app, lái các bước Action rồi chấm từng dòng Expected."
        ),
        "spec": {
            "Máy": baseline.serial,
            "App": baseline.package,
            "SDK First Open": sdk,
            "Key remote config": f"{len(baseline.configs)} · {len(baseline.mirrored_keys)} key bị mirror",
            "Bộ TC": f"{tc.get('total', 0)} case · {tc.get('runnable', 0)} chạy tự động được",
            "Đã chạy lượt này": f"{len(records)} case",
        },
        "cases": records,
    }
