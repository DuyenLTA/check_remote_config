"""Bang thoi gian theo loai va so ket qua tung dong giua cac lượt, cho `rcr-do-thoi-gian` (ham thuan, test duoc)."""

from __future__ import annotations

import collections


def loai(k: str, mo_ta: str) -> str:
    """Gom ban ghi vao nhom de doc bang: dump, dumpsys, input, screencap, Firebase..."""
    if k == "adb":
        if "uiautomator dump" in mo_ta:
            return "uiautomator dump"
        if "dumpsys window" in mo_ta or "dumpsys activity" in mo_ta:
            return "dumpsys window/activity"
        if "input " in mo_ta:
            return "input tap/swipe"
        if "rcr_uidump" in mo_ta:
            return "dump cat/rm"
        return "adb khac"
    if k == "adb_bin":
        return "screencap" if "screencap" in mo_ta else "adb_bin khac"
    if k == "http":
        return "http firebase" if ("firebase" in mo_ta or "oauth2" in mo_ta) else "http khac"
    return k


def bang(d: dict, chi_tiet: str | None = None) -> str:
    """Bang tong theo loai (so lan, giay, %); kem `chi_tiet` thi them top noi goi cua loai do."""
    tong = d.get("tong") or 0.0
    c: dict[str, list] = collections.defaultdict(lambda: [0, 0.0])
    for k, mo_ta, t, *_ in d.get("ghi") or []:
        x = c[loai(k, mo_ta)]
        x[0] += 1
        x[1] += t
    dong = [f"Tong {tong:.0f}s"]
    da_do = 0.0
    for k, (n, t) in sorted(c.items(), key=lambda x: -x[1][1]):
        da_do += t
        dong.append(f"  {k:26s} {n:5d} lan {t:7.1f}s {t / tong * 100 if tong else 0:5.1f}%  tb {t / n:.2f}s")
    dong.append(f"  {'(khong do duoc)':26s}           {max(tong - da_do, 0):7.1f}s")
    if chi_tiet:
        nc: dict[str, list] = collections.defaultdict(lambda: [0, 0.0])
        for k, mo_ta, t, *rest in d.get("ghi") or []:
            if loai(k, mo_ta) == chi_tiet:
                khoa = rest[1] if len(rest) > 1 and rest[1] else "?"
                if k == "sleep":
                    khoa = f"{mo_ta} {khoa}"
                nc[khoa][0] += 1
                nc[khoa][1] += t
        dong.append(f"Chi tiet '{chi_tiet}' theo noi goi:")
        dong += [f"  {n:4d} {t:7.1f}s {k}" for k, (n, t) in sorted(nc.items(), key=lambda x: -x[1][1])[:25]]
    return "\n".join(dong)


def so_dong(luots: list[dict]) -> tuple[str, int]:
    """So verdict tung dong Expected cua cac lượt cung bo case. Tra (bao cao, so dong lech)."""
    ds = [{r["key"]: r for r in (d.get("records") or [])} for d in luots]
    if not ds:
        return "", 0
    dong, lech = [], 0
    for key, r0 in ds[0].items():
        dong.append(key + "  " + " | ".join(f"{d[key]['verdict']} ({d[key].get('thoi_gian_s')}s)"
                                            if key in d else "?" for d in ds))
        for i, l in enumerate(r0.get("lines") or []):
            vs = [(d[key]["lines"][i] if key in d and i < len(d[key].get("lines") or []) else {}) for d in ds]
            khac = len({v.get("v") for v in vs}) > 1
            lech += khac
            dong.append(f"  dong {i + 1}: " + " | ".join(str(v.get("v")) for v in vs)
                        + ("  <-- LECH" if khac else "") + "   " + str(l.get("e", ""))[:60])
            if khac:
                dong += [f"       - {str(v.get('r'))[:220]}" for v in vs]
    dong.append(f"So dong lech: {lech}")
    return "\n".join(dong), lech
