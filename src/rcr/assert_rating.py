"""Cham dong Expected cua tab TC "rating" bang bang chung `act_rating` ghi vao `record["rating"]` cua tung buoc.

Cach cham giong luot do tay AIP892 12/11/2026 (user chap nhan): popup / nut / man doc tu cay node va dumpsys, event
doc tu log FA-SVC, luc nut X hien do bang khung chup lien tuc tinh tu event rating_placement_viewed.
Dong khong thuoc nhom nao duoi day, hoac case khong co buoc rating -> None (luat chung cham tiep).
"""

from __future__ import annotations

import re

from .verdict_levels import FAIL, NEEDS_HUMAN, PASS, out, worst

X_HIEN_RE = re.compile(r"\b(?:button\s+|n[úu]t\s+)?X\s+(ch[ưu]a\s+)?(?:hi[ệe]n|xu[ấa]t\s+hi[ệe]n)(?P<rest>[^.;]*)", re.I)
GIAY_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*gi[âa]y", re.I)
NGAY_RE = re.compile(r"\bngay\b", re.I)
NHAN_RE = re.compile(r"nh[ãa]n[^\"“]{0,20}[\"“]([^\"”]+)[\"”]", re.I)
SO_SAO_RE = re.compile(r"\((\d)\s*[<≥>=]|^\s*(\d)\s*sao\s*:", re.I)
FEEDBACK_RE = re.compile(r"m[ởo]\s+m[àa]n\s+feedback|feedback\s+hi[ểe]n\s+th[ịi]", re.I)
PLAY_RE = re.compile(r"m[ởo]\s+store\s+listing|m[ởo].{0,30}google\s+play", re.I)
KHONG_PLAY_RE = re.compile(r"kh[ôo]ng\s+m[ởo]\s+google\s+play", re.I)
BACK_VE_RE = re.compile(r"\bback\s+v[ềe]\s+(?:đ[úu]ng\s+)?m[àa]n\s+(\S+)", re.I)
POPUP_DONG_RE = re.compile(r"popup\s+đ[óo]ng", re.I)
O_LAI_RE = re.compile(r"[ởo]\s+l[ạa]i\s+m[àa]n", re.I)
CHUA_THOAT_RE = re.compile(r"app\s+ch[ưu]a\s+tho[áa]t", re.I)
THOAT_BT_RE = re.compile(r"app\s+tho[áa]t\s+b[ìi]nh\s+th[ưu][ờo]ng", re.I)
SHORTCUT_KHONG_RE = re.compile(r"shortcut\s+kh[ôo]ng\s+(?:c[òo]n|c[óo])\s+option\s+rat", re.I)
MAN_RATING_RE = re.compile(r"m[ởo]\s+m[àa]n\s+rating", re.I)
KHONG_HIEN_RE = re.compile(r"(?:popup\s+(?:rating\s+)?kh[ôo]ng\s+hi[ệe]n|kh[ôo]ng\s+hi[ệe]n\s+popup)", re.I)
HIEN_RE = re.compile(r"popup\s+(?:rating\s+)?hi[ệe]n|hi[ệe]n\s+popup", re.I)
VI_TRI_RE = {"home": re.compile(r"\bhome\b", re.I), "result": re.compile(r"\bresult\b", re.I),
             "exit_click": re.compile(r"exit_click", re.I)}
EVENT_RE = re.compile(r"event\s+(rating_\w+)", re.I)
KHONG_EVENT_RE = re.compile(r"kh[ôo]ng\s+c[óo]\s+event\s+(rating_\w+)", re.I)
PARAM_RE = re.compile(r"(placement_name|star_value)\s*=\s*[\"“]?([\w]+)", re.I)
SAI_SO_X = 0.6           # khung chup ~0,25s/khung + tre ghi event: lech <= 0,6s van tinh dung moc


def _recs(drive: dict) -> list[dict]:
    return [s["rating"] for s in drive.get("steps") or [] if isinstance(s.get("rating"), dict)]


def _cuoi(recs, viec: str, dk=lambda r: True) -> dict | None:
    return next((r for r in reversed(recs) if r["viec"] == viec and dk(r)), None)


def cham(text: str, drive: dict) -> dict | None:
    recs = _recs(drive or {})
    if not recs:
        return None
    dung = next((r["dung"] for r in recs if r.get("dung")), "")
    if dung:
        # Buoc rating dung giua chung (vd gen khong toi result): khong co bang chung cho dong nao - khong FAIL gia.
        return out(NEEDS_HUMAN, f"tool dừng ở bước rating: {dung}", "")
    phan = [k for k in (_x(text, recs), _nhan(text, recs), _mo(text, recs), _back(text, recs), _dong(text, recs),
                        _thoat(text, recs), _shortcut(text, recs), _popup(text, recs), _event(text, recs)) if k]
    if not phan:
        return None
    v = worst([k["verdict"] for k in phan])
    return out(v, "; ".join(k["reason"] for k in phan), " · ".join(str(k.get("actual") or "") for k in phan))


def _x(text, recs):
    m = X_HIEN_RE.search(text)
    if not m:
        return None
    do = next((r["do_x"] for r in reversed(recs) if (r.get("do_x") or {}).get("khung")), None)
    if not do:
        return out(NEEDS_HUMAN, "chưa đo được lúc nút X hiện (không có khung chụp lúc popup hiện)", "")
    hien, chua = do.get("x_hien_s"), do.get("x_chua_hien_luc_s")
    so = GIAY_RE.search(m.group("rest") or "")
    moc = f"X hiện ở {hien}s sau popup" + (f", còn chưa có ở {chua}s" if chua is not None else "")
    if hien is None:
        return out(FAIL, "khung chụp không thấy nút X hiện", moc)
    if m.group(1):                                   # "X chua hien o moc N giay"
        n = float(so.group(1).replace(",", ".")) if so else 0.0
        if hien < n - SAI_SO_X:
            return out(FAIL, f"X đã hiện ở {hien}s, trước mốc {n:g}s", moc)
        if chua is not None and chua >= n - 0.1:
            return out(PASS, f"mốc {chua}s (≥ {n:g}s) chưa có X", moc)
        return out(NEEDS_HUMAN, f"không có khung chụp ở mốc {n:g}s để xác nhận X chưa hiện", moc)
    if NGAY_RE.search(m.group("rest") or ""):
        if do.get("co_tu_khung_dau") and hien > SAI_SO_X:
            return out(NEEDS_HUMAN, f"khung chụp đầu tiên ({hien}s sau popup) đã có X — không biết X có từ 0s không",
                       moc)
        return out(PASS if hien <= SAI_SO_X else FAIL, f"X hiện {hien}s sau popup (kỳ vọng ngay)", moc)
    if so:
        n = float(so.group(1).replace(",", "."))
        ok = n - SAI_SO_X <= hien <= n + SAI_SO_X
        return out(PASS if ok else FAIL, f"X hiện {hien}s sau popup (kỳ vọng {n:g}s)", moc)
    return out(PASS, "nút X có hiện", moc)


def _rec_sao(text, recs):
    m = SO_SAO_RE.search(text)
    n = int(m.group(1) or m.group(2)) if m else None
    return _cuoi(recs, "sao", lambda r: n is None or r.get("sao") == n)


def _nhan(text, recs):
    m = NHAN_RE.search(text)
    if not m:
        return None
    r = _rec_sao(text, recs)
    if not r:
        return None
    ok = (r.get("nut") or "").strip().lower() == m.group(1).strip().lower()
    if ok and re.search(r"enabled", text, re.I) and not r.get("nut_enabled"):
        return out(FAIL, f"{r['sao']} sao: nút '{r['nut']}' bị disabled", r.get("nut"))
    return out(PASS if ok else FAIL, f"{r['sao']} sao: nút '{r.get('nut') or 'không thấy'}'", r.get("nut"))


def _mo(text, recs):
    fb, play = FEEDBACK_RE.search(text), PLAY_RE.search(text) and not KHONG_PLAY_RE.search(text)
    if not fb and not play:
        return None
    r = _cuoi(recs, "sao", lambda r: r.get("da_bam"))
    if not r:
        return None
    sau = f"{r.get('pkg_sau')}/{r.get('man_sau')}"
    if fb:
        ok = "feedback" in (r.get("man_sau") or "").lower() and not r.get("google_play")
        return out(PASS if ok else FAIL, f"bấm nút → {r.get('man_sau')}", sau)
    return out(PASS if r.get("google_play") else FAIL, f"bấm nút → {sau}", sau)


def _back(text, recs):
    m = BACK_VE_RE.search(text)
    r = _cuoi(recs, "back") if m else None
    if not r:
        return None
    dich, man = m.group(1).lower().strip(".,"), r.get("man") or ""
    if dich in ("a", "trước", "hiện"):
        goc = (_cuoi(recs, "sao", lambda x: x.get("da_bam")) or {}).get("truoc") or ""
        ok = bool(goc) and man == goc
    else:
        ok = {"home": "main" in man.lower()}.get(dich, dich in man.lower())
    return out(PASS if ok else FAIL, f"BACK → {man or r.get('pkg')}", man)


def _dong(text, recs):
    if not POPUP_DONG_RE.search(text):
        return None
    r = _cuoi(recs, "x") or next((x["sau_x"] for x in reversed(recs) if x.get("sau_x")), None)
    if not r or not r.get("bam"):
        return None
    ok = not r.get("popup_con") and (not O_LAI_RE.search(text) or r.get("man") == r.get("truoc"))
    return out(PASS if ok else FAIL, f"bấm X → popup {'còn' if r.get('popup_con') else 'đóng'}, ở {r.get('man')}",
               r.get("man"))


def _thoat(text, recs):
    r = _cuoi(recs, "thoat")
    if not r or not (CHUA_THOAT_RE.search(text) or THOAT_BT_RE.search(text)):
        return None
    if CHUA_THOAT_RE.search(text):
        return out(PASS if r["con_trong_app"] else FAIL, f"BACK → {r.get('pkg')}/{r.get('man')}", r.get("man"))
    ok = not r["con_trong_app"] and not r["popup"]
    return out(PASS if ok else FAIL, f"BACK → {r.get('pkg')}/{r.get('man')}", r.get("man"))


def _shortcut(text, recs):
    r = _cuoi(recs, "shortcut")
    if not r:
        return None
    if SHORTCUT_KHONG_RE.search(text):
        return out(FAIL if r["co_rating"] else PASS, f"shortcut của app: {', '.join(r['shortcuts']) or 'không có'}",
                   r["shortcuts"])
    if MAN_RATING_RE.search(text) and r.get("mo"):
        ok = "rating" in (r.get("man") or "").lower()
        return out(PASS if ok else FAIL, f"mở shortcut Rate → {r.get('man')}", r.get("man"))
    return None


def _su_kien(recs) -> list[dict]:
    seen, ra = set(), []
    for r in recs:
        for e in r.get("su_kien") or []:
            k = (e["t"], e["ten"])
            if k not in seen:
                seen.add(k)
                ra.append(e)
    return ra


# Buoc rating nao cho biet popup o vi tri nao: gen -> result, thoat -> exit_click.
VIEC_CUA = {"result": "gen", "exit_click": "thoat"}


def _vi_tri(text) -> list[str]:
    return [v for v, rx in VI_TRI_RE.items() if rx.search(text)]


def _popup(text, recs):
    viewed = [e["params"].get("placement_name") for e in _su_kien(recs) if e["ten"] == "rating_placement_viewed"]
    vi_tri = _vi_tri(text)
    if KHONG_HIEN_RE.search(text):
        vi_tri = vi_tri or list(VI_TRI_RE)
        co = [v for v in vi_tri if v in viewed]
        thay = [r["viec"] for r in recs if r.get("popup") and r["viec"] in {VIEC_CUA.get(v) for v in vi_tri}]
        ok = not co and not thay
        return out(PASS if ok else FAIL, f"{', '.join(vi_tri)}: rating_placement_viewed "
                   f"{', '.join(viewed) or 'không có'}", viewed)
    if HIEN_RE.search(text):
        viec = {VIEC_CUA[v] for v in vi_tri if v in VIEC_CUA} or {"gen", "thoat"}
        r = next((x for x in reversed(recs) if x["viec"] in viec), None)
        if not r:
            return None
        return out(PASS if r.get("popup") else FAIL, f"popup {'hiện' if r.get('popup') else 'không hiện'} "
                   f"ở {r.get('man')}", r.get("man"))
    return None


def _event(text, recs):
    k = KHONG_EVENT_RE.search(text)
    if k:
        ds = [e for e in _su_kien(recs) if e["ten"] == k.group(1)]
        return out(FAIL if ds else PASS, f"event {k.group(1)}: {len(ds)} lần", len(ds))
    m = EVENT_RE.search(text)
    params = dict((k.lower(), v) for k, v in PARAM_RE.findall(text))
    if not m and "placement_name" not in params:
        return None
    ten = m.group(1) if m else "rating_placement_viewed"
    ds = [e for e in _su_kien(recs) if e["ten"] == ten]
    khop = [e for e in ds if all(e["params"].get(k) == v for k, v in params.items())]
    thay = ", ".join(f"{e['ten']}{e['params']}" for e in ds[-3:]) or "không có"
    return out(PASS if khop else FAIL, f"event {ten} {params or ''}: {thay}", thay)
