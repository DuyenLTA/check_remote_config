"""Cham dong Expected cua tab TC "daily checkin" bang bang chung `act_checkin` ghi vao `record["checkin"]` tung buoc.

Cach cham giong luot do tay AIP893 2.6.0 12-13/11/2026 (user chap nhan): man / chu / nut X doc tu cay node, mau chu
dem pixel dung mau tren anh chup cung luc dump (mau_chu), event doc log FA-SVC, gen xong = History co ban vua tao.
Dong khong thuoc nhom nao duoi day, hoac case khong co buoc checkin -> None (luat chung cham tiep).
"""

from __future__ import annotations

import json
import re

from .verdict_levels import FAIL, NEEDS_HUMAN, PASS, out, worst

QUOTE = r"[\"“]([^\"”]+)[\"”]"
EVENT_RE = re.compile(r"event\s+((?:daily_)?checkin\w*|daily_checkin\w*)", re.I)
KHONG_EVENT_RE = re.compile(r"kh[ôo]ng\s+c[óo]\s+event\s+((?:daily_)?checkin\w*|daily_checkin\w*)", re.I)
LAN_RE = re.compile(r"(\d+)\s*l[ầa]n", re.I)
KHONG_HIEN_RE = re.compile(r"daily\s*check-?in\s+kh[ôo]ng\s+hi[ệe]n", re.I)
HIEN_LAI_RE = re.compile(r"daily\s*check-?in\s+hi[ệe]n\s+l[ạa]i", re.I)
HIEN_RE = re.compile(r"m[àa]n\s+daily\s*check-?in\s+hi[ệe]n", re.I)
SAU_WIDGET_RE = re.compile(r"sau\s+add\s*widget", re.I)
WIDGET_HIEN_RE = re.compile(r"add\s*widget\s+hi[ệe]n", re.I)
UNLOCKED_RE = re.compile(r"m[àa]n\s+unlocked\s+successfully\s+hi[ệe]n|unlocked\s+successfully\s+hi[ệe]n", re.I)
X_NGAY_RE = re.compile(r"(?:button|n[úu]t)\s+x\s+hi[ệe]n\s+ngay", re.I)
VE_HOME_RE = re.compile(r"^\s*(?:\d+\.\s*)?v[ềe]\s+m[àa]n\s+home", re.I)
TEXT_RE = re.compile(r"\b(title|banner|description|cta)\s+" + QUOTE, re.I)
MAU_RE = re.compile(r"\b(title|description|banner(?:\s+text)?|cta(?:\s+text)?)\s+(#[0-9a-f]{6})\b", re.I)
TEXT_UNLOCKED_RE = re.compile(r"text\s+tr[êe]n\s+m[àa]n\s+unlocked", re.I)
MAU_THEO_DS_RE = re.compile(r"m[àa]u\s+theo\s+checkin_sdk_design_system", re.I)
KHAC_TEXT_RE = re.compile(r"c[áa]c\s+text\s+kh[áa]c\s+đ[úu]ng", re.I)
KHAC_MAU_RE = re.compile(r"c[áa]c\s+m[àa]u\s+kh[áa]c\s+đ[úu]ng", re.I)
FREE_RE = re.compile(r"free\s+generate", re.I)
AN_RE = re.compile(r"\b[ẩa]n\b|kh[ôo]ng\s+c[óo]\s+(?:button|n[úu]t)\s+free", re.I)
ENABLED_RE = re.compile(r"\benabled\b", re.I)
DISABLED_RE = re.compile(r"\bdisabled\b", re.I)
SO_LUOT_RE = re.compile(r"(?:đ[úu]ng|c[òo]n)\s+(\d+)\s+l[ưu][ợo]t", re.I)
VAN_HIEN_RE = re.compile(r"v[ẫa]n\s+hi[ệe]n", re.I)
GEN_OK_RE = re.compile(r"gen\s+(?:ch[ạa]y\s+v[àa]\s+tr[ảa]\s+k[ếe]t\s+qu[ảa]\s+)?th[àa]nh\s+c[ôo]ng", re.I)
SO_GEN_RE = re.compile(r"c[ảa]\s+(\d+)\s+l[ầa]n\s+gen", re.I)
GAN = 30                 # it nhat ngan nay pixel dung mau trong khung chu moi coi la chu co mau do
TRUONG_MAU = {"title_text_color": "title", "description_text_color": "description", "banner_text_color": "banner",
              "cta_text_color": "cta"}


def _recs(drive: dict) -> list[dict]:
    return [s["checkin"] for s in drive.get("steps") or [] if isinstance(s.get("checkin"), dict)]


def _json(cfg, key) -> dict:
    try:
        v = json.loads((cfg or {}).get(key) or "{}")
        return v if isinstance(v, dict) else {}
    except ValueError:
        return {}


def _nhin(recs) -> list[dict]:
    """Moi lan nhin Home (sau dong widget / ve Home / kill mo lai) theo thu tu."""
    ra = []
    for r in recs:
        if r["viec"] in ("quan_sat", "vao_home", "full"):
            ra.append(r)
        ra += r.get("lan") or []
    return ra


def _su_kien(recs) -> list[dict]:
    seen, ra = set(), []
    for r in recs:
        for e in r.get("su_kien") or []:
            k = (e["t"], e["ten"])
            if k not in seen:
                seen.add(k)
                ra.append(e)
    return ra


def cham(text: str, drive: dict, cfg: dict | None = None) -> dict | None:
    recs = _recs(drive or {})
    if not recs:
        return None
    dung = next((r["dung"] for r in recs if r.get("dung")), "")
    if dung:
        return out(NEEDS_HUMAN, f"tool dừng ở bước daily checkin: {dung}", "")
    phan = [k for k in (_man(text, recs), _x(text, recs), _ve_home(text, recs), _text(text, recs, cfg),
                        _mau(text, recs, cfg), _free(text, recs), _gen(text, recs), _event(text, recs)) if k]
    if not phan:
        return None
    return out(worst([k["verdict"] for k in phan]), "; ".join(k["reason"] for k in phan),
               " · ".join(str(k.get("actual") or "") for k in phan))


def _man(text, recs):
    nhin = _nhin(recs)
    if KHONG_HIEN_RE.search(text):
        if not nhin:
            return None
        co = [n for n in nhin if n.get("checkin")]
        can = 2 if re.search(r"c[ảa]\s+2\s+b[ưu][ớo]c", text, re.I) else 1
        if len(nhin) < can:
            return out(NEEDS_HUMAN, f"mới nhìn Home {len(nhin)} lần, câu đòi {can}", len(nhin))
        ra = out(FAIL if co else PASS, f"nhìn Home {len(nhin)} lần: màn Check-in {'có' if co else 'không'} hiện",
                 len(co))
        if WIDGET_HIEN_RE.search(text):
            w = any(n.get("widget") for n in nhin)
            ra = out(worst([ra["verdict"], PASS if w else FAIL]), ra["reason"] + f"; Add Widget {'có' if w else 'không'}"
                     " hiện", ra["actual"])
        return ra
    if HIEN_LAI_RE.search(text) or HIEN_RE.search(text):
        if not nhin:
            return None
        n = nhin[-1]
        ok = bool(n.get("checkin")) and (not SAU_WIDGET_RE.search(text) or n.get("widget"))
        return out(PASS if ok else FAIL, f"màn Check-in {'hiện' if n.get('checkin') else 'không hiện'}"
                   + (f", Add Widget {'hiện trước' if n.get('widget') else 'không hiện'}" if SAU_WIDGET_RE.search(text)
                      else ""), (n.get("checkin") or {}).get("title"))
    if WIDGET_HIEN_RE.search(text) and nhin:
        w = any(n.get("widget") for n in nhin)
        return out(PASS if w else FAIL, f"popup Add Widget {'có' if w else 'không'} hiện khi vào Home", w)
    if UNLOCKED_RE.search(text):
        r = next((x for x in reversed(recs) if x.get("bam_checkin")), None)
        if not r:
            return None
        return out(PASS if r.get("unlocked") else FAIL,
                   f"bấm Check-in → màn Unlocked {'hiện' if r.get('unlocked') else 'không hiện'}",
                   (r.get("unlocked") or {}).get("title"))
    return None


def _x(text, recs):
    if not X_NGAY_RE.search(text):
        return None
    if re.search(r"unlocked", text, re.I) or UNLOCKED_RE.search(text):
        r = next((x for x in reversed(recs) if x.get("bam_checkin")), None)
        man = (r or {}).get("unlocked")
    else:
        man = next((n.get("checkin") for n in reversed(_nhin(recs)) if n.get("checkin")), None)
    if man is None:
        return None
    return out(PASS if man.get("x") else FAIL, "lần nhìn đầu tiên khi màn vừa hiện "
               + ("đã có nút X" if man.get("x") else "chưa có nút X"), man.get("x"))


def _ve_home(text, recs):
    if not VE_HOME_RE.search(text):
        return None
    r = next((x.get("sau_dong") or x for x in reversed(recs) if x.get("bam_x") or x.get("sau_dong")), None)
    if not r:
        return None
    ok = "main" in (r.get("man") or "").lower() and not r.get("con_popup")
    return out(PASS if ok else FAIL, f"bấm X → {r.get('man')}" + (", popup còn" if r.get("con_popup") else ""),
               r.get("man"))


def _man_text(text, recs) -> tuple[str, dict | None]:
    if re.search(r"unlocked", text, re.I):
        r = next((x for x in reversed(recs) if x.get("bam_checkin")), None)
        return "unlock", (r or {}).get("unlocked")
    return "checkin", next((n.get("checkin") for n in reversed(_nhin(recs)) if n.get("checkin")), None)


def _text(text, recs, cfg):
    hoi = TEXT_RE.findall(text)
    if not hoi and not TEXT_UNLOCKED_RE.search(text) and not KHAC_TEXT_RE.search(text):
        return None
    khoi, man = _man_text(text, recs)
    if man is None:
        return None
    can = {f.lower(): v for f, v in hoi}
    if KHAC_TEXT_RE.search(text) or TEXT_UNLOCKED_RE.search(text):
        for f, v in (_json(cfg, "checkin_sdk_config").get(khoi) or {}).items():
            if isinstance(v, str) and f in man:
                can.setdefault(f, v)
    if not can:
        return out(PASS, f"JSON không đặt text cho màn {khoi}: app dùng chữ mặc định", man.get("title"))
    sai = [f"{f}: '{man.get(f)}' ≠ '{v}'" for f, v in can.items() if (man.get(f) or "").strip() != v.strip()]
    return out(FAIL if sai else PASS, "; ".join(sai) or "text đúng: " + ", ".join(f"{f}='{v}'" for f, v in can.items()),
               {f: man.get(f) for f in can})


def _mau(text, recs, cfg):
    hoi = [(f.lower().split()[0], h.upper()) for f, h in MAU_RE.findall(text)]
    if not hoi and not MAU_THEO_DS_RE.search(text) and not KHAC_MAU_RE.search(text):
        return None
    khoi, man = _man_text(text, recs)
    if man is None:
        return None
    if KHAC_MAU_RE.search(text) or MAU_THEO_DS_RE.search(text):
        ds = _json(cfg, "checkin_sdk_design_system")
        for k, f in TRUONG_MAU.items():
            if isinstance(ds.get(k), str) and (man.get("khung") or {}).get(f) and f not in dict(hoi):
                hoi.append((f, ds[k].upper()))
    if not hoi:
        return out(PASS, "JSON không đặt màu chữ nào cho màn này", "")
    rec = next((x for x in reversed(recs) if x.get("bam_checkin")), {}) if khoi == "unlock" else None
    mau = (rec or {}).get("mau_unlocked") if khoi == "unlock" else next(
        (n.get("mau") for n in reversed(_nhin(recs)) if n.get("checkin")), None)
    kq = []
    for f, h in hoi:
        khung = (man.get("khung") or {}).get(f)
        do = next((m for m in mau or [] if khung and m["bounds"][:2] == khung[:2]), None)
        if do is None or h not in do["dem"]:
            kq.append((NEEDS_HUMAN, f"{f}: chưa đo được màu {h}"))
            continue
        trong, doi = do["dem"][h]
        ok = trong >= GAN and trong > 3 * doi
        kq.append((PASS if ok else FAIL, f"{f} {h}: {trong} px trong khung chữ / {doi} px đối chứng"))
    return out(worst([v for v, _ in kq]), "; ".join(r for _, r in kq), "")


def _sheets(recs) -> list[dict]:
    return [r["sheet"] for r in recs if r.get("sheet")]


def _free(text, recs):
    if not FREE_RE.search(text) or GEN_OK_RE.search(text):
        return None
    sh = _sheets(recs)
    if not sh:
        return None
    so = SO_LUOT_RE.search(text)
    if VAN_HIEN_RE.search(text):            # "sau lan 1 button Free Generate van hien (con 1 luot)": sheet cua lan 2
        s = sh[1] if len(sh) > 1 else None
        if s is None:
            return out(NEEDS_HUMAN, "chưa có sheet unlock của lần gen thứ 2", "")
    else:
        s = sh[-1]
    ten = s.get("free") or "không có Free Generate"
    if AN_RE.search(text) and not VAN_HIEN_RE.search(text):
        return out(FAIL if s.get("free") else PASS, f"sheet unlock: {ten}", ten)
    if not s.get("free"):
        return out(FAIL, "sheet unlock không có nút Free Generate", ten)
    if DISABLED_RE.search(text):
        return out(FAIL if s.get("enabled") else PASS, f"{ten}: {'enabled' if s.get('enabled') else 'disabled'}", ten)
    if so and s.get("left") != int(so.group(1)):
        return out(FAIL, f"{ten}: còn {s.get('left')} lượt (kỳ vọng {so.group(1)})", ten)
    if ENABLED_RE.search(text) and not s.get("enabled"):
        return out(FAIL, f"{ten}: bị disabled", ten)
    return out(PASS, f"sheet unlock: {ten}", ten)


def _gen(text, recs):
    if not GEN_OK_RE.search(text):
        return None
    gens = [r["gen"] for r in recs if r.get("gen")]
    if not gens:
        return None
    can = int(SO_GEN_RE.search(text).group(1)) if SO_GEN_RE.search(text) else 1
    xong = [g for g in gens if g.get("xong")]
    ok = len(xong) >= can and len(xong) == len(gens)
    return out(PASS if ok else FAIL, f"gen {len(xong)}/{len(gens)} lần xong (History: "
               f"{', '.join(g.get('moi_nhat') or 'không thấy bản mới' for g in gens)})", len(xong))


def _event(text, recs):
    k = KHONG_EVENT_RE.search(text)
    if k:
        ds = [e for e in _su_kien(recs) if e["ten"] == k.group(1)]
        return out(FAIL if ds else PASS, f"event {k.group(1)}: {len(ds)} lần", len(ds))
    m = EVENT_RE.search(text)
    if not m or KHONG_HIEN_RE.search(text):
        return None
    ds = [e for e in _su_kien(recs) if e["ten"] == m.group(1)]
    lan = LAN_RE.search(text[m.end():])
    if lan:
        n = int(lan.group(1))
        return out(PASS if len(ds) == n else FAIL, f"event {m.group(1)}: {len(ds)} lần (kỳ vọng {n})", len(ds))
    return out(PASS if ds else FAIL, f"event {m.group(1)}: {len(ds)} lần", len(ds))
