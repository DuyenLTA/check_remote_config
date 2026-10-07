"""Cham cac dong Expected ve THOI GIAN tren trang native full OB3.

Nguon do (khong doan):
  - `luot`  tu ob3_log: moi lan vao trang -> vao / roi / t0 (ad show, hoac ad
            fail khi khong fill), moc epoch chinh xac toi ms
  - `khung` tu quan_sat: nhin lien tuc, moi khung co gio may + X co hien + so dem

Sai so cho phep: chuyen man do bang log -> +-1s; nut X do bang khung dump (moi
khung ~1-2.5s) -> +-1.5s. Ad khong fill ma dong Expected doi "ad show" thi
KHONG cham dong do theo t0 gia: bao ro dieu kien chua dat.
"""

from __future__ import annotations

import re

from .verdict_levels import FAIL, NEEDS_HUMAN, PASS, out

SAI_SO_LOG = 1.0
SAI_SO_KHUNG = 1.0           # khung nhanh cach nhau ~0,2s -> dung sai so cua TC (±1s)

KHONG_TU_RE = re.compile(r"kh[ôo]ng\s+(?:t[ựu]\s+|auto[\s-]*)?(?:chuy[ểe]n|swipe)|"
                         r"[ởo]\s+l[ạa]i\s+(?:m[àa]n\s+)?OB3", re.I)
TU_CHUYEN_RE = re.compile(r"(?:t[ựu]|auto)[\s-]*(?:chuy[ểe]n|swipe)|chuy[ểe]n\s+m[àa]n\s+t[ạa]i|"
                          r"h[ếe]t\s+timer.*chuy[ểe]n|chuy[ểe]n\s+sau|timer_auto_swipe", re.I)
MOT_LAN_RE = re.compile(r"đúng\s*1\s*l[ầa]n|dung\s*1\s*lan|double\s*navigate|"
                        r"chuy[ểe]n\s+m[àa]n\s+l[ầa]n\s*2|kh[ôo]ng\s+skip\s+m[àa]n", re.I)
X_RE = re.compile(r"(?:button|n[úu]t)\s*X\b|\bX\s+(?:xu[ấa]t\s+hi[ệe]n|hi[ểe]n|hi[ệe]n)", re.I)
DEM_RE = re.compile(r"đ[ếe]m\s*ng[ượu][ợo]c|countdown", re.I)
KHONG_HIEN_RE = re.compile(r"kh[ôo]ng\s+(?:hi[ểe]n\s*th[ịi]|hi[ệe]n|c[óo]|xu[ấa]t\s+hi[ệe]n)", re.I)
# "Button X hien thi NGAY tu dau (khong co so dem nguoc)": khang dinh X HIEN, ve
# "khong co so dem" chi la ve phu - khong duoc doc ca cau thanh cau phu dinh.
X_HIEN_RE = re.compile(r"(?:button|n[úu]t)\s*X\s+(?:\([^)]*\)\s*)?(?:hi[ểe]n\s*th[ịi]|xu[ấa]t\s*hi[ệe]n)|"
                       r"\bX\s+xu[ấa]t\s*hi[ệe]n", re.I)


def _phu_dinh_x(text: str) -> bool:
    return bool(KHONG_HIEN_RE.search(text)) and not X_HIEN_RE.search(text)


# "Tai ~t0+3s: app AUTO CHUYEN MAN NGAY du button X chua kip hien": cau hoi la
# luc CHUYEN MAN, X chi la ve phu -> cham theo log, khong theo khung.
X_CHUA_RE = re.compile(r"ch[ưu]a\s+k[ịi]p\s+hi[ệe]n|d[ùu]\s+(?:button|n[úu]t)\s*X", re.I)
# "Countdown X bi huy khi roi man - khong hien X o man ke": soi khung SAU luc roi OB3.
MAN_KE_RE = re.compile(r"m[àa]n\s+k[ếe]|r[ờo]i\s+m[àa]n", re.I)
BAM_X_RE = re.compile(r"b[ấa]m\s+(?:n[úu]t\s+|button\s+)?X\b|đ[óo]ng.{0,30}chuy[ểe]n.{0,30}\bngay\b", re.I)
AD_MOI_RE = re.compile(r"ad\s+m[ớo]i", re.I)
DOC_LAP_RE = re.compile(r"đ[ộo]c\s+l[ậa]p|kh[ôo]ng\s+can\s+thi[ệe]p", re.I)
# Ad khong fill: user chot (2026-09-25, nhac lai 2026-10-06) "khong fill thi khong
# sao, chi can request DUNG ad". Nen: co request native 303 -> dat; khong co -> FAIL.
# "Auto-timer bi huy" (do bam X), "2 timer doc lap": chi xay ra khi X hien.
HUY_RE = re.compile(r"b[ịi]\s+h[ủu]y", re.I)
NGAY_RE = re.compile(r"\bngay\b", re.I)
# "Bam X -> chuyen man ngay", "Native full dong, chuyen sang man ke tiep ngay"
SAU_BAM_RE = re.compile(r"b[ấa]m\s+(?:n[úu]t\s+|button\s+)?X\b|chuy[ểe]n\s+sang\s+m[àa]n\s+k[ếe]", re.I)
# Tool vua vuot/bam trong khoang nay truoc luc roi trang -> do TOOL, khong phai app.
DO_TOOL = 2.0
GIAY_RE = re.compile(r"t0\s*\+\s*(\d+(?:[.,]\d+)?)|(?:sau|t[ạa]i)\s*(?:đủ\s*)?~?\s*(\d+(?:[.,]\d+)?)\s*s\b|"
                     r"~\s*(\d+(?:[.,]\d+)?)\s*s\b", re.I)


def _so(cfg: dict, key: str) -> float | None:
    try:
        return float(str(cfg.get(key, "")).strip())
    except ValueError:
        return None          # "abc", "null": app dung mac dinh - TC tu ghi so mong doi


def _giay_mong(text: str, cfg: dict, key: str) -> float | None:
    m = GIAY_RE.search(text)
    if m:
        return float(next(g for g in m.groups() if g).replace(",", "."))
    return _so(cfg, key)


def cham(text: str, tl: dict | None, cfg: dict, req_303=()) -> dict | None:
    """Dong nay la dong thoi gian OB3 thi cham, khong phai thi None.

    `req_303`: cac unit native 303 da duoc request trong luot (tu log ads).
    """
    luot = (tl or {}).get("luot") or []
    if not luot:
        return None
    dau = luot[0]
    if AD_MOI_RE.search(text):
        # "Khi ad MOI duoc show: X dem lai tu dau" - cham o lan vao OB3 SAU
        # (luot vuot qua lai), lan cuoi co ad show; khong co thi lan cuoi.
        dau = next((v for v in reversed(luot[1:]) if v["co_ad"]), luot[-1])
    thao_tac = (tl or {}).get("thao_tac") or []
    tool_roi = bool(dau["roi"]) and any(0 <= dau["roi"] - t <= DO_TOOL for t in thao_tac)
    if SAU_BAM_RE.search(text) and tool_roi:
        tre = dau["roi"] - max(t for t in thao_tac if t <= dau["roi"])
        return out(PASS if tre <= 1.5 else FAIL, f"rời trang OB3 {tre:.1f}s sau khi tool bấm", text)
    if BAM_X_RE.search(text):
        # Tool chi bam X khi X hien; ad khong fill thi X khong bao gio hien.
        if not dau["co_ad"]:
            return _khong_fill(text, dau, (tl or {}).get("khung") or [], req_303)
        return out(FAIL, "nút X đã hiện nhưng trang OB3 không rời trong 2s sau khi tool bấm"
                   if thao_tac else "ad đã show nhưng nút X không hiện để bấm", text)
    if TU_CHUYEN_RE.search(text) and X_CHUA_RE.search(text):
        return _tu_chuyen(text, dau, cfg)
    if X_RE.search(text) or DEM_RE.search(text):
        khung = (tl or {}).get("khung") or []
        if MAN_KE_RE.search(text) and KHONG_HIEN_RE.search(text) and dau["roi"]:
            return _x_man_ke(text, dau, khung)
        return _nut_x(text, dau, khung, cfg, req_303)
    if (DOC_LAP_RE.search(text) or HUY_RE.search(text)) and not dau["co_ad"]:
        return _khong_fill(text, dau, (tl or {}).get("khung") or [], req_303)
    if MOT_LAN_RE.search(text) or DOC_LAP_RE.search(text):
        roi = [v["roi"] for v in luot if v["roi"]]
        if len(roi) <= 1 and not any(v["vao"] > dau["vao"] and v["vao"] - (dau["roi"] or 0) < 1.5
                                     for v in luot[1:]):
            return out(PASS, f"trang OB3 chỉ bị rời {len(roi)} lần trong cả lượt — không chuyển "
                             "màn lần 2", text)
        return out(FAIL, f"trang OB3 bị rời/vào lại {len(roi)} lần", text)
    if KHONG_TU_RE.search(text):
        return _khong_tu_chuyen(text, dau, cfg, tool_roi)
    if TU_CHUYEN_RE.search(text):
        if tool_roi:
            return out(NEEDS_HUMAN, "trang OB3 bị rời ngay sau một cú vuốt/bấm của tool — "
                                    "không tách được app tự chuyển hay do tool", text)
        return _tu_chuyen(text, dau, cfg)
    return None


def _tu_chuyen(text: str, v: dict, cfg: dict) -> dict:
    mong = _giay_mong(text, cfg, "timer_auto_swipe")
    if v["roi"] is None:
        return out(FAIL, f"không tự rời trang OB3 trong suốt lượt (t0 = {v['nguon_t0']})", text)
    do = v["roi"] - v["t0"]
    if mong is None:
        return out(PASS, f"tự chuyển màn sau {do:.1f}s kể từ {v['nguon_t0']}", text)
    ok = abs(do - mong) <= SAI_SO_LOG
    return out(PASS if ok else FAIL,
               f"tự chuyển màn sau {do:.1f}s kể từ {v['nguon_t0']} — kỳ vọng {mong:g}s "
               f"(sai số ±{SAI_SO_LOG:g}s, đo bằng giờ trong log)", text)


def _khong_tu_chuyen(text: str, v: dict, cfg: dict, tool_roi: bool) -> dict:
    timer = _so(cfg, "timer_auto_swipe") or 5.0
    if v["roi"] is not None and tool_roi:
        o = v["roi"] - v["t0"]
        if o < timer + SAI_SO_LOG:
            # Tool vuot truoc khi het timer -> chua biet app co tu chuyen khong.
            return out(NEEDS_HUMAN, f"tool vuốt/bấm sau {o:.1f}s, chưa quá timer {timer:g}s", text)
        return out(PASS, f"đứng yên trên OB3 {o:.1f}s (quá timer {timer:g}s), chỉ rời khi tool "
                         "vuốt/bấm", text)
    if v["roi"] is not None:
        return out(FAIL, f"vẫn rời trang OB3 sau {v['roi'] - v['t0']:.1f}s kể từ {v['nguon_t0']}",
                   text)
    return out(PASS, f"không rời trang OB3 trong suốt lượt (timer {timer:g}s) — chỉ rời khi "
                     "tool thao tác", text)


def _nut_x(text: str, v: dict, khung: list, cfg: dict, req_303=()) -> dict:
    tren = [k for k in khung if k["t"] >= v["vao"] and (v["roi"] is None or k["t"] <= v["roi"])]
    if not v["co_ad"] and not _phu_dinh_x(text):
        # Log noi ro ad khong show -> X khong the hien; khong can khung moi ket luan.
        return _khong_fill(text, v, khung, req_303)
    if not tren:
        return out(NEEDS_HUMAN, "không có khung nào chụp trên trang OB3 để soi nút X", text)
    x = [k for k in tren if k["x"]]
    dem = [k for k in tren if k["dem"]]
    if _phu_dinh_x(text):
        thay = ("nút X" if x else "") + (" và " if x and dem else "") + ("số đếm ngược" if dem else "")
        return out(FAIL if thay else PASS,
                   f"thấy {thay} trên trang OB3" if thay else
                   f"{len(tren)} khung trên OB3: không có nút X, không có số đếm ngược", text)
    if not v["co_ad"]:
        return _khong_fill(text, v, khung, req_303)
    if DEM_RE.search(text) and not X_RE.search(text):
        return out(PASS if dem else FAIL,
                   f"số đếm ngược hiện: {', '.join(k['dem'] for k in dem)}" if dem else
                   "không khung nào thấy số đếm ngược", text)
    if not x:
        return out(FAIL, f"nút X không hiện trong {len(tren)} khung trên OB3", text)
    luc = x[0]["t"] - v["t0"]
    if NGAY_RE.search(text):
        return out(PASS if luc <= SAI_SO_KHUNG and not dem else FAIL,
                   f"nút X hiện ở khung đầu sau {luc:.1f}s"
                   + (", có số đếm ngược trước đó" if dem else ""), text)
    mong = _giay_mong(text, cfg, "timer_button_x")
    if mong is None:
        return out(PASS, f"nút X hiện sau {luc:.1f}s kể từ {v['nguon_t0']}", text)
    truoc = [k["t"] - v["t0"] for k in tren if not k["x"] and k["t"] < x[0]["t"]]
    som = max(truoc) if truoc else 0.0       # X hien trong khoang (som, luc]
    ok = som - SAI_SO_KHUNG <= mong <= luc + SAI_SO_KHUNG
    return out(PASS if ok else FAIL,
               f"nút X hiện trong khoảng {som:.1f}–{luc:.1f}s kể từ {v['nguon_t0']} — kỳ vọng "
               f"{mong:g}s (khung chụp cách nhau ~1–2,5s)", text)


def _khong_fill(text: str, v: dict, khung: list, req_303=()) -> dict:
    """Ad khong fill: dat khi native 303 duoc request dung VA X / so dem khong hien."""
    tren = [k for k in khung if k["t"] >= v["vao"] and (v["roi"] is None or k["t"] <= v["roi"])]
    thay = [k for k in tren if k["x"] or k["dem"]]
    if thay:
        return out(FAIL, f"native OB3 không fill nhưng {len(thay)}/{len(tren)} khung vẫn thấy nút X / "
                         "số đếm — X chỉ được hiện khi ad show", text)
    if not req_303:
        return out(FAIL, "native OB3 không show và log không có request native 303 nào — app "
                         "không gọi ad cho OB3", text)
    return out(PASS, f"native OB3 được request đúng ({', '.join(req_303)}) nhưng kho không fill — "
                     "request đúng là đạt; nút X / số đếm chỉ hiện khi ad show"
                     + (f", {len(tren)} khung trên OB3 không thấy X/số đếm" if tren else ""), text)


def _x_man_ke(text: str, v: dict, khung: list) -> dict:
    # Chi khung uiautomator: khung "nhanh" (dumpsys) van thay nut X cua trang OB3
    # nam canh ben trong ViewPager du trang do da khuat -> bao "con X" sai.
    sau = [k for k in khung if k["t"] > v["roi"] and k.get("nguon") != "nhanh"]
    if not sau:
        return out(NEEDS_HUMAN, "không có khung nào chụp sau lúc rời OB3", text)
    thay = [k for k in sau if k["x"] or k["dem"]]
    return out(FAIL if thay else PASS,
               f"{len(thay)}/{len(sau)} khung ở màn kế vẫn thấy nút X / số đếm" if thay else
               f"{len(sau)} khung ở màn kế sau khi rời OB3: không có nút X, không có số đếm", text)


def cach_quan_sat(overrides: dict, expects) -> tuple[float, bool]:
    """-> (so giay theo doi, co can nhin lien tuc khong).

    Cua so = timer lon nhat cua case + 5s, de kip thay ca luc het timer. Chi nhin
    lien tuc (ton thoi gian) khi co dong Expected hoi nut X / so dem nguoc.
    """
    timers = [x for x in (_so(overrides, "timer_auto_swipe"), _so(overrides, "timer_button_x"))
              if x is not None]
    giay = min(25.0, max(8.0, max(timers, default=7.0) + 5.0))
    return giay, any(X_RE.search(e or "") or DEM_RE.search(e or "") or BAM_X_RE.search(e or "")
                     for e in expects)
