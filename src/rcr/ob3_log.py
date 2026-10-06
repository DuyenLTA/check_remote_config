"""Dong thoi gian cua trang native full OB3, doc tu log co moc epoch.

Do tren Pixel 4 + Piclux 2.8.0 (2026-10-06): trang native full OB3 la mot
fragment rieng, SDK in ro luc vao/roi:
    FO_OnboardingNativeAdFullScreen: onFragmentSelected     <- vao trang
    FO_OnboardingNativeAdFullScreen: onFragmentUnSelected   <- roi trang
    AdEventLogger: trackAdShowSuccess ... adType: NATIVE    <- ad show (t0)
    NativeAdHelper: VslTemplate4OnboardingActivity: adNativeState(Fail)
Do lan do: ad khong fill, fail luc +3.85s, roi trang luc +13.87s -> 10.02s,
khop `timer_auto_swipe=10`. Moc log chinh xac toi ms - dump UI mat ~2.5s/lan,
qua tho de phan biet 4s/5s/6s.
"""

from __future__ import annotations

import re

from .app_sandbox import guard

LOGCAT_TIMEOUT = 20.0
TAGS = ("FO_OnboardingNativeAdFullScreen", "NativeAdHelper", "AdEventLogger")
LINE_RE = re.compile(r"^\s*(?P<t>\d+\.\d+)\s+\d+\s+\d+\s+\w\s+(?P<tag>\S+?)\s*:\s?(?P<msg>.*)$")
VAO_RE = re.compile(r"onFragmentSelected")
ROI_RE = re.compile(r"onFragmentUnSelected")
SHOW_RE = re.compile(r"trackAdShowSuccess.*adType:\s*native", re.I)
STATE_RE = re.compile(r"OnboardingActivity:\s*adNativeState\((?P<state>\w+)\)")


async def doc(client, serial: str, pid: str) -> str:
    """Log co moc epoch cua RIENG tien trinh app, chi cac tag can cho OB3."""
    guard(serial)
    out, _, _ = await client._run(
        "-s", serial, "logcat", "-d", "-v", "epoch", "--pid", pid,
        "-s", *(f"{t}:V" for t in TAGS), timeout=LOGCAT_TIMEOUT)
    return out


def su_kien(text: str) -> list[tuple[float, str]]:
    """-> [(epoch, loai)] theo thu tu. loai: vao | roi | show | loaded | fail."""
    ra: list[tuple[float, str]] = []
    for line in (text or "").splitlines():
        m = LINE_RE.match(line)
        if not m:
            continue
        t, tag, msg = float(m.group("t")), m.group("tag"), m.group("msg")
        if tag.startswith("FO_OnboardingNativeAdFullScreen"):
            if ROI_RE.search(msg):          # "UnSelected" chua "Selected" -> xet truoc
                ra.append((t, "roi"))
            elif VAO_RE.search(msg):
                ra.append((t, "vao"))
        elif SHOW_RE.search(msg):
            ra.append((t, "show"))
        else:
            s = STATE_RE.search(msg)
            if s and s.group("state") in ("Loaded", "Fail"):
                ra.append((t, s.group("state").lower()))
    return ra


def luot_ghe(events: list[tuple[float, str]]) -> list[dict]:
    """Moi lan vao trang OB3 -> {vao, roi, show, fail, t0, nguon_t0}.

    t0 = luc ad SHOW (TC dem timer tu do). Ad khong fill thi t0 = luc ad fail
    (trang chuyen sang man mac dinh); khong co ca hai thi t0 = luc vao trang.
    """
    ra: list[dict] = []
    cur: dict | None = None
    for t, kind in events:
        if kind == "vao":
            cur = {"vao": t, "roi": None, "show": None, "loaded": None, "fail": None}
            ra.append(cur)
        elif cur is None:
            continue
        elif kind == "roi" and cur["roi"] is None:
            cur["roi"] = t
        elif kind in ("show", "loaded", "fail") and cur["roi"] is None and cur[kind] is None:
            cur[kind] = t
    for v in ra:
        mo = v["show"] or v["loaded"]
        v["t0"], v["nguon_t0"] = ((mo, "ad show") if mo else
                                  (v["fail"], "ad fail (không fill)") if v["fail"] else
                                  (v["vao"], "lúc vào trang"))
        v["co_ad"] = bool(mo)
    return ra
