"""Cham dong Expected cua tab TC "widget" bang bang chung `act_widget` ghi vao record cac buoc.

AIP893 widget 12/11/2026 (user duyet cach cham tay lam chuan):
  "Widget xuat hien tren home screen dien thoai."  -> `dumpsys appwidget` co widget provider la app, gan vao host.
  "Popup dong." / "Popup dong, ve man Home."        -> dump sau buoc cuoi (cung man voi luc thay popup) khong con
                                                       chu cua popup (title/CTA theo vsl_widget_config, mac dinh
                                                       "Add Widget" / "Add Widget Now").
  'Toast "Widget added!" ...'                       -> toast nghe duoc (accessibility event) luc bam xac nhan.
  "App mo tu Splash, luong giong tap icon app."     -> man app hien dau tien sau khi tap widget la Splash.
Khong co bang chung tuong ung (case khong co buoc widget) -> None, de luat chung cham nhu cu.
"""

from __future__ import annotations

import json
import re

from . import assert_ui, ui_dump
from .verdict_levels import FAIL, NEEDS_HUMAN, PASS, out, worst

TREN_HOME_RE = re.compile(r"widget.{0,40}(?:xu[ấa]t\s*hi[ệe]n|c[óo]\s+m[ặa]t|đ[ưu][ợo]c\s+th[êe]m|n[ằa]m).{0,40}"
                          r"(?:home\s*screen|m[àa]n\s+h[ìi]nh\s+ch[íi]nh|launcher)", re.I)
POPUP_DONG_RE = re.compile(r"\bpopup\s+(?:đã\s+|da\s+|b[ịi]\s+)?(?:đóng|dong|t[ắa]t)\b", re.I)
TOAST_RE = re.compile(r"\btoast\b", re.I)
QUOTED_RE = re.compile(r"[\"“”']([^\"“”']{2,60})[\"“”']")
MO_TU_SPLASH_RE = re.compile(r"m[ởo]\s+(?:t[ừu]|t[ạa]i|v[àa]o)\s+splash", re.I)
# Chu mac dinh cua popup Add Widget khi RC khong dat (AIP893 R02-02: dump thay 'Add Widget', 'Add Widget Now').
CHU_POPUP_MAC_DINH = ("Add Widget", "Add Widget Now")
KEY_WIDGET_RE = re.compile(r"^(?:vsl_)?widget_")


def cham(text: str, drive: dict, cfg: dict | None = None) -> dict | None:
    steps = drive.get("steps") or []
    if TREN_HOME_RE.search(text):
        return _tren_home(steps)
    if TOAST_RE.search(text) and QUOTED_RE.search(text):
        return _toast(QUOTED_RE.search(text).group(1), steps)
    if MO_TU_SPLASH_RE.search(text):
        return _mo_tu_splash(steps)
    if POPUP_DONG_RE.search(text) and _la_case_widget(cfg, steps):
        ket = _popup_dong(drive, cfg)
        # "Popup dong, ve man Home": ve man dich cham bang man dang focus sau buoc cuoi.
        man = assert_ui._man_da_toi(text, drive)
        if man:
            ket = out(worst([ket["verdict"], man["verdict"]]), f"{ket['reason']}; {man['reason']}", text)
        return ket
    return None


def _ghi(steps, khoa: str) -> list[dict]:
    return [s[khoa] for s in steps if isinstance(s.get(khoa), dict)]


def _tren_home(steps) -> dict | None:
    ds = [w for g in _ghi(steps, "widget_xac_nhan") + _ghi(steps, "widget_launcher") for w in g.get("appwidget") or []]
    da_doc = _ghi(steps, "widget_xac_nhan") + _ghi(steps, "widget_launcher")
    if not da_doc:
        return None
    if ds:
        w = ds[-1]
        return out(PASS, f"dumpsys appwidget: widget id={w['id']} provider {w['provider'].split('/')[-1]} "
                         f"gắn trên {w['host'] or 'host'}", w["provider"])
    return out(FAIL, "dumpsys appwidget không có widget nào của app gắn trên launcher", "")


def _toast(chu: str, steps) -> dict | None:
    nghe = [g for g in _ghi(steps, "widget_xac_nhan") if g.get("toast") is not None]
    if not nghe:
        return None                   # khong nghe toast (khong co dialog / loi) -> de luat chung
    thay = [t for g in nghe for t in g["toast"]]
    if any(chu.casefold() in t.casefold() for t in thay):
        return out(PASS, f"toast {chu!r} hiện lúc bấm xác nhận thêm widget (accessibility event)", chu)
    if thay:
        return out(FAIL, f"toast hiện là {', '.join(map(repr, thay))}, không phải {chu!r}", ", ".join(thay))
    return out(NEEDS_HUMAN, f"nghe accessibility event lúc bấm xác nhận nhưng không bắt được toast nào "
                            f"(máy có thể không phát event toast) — xem tay toast {chu!r}", chu)


def _mo_tu_splash(steps) -> dict | None:
    ghi = _ghi(steps, "mo_tu_widget")
    if not ghi:
        return None
    g = ghi[-1]
    if not g.get("tap"):
        return out(NEEDS_HUMAN, f"chưa tap được widget: {g.get('loi') or 'không rõ'}", "")
    ds = g.get("displayed") or []
    if not ds:
        return out(NEEDS_HUMAN, "tap widget xong không đọc được dòng Displayed nào của app trong logcat"
                   + (f" ({g['loi']})" if g.get("loi") else ""), "")
    dau = ds[0]["activity"].split(".")[-1]
    chuoi = " → ".join(d["activity"].split(".")[-1] for d in ds)
    if "Splash" in dau:
        return out(PASS, f"tap widget → màn đầu tiên {dau}" + (f" (+{ds[0]['ms']})" if ds[0].get("ms") else "")
                   + f"; màn đã hiện: {chuoi}", chuoi)
    return out(FAIL, f"tap widget → màn đầu tiên là {dau}, không phải Splash; màn đã hiện: {chuoi}", chuoi)


def _la_case_widget(cfg, steps) -> bool:
    if any(KEY_WIDGET_RE.search(k) for k in (cfg or {})):
        return True
    return any(s.get(k) for s in steps for k in ("widget_xac_nhan", "widget_launcher", "mo_tu_widget"))


def chu_popup(cfg: dict | None) -> set[str]:
    """Chu nhan ra popup Add Widget: title / CTA theo vsl_widget_config, cong chu mac dinh."""
    chu = set(CHU_POPUP_MAC_DINH)
    try:
        conf = json.loads((cfg or {}).get("vsl_widget_config") or "{}")
    except (TypeError, ValueError):
        conf = {}
    for hop in ("addWidgetDialog", "tutorialDialog"):
        d = conf.get(hop) if isinstance(conf, dict) else None
        if isinstance(d, dict):
            chu |= {str(d[k]) for k in ("title", "cta") if d.get(k)}
    return {c.casefold() for c in chu}


def _chu_tren(xml: str, chu: set[str]) -> list[str]:
    try:
        nodes = ui_dump.parse_dump(xml)
    except Exception:                     # noqa: BLE001 - dump hong = khong co chu nao
        return []
    return sorted({n.text for n in nodes if n.visible and n.text.casefold() in chu})


def _popup_dong(drive: dict, cfg) -> dict:
    chu = chu_popup(cfg)
    cuoi = drive.get("final") or {}
    if not cuoi.get("dump"):
        return out(NEEDS_HUMAN, "chưa chụp được màn sau bước cuối", "")
    truoc = [s for s in drive.get("steps") or [] if s is not cuoi and not str(s.get("step", "")).startswith("(sau")]
    thay = [(s, _chu_tren(s.get("dump") or "", chu)) for s in truoc]
    thay = [(s, c) for s, c in thay if c]
    if not thay:
        return out(NEEDS_HUMAN, "chưa thấy popup Add Widget ở màn nào trước đó — không có gì để đối chiếu đóng", "")
    buoc, chu_popup_thay = thay[-1]
    man = (buoc.get("activity") or "").split(".")[-1]
    man_cuoi = (cuoi.get("activity") or "").split(".")[-1]
    if man and man_cuoi != man:
        return out(NEEDS_HUMAN, f"sau bước cuối đang ở {man_cuoi or '?'}, không phải màn có popup ({man})", man_cuoi)
    con = _chu_tren(cuoi["dump"], chu)
    if con:
        return out(FAIL, f"sau bước cuối vẫn thấy {', '.join(map(repr, con))} — popup chưa đóng", ", ".join(con))
    return out(PASS, f"bước {buoc.get('n')} thấy popup ({', '.join(map(repr, chu_popup_thay))}); dump sau bước "
                     f"cuối ở {man_cuoi} không còn chữ của popup — popup đã đóng", man_cuoi)
