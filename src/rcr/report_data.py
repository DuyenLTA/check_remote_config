"""Gom ket qua chay thanh du lieu cho report. Thuan du lieu, khong I/O.

Tach khoi cli_check de cli chi con doc tham so; tach khoi report_html de doi
bo cuc trang khong dung toi phan gom du lieu.

KHONG mang theo `dump` XML: moi dump vai tram KB, 14 case la report vai chuc MB.
Dump chi dung luc cham (`assert_check`), cham xong thi bo.
"""

from __future__ import annotations

from . import report_runs


def actual_text(run: dict, drive: dict) -> str:
    """Mot cau ta lai luot chay that - de doc canh cot Expected.

    KHONG liet ke tung unit o day: bang ads ngay duoi da co du `req/load/show`
    cua tung unit, chep lai bang chu la doc hai lan cung mot thu va lam troi mat
    nhung y chi co o day (lai may buoc, config co song khong).
    """
    parts = []
    units = (run.get("ads") or {}).get("units") or {}
    if units:
        show = sum(1 for u in units.values() if u["shown"])
        load = sum(1 for u in units.values() if u["loaded"] and not u["shown"])
        req = sum(1 for u in units.values() if u["requested"])
        dem = [f"{req} unit được request"]
        if load:
            dem.append(f"{load} load được")
        dem.append(f"{show} đã show" if show else "không unit nào show (không fill)")
        parts.append(" · ".join(dem))
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
    """Mot case -> mot the tren report. Case nhieu luot: moi dong/buoc/unit
    mang nhan luot cua no (xem `report_runs`)."""
    runs = result.get("runs") or [{}]
    nhan = report_runs.nhan_luot(runs)
    lines, steps, ads, actual = [], [], [], []
    for run, n in zip(runs, nhan):
        drive = run.get("drive") or {}
        lines += report_runs.gan_nhan(n, [
            {"v": l["verdict"], "e": l["expected"], "r": l["reason"],
             **({"scope": l["scope"]} if l.get("scope") else {})}
            for l in (run.get("assert") or {}).get("lines", [])], "e")
        steps += report_runs.gan_nhan(n, [
            {"n": s["n"], "s": s["step"], "k": s["action"]["kind"],
             # Ly do la thu DUY NHAT giai thich mot buoc "khong thao tac":
             # bo no di thi buoc lai-roi-dung-dung-cho va buoc that su khong
             # lam gi trong y het nhau tren report.
             "r": _ly_do(s),
             "blocked": bool(s.get("screen_blocked")),
             "shot": s.get("shot", ""), "shot_warning": s.get("shot_warning", "")}
            for s in drive.get("steps", [])], "s")
        ads += report_runs.gan_nhan(n, [
            {"t": u["type"], "u": u["unit"], "req": u["requested"], "load": u["loaded"],
             "show": u["shown"], "keys": u.get("rc_keys") or []}
            for u in ((run.get("ads") or {}).get("units") or {}).values()], "t")
        actual.append((f"{n}: " if n else "") + actual_text(run, drive))
    dau = runs[0]
    return {
        "key": key,
        "tab": (row.get("tab") or "").replace("TC SDK", "").strip(),
        # Nhom theo TINH NANG (cot Feature cua file TC), khong theo tab: tester
        # doc theo man hinh/chuc nang chu khong theo ban SDK.
        "group": row.get("feature") or (row.get("tab") or "").replace("TC SDK", "").strip(),
        "label": row.get("label", ""),
        "precondition": row.get("precondition", ""),
        "actual": " · ".join(actual) if len(actual) == 1 else " | ".join(actual),
        "overrides": report_runs.overrides_gop(runs),
        "verdict": result.get("verdict", ""),
        # Dieu kien precondition doi ma may nay khong tao duoc - phai hien tren
        # report, khong thi doc vao tuong case da chay dung nhanh TC mo ta.
        "precondition_thieu": result.get("precondition_thieu") or [],
        # Ep ad fail bang cach nao - loi mang va no-fill that cho cung mot
        # man hinh nhung khac ma loi, nguoi doc phai biet la cach nao.
        "ep_ad_fail": result.get("ep_ad_fail", ""),
        "reset": (result.get("reset") or {}).get("mode", ""),
        "drive": (dau.get("drive") or {}).get("status", "—"),
        "ob3": _ob3_tom((dau.get("drive") or {}).get("timeline")),
        "keys_not_used": result.get("keys_not_used") or [],
        "lines": lines,
        "pending": sum((r.get("assert") or {}).get("pending", 0) for r in runs),
        "po": sum((r.get("assert") or {}).get("po", 0) for r in runs),
        "ads": ads,
        "banner_states": [s["state"] for r in runs
                          for s in (r.get("ads") or {}).get("banner_states", [])],
        "steps": steps,
    }


def _ly_do(step: dict) -> str:
    """Ly do cua buoc, kem moc t0 va so cu lien tuc neu co - nguoi doc can
    biet thao tac lam LUC NAO va bao nhieu lan, khong chi "vuot"."""
    phan = [step["action"].get("reason", "")]
    moc = step.get("moc")
    if moc:
        phan.append(f"làm lúc t0+{moc['lam_luc']:g}s (TC ghi t0+{moc['t0_cong']:g}s; {moc['ghi_chu']})")
    lt = step.get("lien_tuc")
    if lt:
        phan.append(f"{lt['lan']} lần trong {lt['giay']:g}s")
    if step.get("xoay"):
        phan.append("đã xoay " + " → ".join("ngang" if h == "ngang" else "dọc" for h in step["xoay"]))
    return " · ".join(p for p in phan if p)


def page_data(baseline, tc: dict, records: list[dict], app_label: str = "") -> dict:
    """Du lieu day du cho `report_html.build`."""
    name = app_label or baseline.package.split(".")[-1]
    # "—" la cho HIEN o o trong bang, KHONG duoc ghep vao tieu de: tieu de
    # thanh "Luot cham Piclux —", dau gach cut duoi (do 2026-09-28).
    ban = (tc.get("sdk") or "").strip()
    sdk = ban or "—"
    notes = tc.get("notes") or []
    # Ghi chu kieu "app moi hon delta moi nhat" phai len dau trang: doc so lieu
    # ma khong biet bo TC lech ban la hieu sai ca luot.
    warn = " · ".join(n for n in notes if "moi hon" in n or "Bo qua" in n)
    tabs = ", ".join(sorted({c.get("tab", "") for c in records if c.get("tab")}))
    return {
        # "Piclux 2.8.0 3.5.0" - hai so version dinh nhau, khong ai doc ra cai
        # nao la app cai nao la SDK. Ban SDK phai co nhan di kem.
        "title": f"Lượt chấm {name}" + (f" · SDK FO {ban}" if ban else ""),
        "eyebrow": "Remote Config Case Runner"
                   + (f" · TC SDK {tabs or ban}" if (tabs or ban) else ""),
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


def _ob3_tom(tl: dict | None) -> dict:
    """Dong thoi gian OB3 da do, moc tinh bang giay tu luc vao trang lan dau.

    Giu lai trong JSON de soi lai vi sao mot dong thoi gian ra PASS/FAIL ma
    khong phai chay lai case.
    """
    luot = (tl or {}).get("luot") or []
    if not luot:
        return {}
    goc = luot[0]["vao"]

    def rel(t):
        return round(t - goc, 2) if t else None

    return {"luot": [{k: rel(v[k]) for k in ("vao", "roi", "show", "loaded", "fail", "t0")}
                     for v in luot],
            "khung": [[rel(k["t"]), int(k["x"]), k["dem"]] for k in (tl.get("khung") or [])],
            "thao_tac": [rel(t) for t in (tl.get("thao_tac") or [])]}
